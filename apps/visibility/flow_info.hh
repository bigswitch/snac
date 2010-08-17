/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#ifndef FLOW_INFO_HH
#define FLOW_INFO_HH

#include <boost/foreach.hpp>
#include <boost/shared_ptr.hpp>
#include <list>
#include <vector>
#include <sys/time.h>

#include "flow.hh"

#include "authenticator/authenticator.hh"
#include "authenticator/flow_in.hh"
#include "netinet++/datapathid.hh"

namespace vigil {
namespace applications {

/*
 * Flow_info - composite of flow and the bindings and policy used to route it 
 *
 * Contains a subset of information from a Flow_in_event.  In particular,
 * routing data, data for destinations not taken, and meta-bindings data
 * are not included.
 *
 */
struct Flow_info {

    enum RoutingAction {
        ROUTED = 0,  //allowed by policy; routed to known destination
        BROADCASTED, //destination unknown, flooded
        NOT_ROUTED   //destination known, but no valid route exists
    };

    /* flow info */
    uint64_t id;
    timeval received;
    Flow flow;
    datapathid dpid;

    /* bindings info */
    uint64_t                                  src_host;
    boost::shared_ptr<GroupList>              src_dladdr_groups;
    boost::shared_ptr<GroupList>              src_nwaddr_groups;

    uint64_t                                  dst_host;
    boost::shared_ptr<GroupList>              dst_dladdr_groups;
    boost::shared_ptr<GroupList>              dst_nwaddr_groups;

    /* routing action */
    RoutingAction routing_action;

    /* policy info */
    uint32_t policy_id;
    hash_set<uint32_t> policy_rules;

    Flow_info(uint64_t uid, const Flow_in_event &fie, uint32_t cur_policy,
              uint32_t dest_used) :
        id(uid),
        received(fie.received),
        flow(fie.flow),
        dpid(fie.datapath_id),
        src_host(fie.src_host_netid->name),
        src_dladdr_groups(fie.src_dladdr_groups),
        src_nwaddr_groups(fie.src_nwaddr_groups),
        dst_host(fie.dst_host_netid->name),
        dst_dladdr_groups(fie.dst_dladdr_groups),
        dst_nwaddr_groups(fie.dst_nwaddr_groups),
        policy_id(cur_policy)
    {

        switch (fie.routed_to) {
        case Flow_in_event::NOT_ROUTED:
            routing_action = NOT_ROUTED;
            break;
        case Flow_in_event::BROADCASTED:
            routing_action = BROADCASTED;
            break;
        default:
            routing_action = ROUTED;
        }

        Flow_in_event::DestinationInfo dest = fie.dst_locations[dest_used];
        dst_host = dest.authed_location.location->name;

        policy_rules = dest.rules;
    }

    std::string routing_action_str(RoutingAction action) const {
        switch (action) {
        case ROUTED:
            return "routed";
        case BROADCASTED:
            return "broadcasted";
        case NOT_ROUTED:
            return "not routed";
        default:
            return "unknown";
        }

    }
};

} // namespace applications
} // namespace vigil


#endif /* FLOW_INFO_HH */
