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

#ifndef NETINFO_MOD_EVENT_HH__
#define NETINFO_MOD_EVENT_HH__

#include <boost/noncopyable.hpp>

#include "event.hh"

#include "netinet++/ethernetaddr.hh"
#include "netinet++/datapathid.hh"
#include "netinet++/ipaddr.hh"

namespace vigil {

struct NetInfo_mod_event
    : public Event,
      boost::noncopyable
{

    NetInfo_mod_event(
            ethernetaddr, ipaddr, 
            datapathid, int, bool, bool);

    // -- only for use within python
    NetInfo_mod_event();

    static const Event_name static_get_name() {
        return "NetInfo_mod_event";
    }


    ethernetaddr dladdr; // Interface MAC address
    ipaddr       nwaddr; // IP address in host byte order
    datapathid dpid;     // the datapathid of the connected switch
    int port;            // the connected switch port in host byte order
    bool is_router;      // True if dladdr is a router interface
    bool is_gateway;     // True if dladdr is a gateway interface

}; // struct Host_mod_event

} // namespace vigil

#endif  // -- NETINFO_MOD_EVENT_HH__
