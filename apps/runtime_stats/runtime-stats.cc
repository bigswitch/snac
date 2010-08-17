/*
 *
 */

#include "runtime-stats.hh"

#include <boost/bind.hpp>
#include <iostream>

#include "assert.hh"

#include "datapath-join.hh"
#include "datapath-leave.hh"
#include "packet-in.hh"
#include "flow-expired.hh"
#include "flow-mod-event.hh"

#include "vlog.hh"

using namespace std;
using namespace vigil;

static Vlog_module lg("runtime-stats");

void
runtime_stats::register_callbacks()
{
    // packets/seconds
    controller::register_handler(
            Packet_in_event::static_get_type(),
            boost::bind(&runtime_stats::packet_in, this, _1));

    // flow setup/timeout events
    controller::register_handler(
            Flow_mod_event::static_get_type(),
            boost::bind(&runtime_stats::flow_mod, this, _1));
    controller::register_handler(
            Flow_expired_event::static_get_type(),
            boost::bind(&runtime_stats::flow_exp, this, _1));

    // Datapath join/leave events
    controller::register_handler(Datapath_join_event::static_get_type(),
            boost::bind(&runtime_stats::dp_join, this, _1), 0);
    controller::register_handler(Datapath_leave_event::static_get_type(),
            boost::bind(&runtime_stats::dp_leave, this, _1), 0);

    // Timer to print out results periodically
    timeval tv = {5,0};
    controller::post_timer(boost::bind(&runtime_stats::timer, this), tv);
}

void
runtime_stats::timer()
{
    timeval tv;
    ::gettimeofday(&tv, 0);

    for (hash_map<uint64_t, stats_aggr>::iterator iter = switch_packet_in_stats.begin();
            iter != switch_packet_in_stats.end();
            ++iter){

        iter->second.rotate(tv);
        cout << iter->first  << ":" << endl;
        cout << "\tTotal: " << iter->second.tot_aggr.val << endl;
        cout << "\tPckt/s : " 
             << iter->second.s_aggr.last_s() << " : " 
             << iter->second.s_aggr.max
             << " : " << iter->second.s_aggr.tot_avg() << endl;
        cout << "\tPckt/min : " 
             << iter->second.min_aggr.last_s() << " : " 
             << iter->second.min_aggr.max
             << " : " << iter->second.min_aggr.tot_avg() << endl;
        cout << "\tPckt/5s : " 
             << iter->second.s5_aggr.last_s() << " : " 
             << iter->second.s5_aggr.max
             << " : " << iter->second.s5_aggr.tot_avg() << endl;
        if (switch_outstanding_flows.find(iter->first) !=
                switch_outstanding_flows.end()){
            cout << "\tFlows : " << switch_outstanding_flows[iter->first]
                 << endl;
        }
    }

    struct timeval ntv = {5,0};
    controller::post_timer(boost::bind(&runtime_stats::timer, this), ntv);
}

Disposition 
runtime_stats::packet_in(const Event& e)
{
    const Packet_in_event& pi = assert_cast<const Packet_in_event&>(e);

    timeval tv;
    ::gettimeofday(&tv, 0);

    switch_packet_in_stats[pi.datapath_id.as_host()].inc(tv);
    return CONTINUE;
}

Disposition
runtime_stats::flow_mod(const Event& e)
{
    const Flow_mod_event& fm = assert_cast<const Flow_mod_event&>(e);

    if(fm.get_flow_mod()->command == OFPFC_DELETE ||
       fm.get_flow_mod()->command == OFPFC_DELETE_STRICT  ){
        // XXX May delete multiple flows ... 
        switch_outstanding_flows[fm.datapath_id.as_host()] --;
        return CONTINUE;
    }

    timeval tv;
    ::gettimeofday(&tv, 0);

    switch_flow_events[fm.datapath_id.as_host()].inc(tv);
    switch_outstanding_flows[fm.datapath_id.as_host()] ++;

    return CONTINUE;
}

Disposition
runtime_stats::flow_exp(const Event& e)
{
    const Flow_expired_event& fe = assert_cast<const Flow_expired_event&>(e);
    uint64_t dpid = fe.datapath_id.as_host();

    timeval tv;
    ::gettimeofday(&tv, 0);

    switch_flow_events[dpid].inc(tv);

    if(switch_outstanding_flows.find(dpid) != 
            switch_outstanding_flows.end()){

        if (switch_outstanding_flows[dpid] >=0 ){
            switch_outstanding_flows[dpid] --;
        }else{
            lg.warn("flow count negative for switch %llx", dpid);
        }
    }
    return CONTINUE;
}

Disposition 
runtime_stats::dp_join(const Event& e)
{
    timeval tv;
    ::gettimeofday(&tv, 0);

    switch_events.inc(tv);

    const Datapath_join_event& sf 
                = assert_cast<const Datapath_join_event&>(e);
    switch_outstanding_flows[sf.datapath_id.as_host()] = 0;
    switch_packet_in_stats[sf.datapath_id.as_host()];

    return CONTINUE;
}

Disposition 
runtime_stats::dp_leave(const Event& e)
{
    timeval tv;
    ::gettimeofday(&tv, 0);

    switch_events.inc(tv);

    const Datapath_leave_event& dl = assert_cast<const Datapath_leave_event&>(e);
    uint64_t dpid = dl.datapath_id.as_host();
    assert(switch_packet_in_stats.find(dpid) != switch_packet_in_stats.end());

    stats_aggr& s1 = switch_packet_in_stats[dpid];
    cout << " S:  max: "  
        << s1.s_aggr.max << " min: "
        << s1.s_aggr.min << " avg: "
        << s1.s_aggr.tot_avg() << endl;

    switch_packet_in_stats.erase(dpid);
    switch_outstanding_flows.erase(dpid);
    switch_flow_events.erase(dpid);

    return CONTINUE;
}
