/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "component.hh"
#include "netinfo_mod_event.hh"

#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;


namespace vigil {


NetInfo_mod_event::NetInfo_mod_event( ethernetaddr _dladdr, ipaddr _nwaddr, datapathid _dpid, int _port, 
        bool _is_router, bool _is_gateway):Event(static_get_name()),
dladdr(_dladdr), nwaddr(_nwaddr), dpid(_dpid), port(_port), is_router(_is_router), is_gateway(_is_gateway)
{
}

// -- only for use within python
NetInfo_mod_event::NetInfo_mod_event() : Event(static_get_name()) { }

}// namespace vigil

namespace {

static Vlog_module lg("netinfo_mod_event");

class NetInfo_mod_event_component
    : public Component {
public:
    NetInfo_mod_event_component(const Context* c,
                     const json_object*) 
        : Component(c) {
    }

    void configure(const Configuration*) {
    }

    void install() {
    }

private:
    
};

REGISTER_COMPONENT(container::Simple_component_factory<NetInfo_mod_event_component>, 
                   NetInfo_mod_event_component);

} // unnamed namespace
