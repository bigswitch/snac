#include "restracker.hh"

#include <boost/bind.hpp>
#include <inttypes.h>
#include <cstdio>
#include <iostream>

#include "flow.hh"
#include "buffer.hh"
#include "kernel.hh"
#include "assert.hh"
#include "packet-in.hh"

#include "netinet++/ethernet.hh"

#include "vlog.hh"


namespace vigil {
namespace applications {

using namespace std;

restracker::restracker(const container::Context* c,
                       const json_object*)
    : Component(c)
{
    sw.reset_countdown_timer(COUNTDOWN_DURATION);
}

void
restracker::getInstance(const container::Context* ctxt,
                           restracker*& h)
{
    h = dynamic_cast<restracker*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(restracker).name())));
}

void
restracker::configure(const container::Configuration*)
{
    register_handler<Packet_in_event>
        (boost::bind(&restracker::handle_packet_in, this, _1));
}

void
restracker::install()
{
}

Disposition
restracker::handle_packet_in(const Event& e)
{
    const Packet_in_event& pi = assert_cast<const Packet_in_event&>(e);
    
    uint64_t sw_port = pi.datapath_id.as_host();
    sw_port |= ((uint64_t)pi.in_port) << 48;

    Flow flow(htons(pi.in_port), *(pi.buf));

    // Ignore LLDP packets ...
    // XXX Should we check that they're being sent to the
    // NDB multicast destination as well?
    if (flow.dl_type == ethernet::LLDP){
        return CONTINUE;
    }

    int& hcnt = hosts[sw_port][flow.dl_src.hb_long()];
    hcnt ++;
     // if  ( hcnt > HOST_PACKET_LIMIT) {
     // }

     // cout << flow.dl_src << " : " << hcnt << endl;

    if (sw.time_to_finish() < 1){
        hosts.clear();
        sw.reset_countdown_timer(COUNTDOWN_DURATION);
    }


    return CONTINUE;
}

} // namespace vigil
} // namespace applications


REGISTER_COMPONENT(vigil::container::Simple_component_factory<vigil::applications::restracker>,
                   vigil::applications::restracker);
