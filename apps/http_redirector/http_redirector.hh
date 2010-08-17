#ifndef HTTP_REDIRECTOR_HH
#define HTTP_REDIRECTOR_HH

#include <string>

#include "authenticator/flow_in.hh"
#include "authenticator/flow_util.hh"
#include "boost/format.hpp"
#include "config.h"
#include "component.hh"
#include "configuration/properties.hh"
#include "event.hh"
#include "flow.hh"
#include "hash_map.hh"
#include "netinet++/ethernet.hh"
#include "netinet++/ip.hh"
#include "redirected_flow_cache.hh"
#include "storage/transactional-storage.hh"

namespace vigil {
namespace applications {

class Http_redirector
    : public container::Component {
public:
    static const int RESP_BUF_SZ = 1518;

    Http_redirector(const container::Context*,
                    const json_object*);

    void configure(const container::Configuration*);
    void install();
    static void getInstance(const container::Context*, Http_redirector *&);

    void redirect_http_request(const Flow_in_event &fi);

    Redirected_flow_cache &get_flow_cache() { return rd_flow_cache; }

    void load_properties();

private:
    void props_load_cb();
    void props_load_eb();

    std::string get_redirect_payload(uint64_t cookie);
    ip_* init_response_buffer(ethernet *eth_stim);
    void send_response_buffer(datapathid datapath_id, uint16_t in_port);
    Disposition handle_dp_join(const Event& e);

    storage::Async_transactional_storage* storage;
    Flow_util *flow_util;
    Redirected_flow_cache rd_flow_cache;

    uint16_t ip_id;               //the IPID for the next packet
    Nonowning_buffer resp_buf;    //a reusable buffer for outbound packets
    uint8_t raw_buf[RESP_BUF_SZ]; //the underlying storage for resp_buf

    // Parameters from configuration
    configuration::Properties *props;
    bool props_dirty;
    bool props_set;
    size_t redir_payload_sz;  //=size(header(url) + html(title,body))
};


} // namespace applications
} // namespace vigil


#endif /* HTTP_REDIRECTOR_HH */
