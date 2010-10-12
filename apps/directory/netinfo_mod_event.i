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
%{
#include "bootstrap-complete.hh"
#include "datapath-join.hh"
#include "datapath-leave.hh"
#include "flow-removed.hh"
#include "flow-mod-event.hh"
#include "netinfo_mod_event.hh"
#include "aggregate-stats-in.hh"
#include "desc-stats-in.hh"
#include "table-stats-in.hh"
#include "port-stats-in.hh"
#include "packet-in.hh"
#include "port-status.hh"
#include "echo-request.hh"
#include "pyrt/pycontext.hh"
#include "pyrt/pyevent.hh"
#include "pyrt/pyglue.hh"
#include "switch-mgr-leave.hh"
#include "switch-mgr-join.hh"

using namespace vigil;
%}

%import "netinet/netinet.i"
%import "pyrt/event.i"

%include "common-defs.i"
%include "std_string.i"
%include "cstring.i"

struct NetInfo_mod_event
    : public Event
{

    NetInfo_mod_event(
            ethernetaddr, ipaddr, 
            datapathid, int, bool, bool);



    ethernetaddr   dladdr; // Interface MAC address
    ipaddr         nwaddr; // IP address in host byte order
    datapathid     dpid;   // the datapathid of the connected switch
    int port;            // the connected switch port in host byte order
    bool is_router;      // True if dladdr is a router interface
    bool is_gateway;     // True if dladdr is a gateway interface

    static const std::string static_get_name();

%extend {
    static void fill_python_event(const Event& e, PyObject* proxy) 
    {
        const NetInfo_mod_event& le = dynamic_cast<const NetInfo_mod_event&>(e);
        
        pyglue_setattr_string(proxy, "dladdr", to_python(le.dladdr));
        pyglue_setattr_string(proxy, "nwaddr", to_python(le.nwaddr));
        pyglue_setattr_string(proxy, "dpid", to_python(le.dpid));
        pyglue_setattr_string(proxy, "port", to_python(le.port));
        pyglue_setattr_string(proxy, "is_router", to_python(le.is_router));
        pyglue_setattr_string(proxy, "is_gateway", to_python(le.is_gateway));

        SwigPyObject* swigo = SWIG_Python_GetSwigThis(proxy);
        ((Event*)swigo->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        SwigPyObject* swigo = SWIG_Python_GetSwigThis(ctxt);
        if (!swigo || !swigo->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)swigo->ptr;
        pyctxt->register_event_converter<NetInfo_mod_event>
            (&NetInfo_mod_event_fill_python_event);
    }
};

};

