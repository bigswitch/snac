/* Copyright 2008 (C) Nicira, Inc.
 */
#include "component.hh"
#include "config.h"
#include "vlog.hh"
#include <xercesc/dom/DOM.hpp>
#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <malloc.h> 

using namespace std;
using namespace vigil;
using namespace vigil::container;

namespace {

static Vlog_module lg("malloc-monitor");

class MallocMonitor : public Component {

public:
    MallocMonitor(const Context* c, const xercesc::DOMNode*)
        : Component(c), print_interval_secs(60) {
    }

    void configure(const Configuration* conf) {
      Component_argument_list clist = conf->get_arguments(); 
      Component_argument_list::const_iterator cit = clist.begin();
      while(cit != clist.end()){
        char *key = strdup(cit->c_str()); 
        char *value = strchr(key,'='); 
        if(value != NULL) {
          *value = NULL;
          ++value;
          if(!strcmp(key,"print_interval_secs")) {  
            this->print_interval_secs = atoi(value);
          } 
        }
        free(key); 
        ++cit; 
      }   
    }

    void install() {
      start = do_gettimeofday();
      do_print(); // kick it off
    }

    void do_print() { 
      timeval now = do_gettimeofday();
      timeval diff = now - start; 
      struct mallinfo m = mallinfo();
      uint32_t inuse = (uint32_t)m.uordblks / 1000; 
      uint32_t free = (uint32_t)m.fordblks / 1000; 
      uint32_t arena = (uint32_t)m.arena / 1000; 
      uint32_t mmap = (uint32_t)m.hblkhd / 1000; 
      lg.err("malloc: %d used / %d free / %d arena / %d mmap KB after %d secs.\n", 
          inuse, free, arena , mmap, diff.tv_sec); 
      timeval tv = make_timeval(this->print_interval_secs,0); 
      post(boost::bind(&MallocMonitor::do_print, this),tv);
    } 

private:
  timeval start; 
  int print_interval_secs;
};

REGISTER_COMPONENT(container::Simple_component_factory<MallocMonitor>,
                   MallocMonitor);

} // unnamed namespace
