#ifndef REDIRECTED_FLOW_CACHE_HH
#define REDIRECTED_FLOW_CACHE_HH

#include "flow.hh"
#include "hash_map.hh"
#include "netinet++/datapathid.hh"

namespace vigil {
namespace applications {

static const int PAYLOAD_HEAD_SZ = 1460;

struct Redirected_flow {
    Flow flow;
    datapathid dpid;
    char payload_head[PAYLOAD_HEAD_SZ];
    bool is_initialized;

    Redirected_flow() : is_initialized(false) {
        // Constructor solely for python bindings
        memset(payload_head, 0, PAYLOAD_HEAD_SZ);
    }

    Redirected_flow(const Flow &inf, datapathid dpid_) : 
        flow(inf), dpid(dpid_), is_initialized(true)
    {
        memset(payload_head, 0, PAYLOAD_HEAD_SZ);
    }

    static uint64_t get_id_for_flow(const Flow &f, datapathid dpid);
};

typedef hash_map<uint64_t, Redirected_flow> RdFlowMap;

class Redirected_flow_cache {
public:
    Redirected_flow_cache() :
        cur_redirected_flows(&fm1), old_redirected_flows(&fm2) 
    {
        time(&last_redirect_swap);
    }

    Redirected_flow *get_redirected_flow(const Flow &f, datapathid dpid);
    Redirected_flow *get_redirected_flow(uint64_t flowid);
    Redirected_flow *update_redirected_flow(const Flow &f, datapathid dpid,
            const uint8_t *payload, int offset, int payload_sz);

private:
    void expire_old_redirected_flows();

    RdFlowMap fm1, fm2;
    RdFlowMap *cur_redirected_flows;
    RdFlowMap *old_redirected_flows;
    time_t last_redirect_swap;
};


} // namespace applications
} // namespace vigil


#endif /* REDIRECTED_FLOW_CACHE_HH */
