/* Stats aggregator
 * 
 * Maintain daily/hourly/max/min/average stats given
 * periodic updates.
 *
 * TODO:
 *
 *  - Number of active hosts
 *  - Number of link changes per second 
 *  - If no events come in over a period of time, doesn't keep track of
 *    data.
 *
 */

#ifndef STATS_AGGR_HH__
#define STATS_AGGR_HH__

#include "timeval.hh"

#include <deque>
#include <cassert>
#include <iostream>

namespace vigil
{

template <int N = -1, int S = 1>    
struct timed_aggr 
{

public:
    timeval start_time;
    timeval last_update;

    std::deque<float> sum_queue;

    // MAX/MIN values collacted over the time range
    unsigned int min;
    unsigned int max;

    // Current count in the given time range
    unsigned int val;

    // Used to keep running average for this time range
    int          sum;     
    int          sum_cnt; 

    timed_aggr():
        min((unsigned int)-1), max(0), val(0), sum(0), sum_cnt(0)
    {
        start_time.tv_sec  = 0;
        start_time.tv_usec = 0;
        last_update.tv_sec = 0;
        last_update.tv_usec = 0;
    }

    bool init(const timeval& tv){
        start_time = last_update = tv;
        return true;
    }

    float last_s() const{
        if (sum_queue.size() > 0){
            return sum_queue.back();
        }
        return 0;
    }

    bool rotate(const timeval& tv){

        float last_interval;

        if ( (last_interval = (float)timeval_to_ms( (tv - start_time))) > N){

            // use midpoint between last two events as finishing time
            float mid_point = ((float)timeval_to_ms( (tv - last_update)))/(float)2.;
            float delta_ms = (float)
                             (((float)timeval_to_ms(last_update - start_time) + 
                               mid_point));
            assert(delta_ms);
            int cnt_per_s =  (int)((float)val / (delta_ms / 1000.));

            if (cnt_per_s > max) {
                max = cnt_per_s;
            }

            if (cnt_per_s && cnt_per_s < min){
                min = cnt_per_s;
            }
            if(S){
                sum_queue.push_back(cnt_per_s);
                if(sum_queue.size() > S){
                    sum_queue.pop_front();
                }
            }
            sum += cnt_per_s;
            sum_cnt ++;
            val = 0;
            return true;
        }
        return false;
    }

    void inc(const timeval& tv) {

        if ( rotate(tv) ){
            start_time  = tv;
            last_update = tv;
        }else{
            last_update = tv;
        }

        val ++;
    }

    float tot_avg() {
        if (!sum_cnt){
            return cur_avg();
        }
        return sum / sum_cnt;
    }

    float cur_avg() {
        float delta_ms = (float)timeval_to_ms(last_update - start_time);
        if (delta_ms == 0.){
            return 0;
        }
        return (float)val / (delta_ms/1000.);
    }

};

// Specialization for 
template <int S>
struct timed_aggr<-1,S>
{
    timeval start_time;
    timeval last_update;

    // Since time range is infinite, just keep track of sim
    int          val;     

    timed_aggr(): val(0)
    { ; }

    void inc(const timeval& tv) {
        val ++;
        last_update = tv;
    }

    float cur_avg_s(){
        float delta_ms = (float)timeval_to_ms(last_update - start_time);
        if (delta_ms == 0.){
            return 0.;
        }
        return (float)val /
               (delta_ms / 100.);
    }
};

struct stats_aggr
{

public:

    timed_aggr<1000,   30>  s_aggr;
    timed_aggr<5*1000, 20>  s5_aggr;
    timed_aggr<60*1000,10>  min_aggr;
    timed_aggr<5*60*1000>   min5_aggr;
    timed_aggr<60*60*1000>  hr_aggr;
    timed_aggr<24*60*1000>  day_aggr;
    timed_aggr<>            tot_aggr;

public:    
    stats_aggr();

    void inc(const timeval& in);
    void rotate(const timeval& in);

}; // class stats_aggr;

inline
stats_aggr::stats_aggr()
{
}

inline 
void
stats_aggr::rotate(const timeval& tv_in)
{
    s_aggr.rotate(tv_in);
    s5_aggr.rotate(tv_in);
    min_aggr.rotate(tv_in);
    min5_aggr.rotate(tv_in);
    hr_aggr.rotate(tv_in);
    day_aggr.rotate(tv_in);
}

inline 
void
stats_aggr::inc(const timeval& tv_in)
{
    s_aggr.inc(tv_in);
    s5_aggr.inc(tv_in);
    min_aggr.inc(tv_in);
    min5_aggr.inc(tv_in);
    hr_aggr.inc(tv_in);
    day_aggr.inc(tv_in);
    tot_aggr.inc(tv_in);
}

} // namespace vigil

#endif // -- STATS_AGGR_HH__
