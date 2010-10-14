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
%module "nox.ext.apps.directory.pydirmanager"

%{
#include "aggregate-stats-in.hh"
#include "desc-stats-in.hh"
#include "bootstrap-complete.hh"
#include "datapath-join.hh"
#include "datapath-leave.hh"
#include "echo-request.hh"
#include "flow-removed.hh"
#include "flow-mod-event.hh"
#include "switch-mgr.hh"
#include "switch-mgr-join.hh"
#include "switch-mgr-leave.hh"
#include "packet-in.hh"
#include "port-stats-in.hh"
#include "port-status.hh"
#include "table-stats-in.hh"
#include "pyrt/pycontext.hh"
#include "pyrt/pyevent.hh"
#include "pyrt/pyglue.hh"

#include "group_change_event.hh"
#include "group_event.hh"
#include "location_del_event.hh"
#include "principal_event.hh"
#include "pydirmanager.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%import "netinet/netinet.i"
%import(module="nox.coreapps.pyrt.pycomponent") "pyrt/event.i"

%include "common-defs.i"
%include "std_string.i"
%include "directory.i"
%include "pydirmanager.hh"

struct Principal_name_event
    : public Event
{
    Principal_name_event(Directory::Principal_Type type,
                         const std::string&, const std::string&);

    Principal_name_event();

    static const std::string static_get_name();

    Directory::Principal_Type type;
    std::string   oldname;
    std::string   newname;  // set to "" if principal name deleted

%pythoncode
%{
    def __str__(self):
        return 'Principal_name_event '+ 'type: '+str(self.type) +\
               ' , oldname: ' + str(self.oldname) +\
               ' , newname: ' + str(self.newname) + ']'
%}

%extend {

    static void fill_python_event(const Event& e, PyObject* proxy) const 
    {
        const Principal_name_event& pe = dynamic_cast<const Principal_name_event&>(e);

        pyglue_setattr_string(proxy, "type", to_python((uint32_t)(pe.type)));
        pyglue_setattr_string(proxy, "oldname", to_python(pe.oldname));
        pyglue_setattr_string(proxy, "newname", to_python(pe.newname));

        ((Event*)SWIG_Python_GetSwigThis(proxy)->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr;
        pyctxt->register_event_converter<Principal_name_event>
            (&Principal_name_event_fill_python_event);
    }
}

};

struct Group_name_event
    : public Event
{
    Group_name_event(Directory::Group_Type type,
                     const std::string&, const std::string&);

    Group_name_event();

    static const std::string static_get_name();

    Directory::Group_Type type;
    std::string   oldname;
    std::string   newname;  // set to "" if group name deleted

%pythoncode
%{
    def __str__(self):
        return 'Group_name_event '+ 'type: '+str(self.type) +\
               ' , oldname: ' + str(self.oldname) +\
               ' , newname: ' + str(self.newname) + ']'
%}

%extend {

    static void fill_python_event(const Event& e, PyObject* proxy) const 
    {
        const Group_name_event& pe = dynamic_cast<const Group_name_event&>(e);

        pyglue_setattr_string(proxy, "type", to_python((uint32_t)(pe.type)));
        pyglue_setattr_string(proxy, "oldname", to_python(pe.oldname));
        pyglue_setattr_string(proxy, "newname", to_python(pe.newname));

        ((Event*)SWIG_Python_GetSwigThis(proxy)->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr;
        pyctxt->register_event_converter<Group_name_event>
            (&Group_name_event_fill_python_event);
    }
}

};

struct Group_change_event
    : public Event
{
    enum Change_Type {
        ADD_PRINCIPAL,
        DEL_PRINCIPAL,
        ADD_SUBGROUP,
        DEL_SUBGROUP
    };

    Group_change_event(Directory::Group_Type,
                       const std::string&, Change_Type, const std::string&);

    Group_change_event();

    static const std::string static_get_name();

    Directory::Group_Type type;     // Group's type
    std::string   group_name;                     // Group's name
    Change_Type   change_type;                    // Type of change
    std::string   change_name;                    // Entity added/deleted

%pythoncode
%{
    def __str__(self):
        return 'Group_change_event '+ 'type: '+str(self.type) +\
               ' , group name: ' + str(self.group_name) +\
               ' , change type: ' + str(self.change_type) +\
               ' , change name: ' + str(self.change_name) + ']'
%}

%extend {

    static void fill_python_event(const Event& e, PyObject* proxy) const 
    {
        const Group_change_event& gce = dynamic_cast<const Group_change_event&>(e);

        pyglue_setattr_string(proxy, "type", to_python((uint32_t)(gce.type)));
        pyglue_setattr_string(proxy, "group_name", to_python(gce.group_name));
        pyglue_setattr_string(proxy, "change_type", to_python((uint32_t)(gce.change_type)));
        pyglue_setattr_string(proxy, "change_name", to_python(gce.change_name));

        ((Event*)SWIG_Python_GetSwigThis(proxy)->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr;
        pyctxt->register_event_converter<Group_change_event>
            (&Group_change_event_fill_python_event);
    }
}

};

struct Location_delete_event
    : public Event
{
    Location_delete_event(const std::string&, const std::string&,
                          const datapathid&, uint16_t);

    Location_delete_event();

    static const std::string static_get_name();

    std::string   oldname;
    std::string   newname;
    datapathid    dpid;
    uint16_t      port;

%pythoncode
%{
    def __str__(self):
        return 'Location_delete_event '+\
               ' , oldname: ' + str(self.oldname) +\
               ' , newname: ' + str(self.newname) +\
               ' , dpid: ' + str(self.dpid) + ' , port: ' + str(self.port) + ']'
%}

%extend {

    static void fill_python_event(const Event& e, PyObject* proxy) const 
    {
        const Location_delete_event& le = dynamic_cast<const Location_delete_event&>(e);

        pyglue_setattr_string(proxy, "oldname", to_python(le.oldname));
        pyglue_setattr_string(proxy, "newname", to_python(le.newname));
        pyglue_setattr_string(proxy, "dpid", to_python(le.dpid));
        pyglue_setattr_string(proxy, "port", to_python(le.port));

        ((Event*)SWIG_Python_GetSwigThis(proxy)->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr;
        pyctxt->register_event_converter<Location_delete_event>
            (&Location_delete_event_fill_python_event);
    }
}

};

%pythoncode
%{
    from nox.lib.core import Component

    class PyDirManager(Component):
        def __init__(self, ctxt):
            Component.__init__(self, ctxt)
            self.dm = PyDirectoryManager(ctxt)
        
        def configure(self, configuration):
            self.dm.configure(configuration)
            Principal_name_event.register_event_converter(self.ctxt)
            Group_name_event.register_event_converter(self.ctxt)
            Group_change_event.register_event_converter(self.ctxt)
            Location_delete_event.register_event_converter(self.ctxt)

        def install(self):
            self.dm.install()

        def getInterface(self):
            return str(PyDirManager)

        def set_py_dm(self, dm_):
            return self.dm.set_py_dm(dm_)

        def set_create_dp(self, dp_):
            return self.dm.set_create_dp(dp_)

        def set_create_eth(self, eth_):
            return self.dm.set_create_eth(eth_)

        def set_create_ip(self, ip_):
            return self.dm.set_create_ip(ip_)
        
        def set_create_cidr(self, cidr_):
            return self.dm.set_create_cidr(cidr_)
        
        def set_create_cred(self, cred_):
            return self.dm.set_create_cred(cred_)

    def getFactory():
        class Factory():
            def instance(self, context):
                return PyDirManager(context)

        return Factory()
%}
