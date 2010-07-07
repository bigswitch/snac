#include "redirected_flow_cache.hh"

#include <ctime>
#include <openssl/md5.h>
#include <openssl/rand.h>

#include "flow.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications;

namespace vigil {
namespace applications {

static const int REDIRECT_FLOW_CACHE_LIFETIME_SEC = 60;

Vlog_module log("Redirected_flow_cache");

static bool rand_seed_initialized = false;
static unsigned char rand_seed[8];

void
Redirected_flow_cache::expire_old_redirected_flows() {
    time_t now;
    time(&now);
    if (now - last_redirect_swap > REDIRECT_FLOW_CACHE_LIFETIME_SEC) {
        log.dbg("Now have %zu old redirected flows and %zu current",
                old_redirected_flows->size(), cur_redirected_flows->size());
        log.dbg("Expiring %zu old redirected flows from cache",
                old_redirected_flows->size());
        old_redirected_flows->clear();
        cur_redirected_flows->swap(*old_redirected_flows);
        log.dbg("Now have %zu old redirected flows and %zu current",
                old_redirected_flows->size(), cur_redirected_flows->size());
        last_redirect_swap = now;
    }
}

Redirected_flow*
Redirected_flow_cache::get_redirected_flow(const Flow &f, datapathid dpid)
{
    return get_redirected_flow(Redirected_flow::get_id_for_flow(f, dpid));
}

Redirected_flow*
Redirected_flow_cache::get_redirected_flow(uint64_t flowid)
{
    expire_old_redirected_flows();

    RdFlowMap::iterator rd_iter;
    rd_iter = old_redirected_flows->find(flowid);
    if (rd_iter != old_redirected_flows->end()) {
        pair<RdFlowMap::iterator, bool> p; 
        p = (*cur_redirected_flows).insert(std::make_pair(flowid,
                    rd_iter->second));
        old_redirected_flows->erase(rd_iter);
        log.dbg("Reviving flow from old table");
        log.dbg("Now have %zu old redirected flows and %zu current", 
                old_redirected_flows->size(), cur_redirected_flows->size());
        return &((p.first)->second);
    }
    else {
        rd_iter = cur_redirected_flows->find(flowid);
        if (rd_iter == cur_redirected_flows->end()) {
            return NULL;
        }
        return &rd_iter->second;
    }
}

Redirected_flow*
Redirected_flow_cache::update_redirected_flow(const Flow &f, datapathid dpid,
       const uint8_t *payload, int payload_offset, int payload_sz)
{
    Redirected_flow *ret = get_redirected_flow(f, dpid);
    if (ret == NULL) {
        log.dbg("Creating new flow");
        Redirected_flow newflow(f, dpid);
        ret = &newflow;
        uint64_t id = Redirected_flow::get_id_for_flow(newflow.flow, dpid);
        pair<RdFlowMap::iterator, bool> p; 
        p = (*cur_redirected_flows).insert(std::make_pair(id, newflow));
        ret = &((p.first)->second);
    }
    //log.dbg("Current payload_head (%lu): '%s'", 
    //        strlen((char*)ret->payload_head), 
    //        (char*)ret->payload_head);
    if (payload_offset < sizeof(ret->payload_head) - 1) {
        if (payload_offset + payload_sz < 
                sizeof (ret->payload_head) - 1) {
            log.dbg("copying entire (%d) payload starting at %d", payload_sz, 
                    payload_offset);
            memcpy(ret->payload_head + payload_offset, payload,
                    payload_sz);
        }
        else {
            log.dbg("copying subset (%zu) of payload starting at %d", 
                    sizeof(ret->payload_head) - payload_offset - 1, 
                    payload_offset);
            memcpy(ret->payload_head + payload_offset, payload,
                    sizeof(ret->payload_head) - payload_offset - 1);
        }
    }
    else {
        log.dbg("ignoring payload starting at %d (beyond buffer)", 
                payload_offset);
    }
    //log.dbg("New payload_head (%lu): '%s'", 
    //        strlen(ret->payload_head), 
    //        ret->payload_head);

    return ret;
}

static void 
init_rand_seed() {
    int status = RAND_pseudo_bytes(rand_seed, sizeof(rand_seed));
    if (status == -1) {
        log.err("No RAND methods implemented by configured libraries, "
                  "redirected flow cookies will be predictable.");
    }
    rand_seed_initialized = true;
}

uint64_t 
Redirected_flow::get_id_for_flow(const Flow &f, datapathid dpid) {
    if (!rand_seed_initialized) {
        init_rand_seed();
    }
    //we compute the flow id as: 64bits(md5(seed+dpid+hash(flow)))
    unsigned char md[MD5_DIGEST_LENGTH];
    MD5_CTX ctx;
    MD5_Init(&ctx);
    uint64_t flow_hash = f.hash_code();
    MD5_Update(&ctx, rand_seed, sizeof(rand_seed));
    MD5_Update(&ctx, &dpid, sizeof(dpid));
    MD5_Update(&ctx, &flow_hash, sizeof(flow_hash));
    MD5_Final(md, &ctx);
    uint64_t ret = *((uint64_t*)md);
    //log.dbg("Generating digest of flow %s: %lx", f.to_string().c_str(), ret);
    return ret;
}


} // namespace applications
} // namespace vigil


