#ifndef RESTRACKER_HH
#define RESTRACKER_HH

#include "component.hh"
#include "hash_map.hh"

#include <ctime>

class restracker_proxy;

namespace vigil {
namespace applications {

class stopwatch
{
    protected:

        time_t last;
        int    cd_timer;

    public:    

        void reset_countdown_timer(int);
        int  time_to_finish();  
        
}; // class stopwatch

inline
void 
stopwatch::reset_countdown_timer(int t)
{
    last = ::time(NULL);
    cd_timer = t;
}

inline
int  
stopwatch::time_to_finish()
{
    return cd_timer - (::time(NULL) - last);
}

class restracker
    : public container::Component 
{
    public:    

        static const int HOST_PACKET_LIMIT  = 30000;
        static const int COUNTDOWN_DURATION = 30;

        typedef hash_map<uint64_t, hash_map<uint64_t,int> > HostMap;
        typedef hash_map<uint64_t, int >                    InportMap;

        friend class restracker_proxy;

    protected:


        HostMap   hosts;
        InportMap inports; // currently unused

        stopwatch sw;

        Disposition handle_packet_in(const Event&);

    public:    
        restracker( const container::Context*, const json_object*);
        restracker() : Component(0) {}

        static void getInstance(const container::Context*, restracker*&);

        void configure(const container::Configuration*);
        void install();


}; // class restracker

} // namespace applications
} // namespace vigil

#endif  // -- RESTRACKER_HH


