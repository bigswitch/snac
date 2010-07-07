/*
 * Copyright 2008 (C) Nicira, Inc.
 */
#ifndef FLOW_CACHE_HH
#define FLOW_CACHE_HH

#include <boost/shared_ptr.hpp>
#include <string>
#include "hash_map.hh"

#include "authenticator/authenticator.hh"
#include "configuration/properties.hh"
#include "flow_info.hh"
#include "netinet++/datapathid.hh"
#include "static_ring_buf.hh"
#include "storage/transactional-storage.hh"

namespace vigil {
namespace applications {

typedef boost::shared_ptr<Flow_info> Flow_info_ptr;
typedef Static_ring_buf<Flow_info_ptr> FlowBuf;
typedef boost::shared_ptr<FlowBuf> FlowBuf_ptr;
typedef hash_map<uint32_t, FlowBuf_ptr> FlowBufMap;
typedef hash_map<uint32_t, uint32_t> HostRefCountMap;


class Flow_cache
    : public container:: Component {
public:
    Flow_cache(const container::Context*, const xercesc::DOMNode*);
    void configure(const container::Configuration*);
    void install();
    static void getInstance(const container::Context*, Flow_cache *&);

    const FlowBuf& get_allowed_flow_buf() { return allowedflows; }
    const FlowBuf& get_denied_flow_buf() { return deniedflows; }
    const FlowBuf& get_all_flow_buf() { return allflows; }
    const FlowBuf_ptr get_host_flow_buf(std::string hostname);
    const FlowBuf_ptr get_host_flow_buf(uint32_t host_id, bool create=false);
    const FlowBuf_ptr get_policy_flow_buf(uint32_t policy_id, uint32_t rule_id,
            bool create=false);

    uint32_t get_cur_policy_id() {return cur_policy_id;}

    inline bool get_group_type(uint32_t id, Directory::Group_Type & gtype) const
    {
        return authenticator->get_group_type(id, gtype);
    }

private:
    Disposition handle_flow_in(const Event& e);
    Disposition handle_bootstrap_complete(const Event& e);
    Disposition handle_host_event(const Event& e);

    void update_policy_id(const Trigger_function& trigger_to_add);
    void policy_updated_cb(const Trigger_id&, const Row&, const Trigger_reason);

    uint32_t cur_policy_id;
    uint64_t next_flow_id;
    HostRefCountMap host_ref_counts;

    FlowBuf allowedflows;
    FlowBuf deniedflows;
    FlowBuf allflows;

    FlowBufMap hostflows;
    FlowBufMap policyflows;

    Authenticator* authenticator;
    storage::Async_transactional_storage* storage;
    configuration::Properties *props;
};


} // namespace applications
} // namespace vigil


#endif /* FLOW_CACHE_HH */
