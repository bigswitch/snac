/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#include "flow_cache.hh"

#include <boost/bind.hpp>
#include <boost/foreach.hpp>

#include "assert.hh"
#include "authenticator/flow_util.hh"
#include "authenticator/host_event.hh"
#include "bootstrap-complete.hh"
#include "flow.hh"
#include "netinet++/datapathid.hh"
#include "storage/transactional-storage-blocking.hh"
#include "vlog.hh"

#define DP_MASK 0xffffffffffffULL

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::configuration;
using namespace vigil::applications::storage;


namespace vigil {
namespace applications {

static const string PROPERTIES_SECTION("flow_cache_settings");
static const string CURRENT_POLICY_TABLE("current_policy");

static const int ALLOWED_FLOW_BUF_SZ = 200;
static const int DENIED_FLOW_BUF_SZ = 200;
static const int ALL_FLOW_BUF_SZ = 200;

static const int HOST_FLOW_BUF_SZ = 50;
static const int RULE_FLOW_BUF_SZ = 200;

static Vlog_module lg("flow_cache");

Flow_cache::Flow_cache(const container::Context* c, const xercesc::DOMNode*)
    : Component(c), cur_policy_id(0), next_flow_id(0),
      allowedflows(ALLOWED_FLOW_BUF_SZ), deniedflows(DENIED_FLOW_BUF_SZ),
      allflows(ALL_FLOW_BUF_SZ)
{
    //NOP
}

void
Flow_cache::configure(const container::Configuration* conf) {
    resolve(storage);
    resolve(authenticator);

    register_handler<Bootstrap_complete_event>(
            boost::bind(&Flow_cache::handle_bootstrap_complete, this, _1));
        
    register_handler<Flow_in_event>(
            boost::bind(&Flow_cache::handle_flow_in, this, _1));

    register_handler<Host_join_event>(
            boost::bind(&Flow_cache::handle_host_join_event, this, _1));
}

void
Flow_cache::install() {
    //don't need properties yet (phew!)
    //props = new Properties(storage, PROPERTIES_SECTION);
}

void
Flow_cache::getInstance(const container::Context* ctxt, Flow_cache*& h) {
    h = dynamic_cast<Flow_cache*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(Flow_cache).name())));
}

void
Flow_cache::update_policy_id(const Trigger_function &trigger_to_add) {
    //Get the current policy ID from CDB
    Sync_transactional_storage sstorage(storage);
    Sync_transactional_storage::Get_connection_result result =
            sstorage.get_connection();
    if (!result.get<0>().is_success()) {
        throw runtime_error("Can't access the transactional storage");
    }
    Sync_transactional_connection_ptr conn = result.get<1>();
    Query q;
    Sync_transactional_connection::Get_result get_result = 
            conn->get(CURRENT_POLICY_TABLE, q);
    if (get_result.get<0>().is_success()) {
        Sync_transactional_cursor::Get_next_result gn_result =
                (get_result.get<1>())->get_next();
        if (gn_result.get<0>().is_success()) {
            storage::Row row = gn_result.get<1>();
            Row::const_iterator iter = row.find("id");
            if (iter != row.end()) {
                cur_policy_id = boost::get<int64_t>(iter->second);
            }
        }
        (get_result.get<1>())->close();
    }
    if (trigger_to_add != NULL) {
        conn->put_trigger(CURRENT_POLICY_TABLE, false, trigger_to_add);
    }
}

void
Flow_cache::policy_updated_cb(const Trigger_id &tid, const Row &row,
        const Trigger_reason reason) {
    if (reason == storage::INSERT or reason == storage::MODIFY) {
        policyflows.clear();
        update_policy_id(
                boost::bind(&Flow_cache::policy_updated_cb, this, _1, _2, _3));
    }
}

Disposition
Flow_cache::handle_bootstrap_complete(const Event& e)
{
    update_policy_id(
            boost::bind(&Flow_cache::policy_updated_cb, this, _1, _2, _3));
    return CONTINUE;
}

Disposition
Flow_cache::handle_flow_in(const Event& e)
{
    const Flow_in_event& fie = assert_cast<const Flow_in_event&>(e);

    if (!fie.route_destinations.empty() &&
            fie.dst_locations[fie.routed_to].authed_location.location->name != 0) {
        //Don't report on flows destined for known locations behind a router;
        //we'll report on the flow that comes in from the router
        lg.dbg("Not caching flow destined for a router");
        return CONTINUE;
    }

    const boost::shared_ptr<vigil::Location> loc = (fie.route_source != NULL) ? fie.route_source : fie.src_location.location;
    if (loc->sw->dp != fie.datapath_id) {
        //Don't report on flows not from the originating switch or router
        lg.dbg("Not caching flow from intermediate switch");
        return CONTINUE;
    }

    uint32_t dest_used = 0;
    if (fie.fn_applied) {
        for (int i = fie.dst_locations.size()-1; i >= 0; --i) {
            Flow_in_event::DestinationInfo di = fie.dst_locations[i];
            //the function is on the first non-active destination
            if (fie.dst_locations[i].allowed == false) {
                dest_used = i;
                break;
            }
        }
    }
    else if (fie.route_destinations.empty() 
            && fie.routed_to != fie.NOT_ROUTED
            && fie.routed_to != fie.BROADCASTED)
    {
        dest_used = fie.routed_to;
    }
    else {
        BOOST_FOREACH(Flow_in_event::DestinationInfo di, fie.dst_locations) {
            if (di.allowed) {
                break;
            }
            dest_used += 1;
        }
        if (dest_used == fie.dst_locations.size()) {
            //no allows
            dest_used = 0;
        }
    }

    Flow_info_ptr fi = Flow_info_ptr(new Flow_info(next_flow_id++, fie,
                cur_policy_id, dest_used));

    //cache in system-wide buffers
    allflows.put(fi);
    if (fie.fn_applied || fie.dst_locations[dest_used].allowed) {
        allowedflows.put(fi);
    }
    else {
        deniedflows.put(fi);
    }

    //cache in source host buffer
    get_host_flow_buf(fie.src_host_netid->name, true)->put(fi);

    //cache in buffers for policy rules
    BOOST_FOREACH(uint32_t id, fie.dst_locations[dest_used].rules) {
        get_policy_flow_buf(cur_policy_id, id, true)->put(fi);
    }

    //cache in buffer for destination if flow was routed there
    if (fie.routed_to != fie.NOT_ROUTED) {
        uint64_t host_id = fie.dst_locations[dest_used].authed_location.location->name;
        get_host_flow_buf(host_id, true)->put(fi);
    }

    return CONTINUE;
}

Disposition
Flow_cache::handle_host_join_event(const Event& e)
{
    // For now, we have to maintain a counter of bindings for each host.
    // This should get a lot simplier when the authenticator is  refactored.
    
    const Host_join_event& he = assert_cast<const Host_join_event&>(e);

    uint64_t host_id = he.hostname;
    if (he.action == Host_join_event::JOIN) {
        host_ref_counts[host_id] += 1;
    }
    else {
        //Host_join_event::LEAVE
        host_ref_counts[host_id] -= 1;
        if (host_ref_counts[host_id] <= 0) {
            host_ref_counts.erase(host_id);
            hostflows.erase(host_id);
        }
    }

    return CONTINUE;
}

const FlowBuf_ptr
Flow_cache::get_host_flow_buf(string hostname) {
    /*uint64_t host_id = authenticator->get_id(hostname,
            Directory::HOST_PRINCIPAL, (Directory::Group_Type)0, true, false);
    return get_host_flow_buf(host_id, false);
    */
    // Copied over from SNAC. Still TODO
    return FlowBuf_ptr();
}

const FlowBuf_ptr
Flow_cache::get_host_flow_buf(uint64_t host_id, bool create) {
    FlowBuf_ptr hbuf;
    FlowBufMap::const_iterator fbentry = hostflows.find(host_id);
    if (fbentry != hostflows.end()) {
        return fbentry->second;
    }
    else if (create) {
        hbuf = FlowBuf_ptr(new FlowBuf(HOST_FLOW_BUF_SZ));
        hostflows[host_id] = hbuf;
        return hbuf;
    }
    else {
        return FlowBuf_ptr();
    }
}

const FlowBuf_ptr
Flow_cache::get_policy_flow_buf(uint32_t policy_id, uint32_t rule_id,
        bool create) {
    if (!create && policy_id != cur_policy_id) {
        //we only cache for rules in the current policy
        return FlowBuf_ptr();
    }
    FlowBufMap::const_iterator fbentry = policyflows.find(rule_id);
    if (fbentry != policyflows.end()) {
        return fbentry->second;
    }
    else if (create) {
        FlowBuf_ptr pbuf = FlowBuf_ptr(new FlowBuf(RULE_FLOW_BUF_SZ));
        policyflows[rule_id] = pbuf;
        return pbuf;
    }
    else {
        return FlowBuf_ptr();
    }
}


} // namespace applications
} // namespace vigil

REGISTER_COMPONENT(container::Simple_component_factory<Flow_cache>,
                           Flow_cache);
