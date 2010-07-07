/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */
/* Collect a set of runtime stats 
 * 
 * TODO: 
 *
 *   - have the stats collected be CLA configurable
 *   - add per-host stats collection as soon as host events are added
 *     - outstanding flows per host 
 *     - flow connectino requests per host
 *   - Once this stablizes, delete "counter" app
 *
 */

#ifndef RUNTIME_STATS_HH__
#define RUNTIME_STATS_HH__

#include <list>

#include "stats-aggr.hh"
#include "controller.hh"
#include "hash_map.hh" 
#include "timeval.hh"

// #include <algorithm>

namespace vigil
{

struct stats_snapshot
{
    float last_s;
    float max_s;
    float avg_s;

    int   samples;
};

// Python interface
bool rotate();

bool get_packet_in_s(uint64_t swid, stats_snapshot& s_in);
bool get_packet_in_s5(uint64_t swid, stats_snapshot& s_in);
bool get_packet_in_min(uint64_t swid, stats_snapshot& s_in);

int get_packet_in_s_history(uint64_t swid, std::list<float>& res);
int get_packet_in_s5_history(uint64_t swid, std::list<float>& res);
int get_packet_in_min_history(uint64_t swid, std::list<float>& res);

class runtime_stats
{

protected:    

    // Network events
    stats_aggr switch_events; 

    // Flow events (mod/exp)
    hash_map<uint64_t, stats_aggr> switch_flow_events; 
    hash_map<uint64_t, int>        switch_outstanding_flows; 

    hash_map<uint64_t, stats_aggr> switch_packet_in_stats;

    Disposition packet_in(const Event& e);

    Disposition flow_mod(const Event& e);
    Disposition flow_exp(const Event& e);

    Disposition dp_leave (const Event& e);
    Disposition dp_join (const Event& e);

    void timer();

public:    

    runtime_stats(){ ; }
    void register_callbacks();


    // accessors
    int get_total_packets(uint64_t swid);

    bool get_packet_in_s(uint64_t swid, stats_snapshot& s_in);
    bool get_packet_in_s5(uint64_t swid, stats_snapshot& s_in);
    bool get_packet_in_min(uint64_t swid, stats_snapshot& s_in);

    int get_packet_in_s_history(uint64_t swid, std::list<float>& res);
    int get_packet_in_s5_history(uint64_t swid, std::list<float>& res);
    int get_packet_in_min_history(uint64_t swid, std::list<float>& res);

    bool rotate();

};

//---------------------------------------------------------------------
inline
int
runtime_stats::get_total_packets(uint64_t swid)
{
    if(switch_packet_in_stats.find(swid) !=
            switch_packet_in_stats.end()){
        return switch_packet_in_stats[swid].tot_aggr.val;
    }
    return -1;
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
bool
runtime_stats::rotate()
{
    timeval tv;
    ::gettimeofday(&tv, 0);

    for(hash_map<uint64_t, stats_aggr>::iterator iter = 
            switch_packet_in_stats.begin();
            iter != switch_packet_in_stats.end();
            ++iter){
        iter->second.rotate(tv);
    }
    return true;
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
bool 
runtime_stats::get_packet_in_s(uint64_t swid, stats_snapshot& s_in)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  

    s_in.last_s = sa.s_aggr.last_s();
    s_in.max_s  = sa.s_aggr.max;
    s_in.avg_s  = sa.s_aggr.tot_avg();

    s_in.samples  = sa.s_aggr.sum_cnt;
    return true;
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
bool 
runtime_stats::get_packet_in_s5(uint64_t swid, stats_snapshot& s_in)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  

    s_in.last_s = sa.s5_aggr.last_s();
    s_in.max_s  = sa.s5_aggr.max;
    s_in.avg_s  = sa.s5_aggr.tot_avg();

    s_in.samples  = sa.s5_aggr.sum_cnt;
    return true;
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
bool 
runtime_stats::get_packet_in_min(uint64_t swid, stats_snapshot& s_in)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  

    s_in.last_s = sa.min_aggr.last_s();
    s_in.max_s  = sa.min_aggr.max;
    s_in.avg_s  = sa.min_aggr.tot_avg();

    s_in.samples  = sa.min_aggr.sum_cnt;
    return true;
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
int 
runtime_stats::get_packet_in_s_history(uint64_t swid, std::list<float>&
        results)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  
    
    if(sa.s_aggr.sum_queue.size() == 0){
        return 0;
    }
    for(std::deque<float>::iterator iter = sa.s_aggr.sum_queue.begin();
            iter != sa.s_aggr.sum_queue.end(); ++iter){
        results.push_back(*iter);
    }

    return results.size();
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
int 
runtime_stats::get_packet_in_s5_history(uint64_t swid, std::list<float>&
        results)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  
    
    if(sa.s5_aggr.sum_queue.size() == 0){
        return 0;
    }
    for(std::deque<float>::iterator iter = sa.s5_aggr.sum_queue.begin();
            iter != sa.s5_aggr.sum_queue.end(); ++iter){
        results.push_back(*iter);
    }

    return results.size();
}
//---------------------------------------------------------------------

//---------------------------------------------------------------------
inline
int 
runtime_stats::get_packet_in_min_history(uint64_t swid, std::list<float>&
        results)
{
    if(switch_packet_in_stats.find(swid) ==
            switch_packet_in_stats.end()){
        return false;
    }

    stats_aggr& sa = switch_packet_in_stats[swid];  
    
    if(sa.min_aggr.sum_queue.size() == 0){
        return 0;
    }
    for(std::deque<float>::iterator iter = sa.min_aggr.sum_queue.begin();
            iter != sa.min_aggr.sum_queue.end(); ++iter){
        results.push_back(*iter);
    }

    return results.size();
}
//---------------------------------------------------------------------

}

#endif // -- RUNTIME_STATS_HH__
