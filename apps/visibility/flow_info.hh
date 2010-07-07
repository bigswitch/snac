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
#include "authenticator/flow-in.hh"
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
    uint32_t src_host;
    std::list<uint32_t> src_users;
    uint32_t dst_host;
    std::list<uint32_t> dst_users;

    //user_groups may not be distinct - the reader should union the list
    //(we avoid performing union every flow since multiple users are uncommon)
    std::vector<uint32_t> src_user_groups;
    std::vector<uint32_t> dst_user_groups;
    //host_groups may contain host, location, and switch groups
    std::vector<uint32_t> src_host_groups;
    std::vector<uint32_t> dst_host_groups;
    //addr_groups may contain dladdr and nwaddr groups
    boost::shared_ptr<std::vector<uint32_t> > src_addr_groups;
    boost::shared_ptr<std::vector<uint32_t> > dst_addr_groups;

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
        src_host(fie.source->host),
        dst_host(Authenticator::UNKNOWN_ID),
        src_host_groups(fie.source->hostgroups),
        src_addr_groups(fie.src_addr_groups),
        dst_addr_groups(fie.dst_addr_groups),
        policy_id(cur_policy)
    {
        BOOST_FOREACH(user_info user, fie.source->users) {
            src_users.push_back(user.user);
            BOOST_FOREACH(uint32_t ugroup, user.groups) {
                src_user_groups.push_back(ugroup);
            }
        }

        Flow_in_event::DestinationInfo dest = fie.destinations[dest_used];
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

        dst_host = dest.connector->host;
        dst_host_groups = dest.connector->hostgroups;
        BOOST_FOREACH(user_info user, dest.connector->users) {
            dst_users.push_back(user.user);
            BOOST_FOREACH(uint32_t ugroup, user.groups) {
                dst_user_groups.push_back(ugroup);
            }
        }

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
