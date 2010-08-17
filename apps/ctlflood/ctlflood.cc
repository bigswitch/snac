#include <netinet/in.h>

#include <boost/bind.hpp>
#include <boost/shared_array.hpp>

#include "assert.hh"
#include "component.hh"
#include "packet-in.hh"
#include "vlog.hh"

using namespace vigil;
using namespace vigil::container;

namespace {

Vlog_module lg("ctlflood");

class CtlFlood
    : public Component 
{

public:
    CtlFlood(const Context* c,
             const json_object*) 
        : Component(c) { }

    void configure(const Configuration*) {
        register_handler<Packet_in_event>
            (boost::bind(&CtlFlood::handler, this, _1));
    }

    Disposition handler(const Event& e) {
        const Packet_in_event& pi = assert_cast<const Packet_in_event&>(e);
        datapathid dpid    = pi.datapath_id;
        uint32_t buffer_id = pi.buffer_id;
        
        /* Send out packet if necessary. */
        if (buffer_id == UINT32_MAX) {
            if (pi.total_len != pi.get_buffer()->size()) {
                /* Control path didn't buffer the packet and didn't send us
                 * the whole thing--what gives? */
                lg.dbg("total_len=%zu data_len=%zu\n",
                       pi.total_len, pi.get_buffer()->size());
                return CONTINUE;
            }

            send_openflow_packet(dpid, *pi.get_buffer(), OFPP_FLOOD,pi.in_port,
                                 true);
        } else {
            send_openflow_packet(dpid, buffer_id, OFPP_FLOOD, pi.in_port, 
                                 true);
        }
        
        return CONTINUE;
    }

    void install() {

    }
};

REGISTER_COMPONENT(container::Simple_component_factory<CtlFlood>, CtlFlood);

} // unnamed namespace
