#include <ctime>
#include <cmath>
#include <list>
#include <sys/time.h>
#include "hash_map.hh"

#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>

#include <stdio.h>

#include "component.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace boost;

// ^^
// Debug on:
//   :0,$s/ printf("/\/\/ printf("/g
// Debug off:
//   :0,$s//\/\ printf("/ printf("/g

namespace { 

static Vlog_module lg("audit");

class Audit
    : public Component
{
public:

    Audit(const Context* c,
          const xercesc::DOMNode* xml) 
        : Component(c), v_calibrations(NULL), r_calibrations(NULL) {
    }

    ~Audit() {
        if (v_calibrations) {
            free(v_calibrations);
            v_calibrations = NULL;
        }
        if (r_calibrations) {
            free(r_calibrations);
            r_calibrations = NULL;
        }
        if (v_bar) {
            free(v_bar);
            v_bar = NULL;
        }
        if (r_bar) {
            free(r_bar);
            r_bar = NULL;
        }
    }

    void configure(const Configuration*) {
        fprintf(stderr,"@@ Auditing @@\n");
        wait_initial = 2;
        wait_calibrate = 2;
        num_calibrations = 15;
        wait_examine = 5;
        v_wiggle = 512; //kB
        r_wiggle = 128;  //kB
        devs = 4;
        bar_length = 41; // Must be at least 9
        gettimeofday(&start,NULL);
        v_calibrations = (int*)malloc(sizeof(int)*num_calibrations);
        r_calibrations = (int*)malloc(sizeof(int)*num_calibrations);
        v_bar = (char*)malloc(sizeof(char)*(bar_length+1));
        r_bar = (char*)malloc(sizeof(char)*(bar_length+1));
    }

    // This is broken perhaps, for large stdev small wiggle
    void set_bar(char* bar, double stdev, int wiggle) {
        //  def bar(s,w):
        //    return ' <<-%s[%s]%s->> ' % ('-'*w,' '*(2*s+1),'-'*w)
        //  def nums(n,w,s):
        //   ss = int((((n-6)*s)/(w+s)-3)/2)
        //   ss = min(max(0,ss),(n-11)/2)
        //   ws = (n-11 - 2*ss)/2
        //   return (ss,ws)

        if (stdev == wiggle) { // Avoid division by 0
            stdev = 1;
            wiggle = 1;
        }

        int std = (((bar_length-6)*devs*stdev)/(wiggle+devs*stdev)-3)/2;
        if (std < 0) {
            std = 0;
        }
        if (std > (bar_length-9)/2) {
            std = (bar_length-9)/2;
        }
        int wig = (bar_length-9 -2*std)/2;

        int i;
        char wig_str[100];  // Where 100 > bar_length, kludged
        for (i=0 ; i<wig; i++){
            wig_str[i] = '-';
        }
        wig_str[i] = '\0';

        char std_str[100];
        for (i=0 ; i<2*std+1; i++){
            std_str[i] = ' ';
        }
        std_str[i] = '\0';

        sprintf(bar," <<%s[%s]%s>> ",wig_str,std_str,wig_str);
        for (int i=0; i< bar_length; i++) {
            if (bar[i] == '0') {
                bar[i] = '-';
            }
            else if (bar[i] == '1') {
                bar[i] = '[';
            }
            else if (bar[i] == '2') {
                bar[i] = ']';
            }
        }
    }

    int draw_mem(int val, double max, double stdev, int wiggle) {
        if (stdev == wiggle) { // Avoid division by 0
            stdev = 1;
            wiggle = 1;
        }

        double z = (val - max)/(devs*stdev + wiggle);
        if (z > 1) {
            return bar_length-1;
        }
        if (z < -1) {
            return 0;
        }

        return 3 + ((z+1)*(bar_length-6))/2;
    }

    void install() {
       // printf("@@ Auditor Initializing ... @@ \n");
        pid = getpid();
       // printf(" @ Oxide pid: %d @\n", pid);
       // printf(" @ Initial Wait: %d @\n", wait_initial);
       // printf(" @ Number of Calibrations: %d@\n", num_calibrations);
       // printf(" @ Calibration Wait: %d @\n", wait_calibrate);
       // printf(" @ Examination Wait: %d @\n", wait_examine);
       // printf(" @ Virtual Wiggle-Room: %d @\n", v_wiggle);
       // printf(" @ Resident Wiggle-Room: %d @\n", r_wiggle);

        // Wait for inital turmoil to settle
        timeval tv = { wait_initial, 0 };
        post(boost::bind(&Audit::calibrate, this), tv);
    }

    void calibrate() {
        char cmd[128];
        int v_mem = -911;
        int r_mem = -911;
        static int count = 0;
        if (count == 0) {
           // printf("@@ Calibrating ... @@ \n");
        }
        count++;
       // printf(" @ (%d/%d) @\n", count, num_calibrations);

        sprintf(cmd,"ps -p %d -ovsz=,rss=",pid);
        FILE* ps = popen(cmd,"r");
        fscanf(ps,"%d",&v_mem);
        fscanf(ps,"%d",&r_mem);
        fclose(ps);

       // printf(" @ Virtual Memory Used: %d @\n", v_mem);
       // printf(" @ Resident Memory Used: %d @\n", r_mem);
        v_calibrations[count-1] = v_mem;
        r_calibrations[count-1] = r_mem;

        if (count < num_calibrations) {
            timeval tv = { wait_calibrate, 0 };
            post(boost::bind(&Audit::calibrate, this), tv);
        }
        else {
           // printf(" @ Calibration Data: @\n");

            v_mean = 0;
            r_mean = 0;
            v_max = 0;
            r_max = 0;
            for (int i=0; i < num_calibrations; i++) {
                v_mean += v_calibrations[i];
                r_mean += r_calibrations[i];
                if (v_calibrations[i] > v_max) {
                    v_max = v_calibrations[i];
                }
                if (r_calibrations[i] > r_max) {
                    r_max = r_calibrations[i];
                }
            }
            v_mean /= num_calibrations;
            r_mean /= num_calibrations;
           // printf(" @  Mean(Virt): %.2fkB @\n", v_mean);
           // printf(" @  Mean(Res):  %.2fkB @\n", r_mean);

            v_stdev = 0;
            r_stdev = 0;
            if (num_calibrations < 2) {
               // printf(" @ Too few samples to calculate deviation.\n");
                v_stdev = 5000; // Other options? : infinite, zero
                r_stdev = 5000; // Other options? : infinite, zero
            }
            else {
                for (int i=0; i < num_calibrations; i++) {
                    v_stdev += (v_calibrations[i] - v_mean) *
                               (v_calibrations[i] - v_mean);
                    r_stdev += (r_calibrations[i] - r_mean) *
                               (r_calibrations[i] - r_mean);
                }
                v_stdev = sqrt(v_stdev)/(num_calibrations-1);
                r_stdev = sqrt(r_stdev)/(num_calibrations-1);
                set_bar(v_bar,v_stdev,v_wiggle);
                set_bar(r_bar,r_stdev,r_wiggle);
               // printf(" @  Stdev(Virt): %.2fkB @\n", v_stdev);
               // printf(" @  Stdev(Res):  %.2fkB @\n", r_stdev);
            }

            free(v_calibrations);
            v_calibrations = NULL;
            free(r_calibrations);
            r_calibrations = NULL;
           // printf("@@ Examining ... @@ \n");

            v_leak = v_max + devs*v_stdev + v_wiggle;
            r_leak = r_max + devs*r_stdev + r_wiggle;
            examine();
        }
    }

    void examine() {
        char cmd[128];
        int v_mem = -911;
        int r_mem = -911;

        sprintf(cmd,"ps -p %d -ovsz=,rss=",pid);
        FILE* ps = popen(cmd,"r");
        fscanf(ps,"%d",&v_mem);
        fscanf(ps,"%d",&r_mem);
        fclose(ps);

       // printf(" @ Virtual Memory Used: %dkB @\n", v_mem);
       // printf(" @ Resident Memory Used: %dkB @\n", r_mem);

        int vm = draw_mem(v_mem,v_max,v_stdev,v_wiggle);
        char v_tmp = v_bar[vm];
        v_bar[vm] = '*';
        fprintf(stderr," @ VMem: %s [%8d/%-8d] @\n",v_bar,v_mem,v_leak);
        v_bar[vm] = v_tmp;

        int rm = draw_mem(r_mem,r_max,r_stdev,r_wiggle);
        char r_tmp = r_bar[rm];
        r_bar[rm] = '#';
        fprintf(stderr," @ RMem: %s [%8d/%-8d] @\n",r_bar,r_mem,r_leak);
        r_bar[rm] = r_tmp;

       // printf("\n");

        if ((v_mem > v_leak) || (r_mem > r_leak)) {
            timeval tv;
            gettimeofday(&tv,NULL);

            fprintf(stderr,"\n@@@@@@@@@ Suspected Memory Leak @@@@@@@@@\n");
            fprintf(stderr," @  Time Elapsed:  %7d seconds     @\n", 
                    (int)(tv.tv_sec - start.tv_sec));
            fprintf(stderr," @                                     @\n");
            fprintf(stderr," @  Virtual:  %8d/%-8d kB %s @\n", v_mem,v_leak,
                                                 (v_mem>v_leak)?"(!) ":"   ");
            fprintf(stderr," @    Wiggle-Room:   %10d kB     @\n", v_wiggle);
            fprintf(stderr," @    Mean:         %11.2f kB     @\n", v_mean);
            fprintf(stderr," @    Stdev:        %11.2f kB     @\n", v_stdev);
            fprintf(stderr," @                                     @\n");
            fprintf(stderr," @  Resident: %8d/%-8d kB %s @\n", r_mem,r_leak,
                                                 (r_mem>r_leak)?"(!) ":"   ");
            fprintf(stderr," @    Wiggle-Room:   %10d kB     @\n", r_wiggle);
            fprintf(stderr," @    Stdev:        %11.2f kB     @\n", r_stdev);
            fprintf(stderr," @    Mean:         %11.2f kB     @\n", r_mean);
            fprintf(stderr,"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n");
            exit(1);
        } else {
            timeval tv = { wait_examine, 0 };
            post(boost::bind(&Audit::examine, this), tv);
        }
    }


private:
   
    int pid;
    int wait_initial; 
    int wait_calibrate; 
    int num_calibrations;
    int wait_examine; 
    double devs;
    int* v_calibrations;
    int* r_calibrations;
    double v_mean;
    double v_stdev;
    int v_max;
    int v_leak;
    int v_wiggle;
    double r_mean;
    double r_stdev;
    int r_wiggle;
    int r_max;
    int r_leak;
    int bar_length;
    char* v_bar;
    char* r_bar;
    timeval start;
};

REGISTER_COMPONENT(container::Simple_component_factory<Audit>, Audit);

}
