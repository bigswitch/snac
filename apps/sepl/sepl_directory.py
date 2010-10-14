# Copyright 2008 (C) Nicira, Inc.

from twisted.python import log
from twisted.internet import defer

from nox.lib.core import Component
from nox.lib.netinet import netinet
from nox.lib.directory import Directory, SwitchInfo, LocationInfo, NetInfo, \
    HostInfo, UserInfo, GroupInfo

from nox.ext.apps.directory.directorymanager import directorymanager, demangle_name
from nox.ext.apps.directory.pydirmanager import Principal_name_event
from nox.ext.apps.directory.pydirmanager import Group_name_event
from nox.ext.apps.directory.simple_directory import simple_directory 

from nox.coreapps.pyrt.pycomponent import CONTINUE

SEPL_DIRECTORY_NAME = 'sepl_directory'
SEPL_DIRECTORY_TYPE = 'sepl_directory'

# poor man's singleton instance and static methods to be used by principals.py
__instance__ = None


# Registration methods are used to load up principles on startup.  
# Runtime variants of these methods return deferred objects since
# they're expected to follow the asyncronous model

def register_switch(name, dpid):
    if not isinstance(dpid, netinet.datapathid):
        dpid = netinet.create_datapathid_from_host(dpid)
    return __instance__.add_switch(SwitchInfo(name, dpid))

# dpid can be switch name

def register_location(name, dpid, port, port_name):
    if isinstance(dpid, basestring):
        d = __instance__.get_switch(dpid)
        d.addCallback(register_location2, name, dpid, port, port_name)
        return d
    if not isinstance(dpid, netinet.datapathid):
        dpid = netinet.create_datapathid_from_host(dpid)
    return __instance__.add_location(LocationInfo(name, dpid, port, port_name))

def register_location2(switch_info, name, dpid, port, port_name):
    if switch_info == None:
        return defer.fail(Exception('Cannot register location - switch does not exist.'))
    return __instance__.add_location(LocationInfo(name, switch_info.dpid, port, port_name))

def register_host(name, dpid=None, port=None, dladdr=None, is_router=False, is_gateway=False, nwaddr=None):
    ninfos = []
    if dpid != None or port != None:
        if not isinstance(dpid, netinet.datapathid):
            dpid = netinet.create_datapathid_from_host(dpid)
        ninfos.append(NetInfo(dpid, port))
    if dladdr != None:
        if not isinstance(dladdr, netinet.ethernetaddr):
            dladdr = netinet.create_eaddr(dladdr)
        ninfos.append(NetInfo(None, None, dladdr, None, is_router, is_gateway))
    if nwaddr != None:
        ninfos.append(NetInfo(None, None, None, nwaddr))
    return __instance__.add_host(HostInfo(name, netinfos=ninfos))

def register_user(name):
    return __instance__.add_user(UserInfo(name))

# Register principal group with name 'name'.  Group should be a list
# of principal names and a list of subgroup names.

def __get_group_info__(name, desc, principals, subgroups):
    n = SEPL_DIRECTORY_NAME + ';'
    mprincipals = []
    msubgroups = []
    for p in principals:
        if ';' not in p:
            mprincipals.append(n + p)
        else:
            mprincipals.append(p)
    for s in subgroups:
        if ';' not in s:
            msubgroups.append(n + s)
        else:
            msubgroups.append(s)
    return GroupInfo(name, desc, mprincipals, msubgroups)

def register_switch_group(name, description, principals, subgroups):
    return __instance__.add_group(Directory.SWITCH_PRINCIPAL_GROUP, 
            __get_group_info__(name, description, principals, subgroups))

def register_location_group(name, description, principals, subgroups):
    return __instance__.add_group(Directory.LOCATION_PRINCIPAL_GROUP, 
            __get_group_info__(name, description, principals, subgroups))

def register_host_group(name, description, principals, subgroups):
    return __instance__.add_group(Directory.HOST_PRINCIPAL_GROUP,
            __get_group_info__(name, description, principals, subgroups))

def register_user_group(name, description, principals, subgroups):
    return __instance__.add_group(Directory.USER_PRINCIPAL_GROUP,
            __get_group_info__(name, description, principals, subgroups))

def register_dladdr_group(name, description, principals, subgroups):
    eths = [ netinet.create_eaddr(p) for p in principals ]
    n = SEPL_DIRECTORY_NAME + ';'
    sgs = []
    for s in subgroups:
        if ';' not in s:
            sgs.append(n+s)
        else:
            sgs.append(s)
    return __instance__.add_group(Directory.DLADDR_GROUP,
                                  GroupInfo(name, description, eths, sgs))

def register_nwaddr_group(name, description, principals, subgroups):
    ips = [ netinet.create_ipaddr(p) for p in principals ]
    n = SEPL_DIRECTORY_NAME + ';'
    sgs = []
    for s in subgroups:
        if ';' not in s:
            sgs.append(n+s)
        else:
            sgs.append(s)
    return __instance__.add_group(Directory.NWADDR_GROUP,
                                  GroupInfo(name, description, ips, sgs))



class sepl_directory(Component, simple_directory):

    def __init__(self, ctxt):
        simple_directory.__init__(self)
        
        # poor man's singleton
        global __instance__
        if __instance__ != None:
            raise Exception("sepl_directory already instantiated")
        Component.__init__(self, ctxt)
        __instance__ = self
        
        self.restricted_names.add(None)

    def install(self):
        self._dm = self.resolve(directorymanager)
        self.name = SEPL_DIRECTORY_NAME
        # Attempt to import "principals" and set ourselves within the
        # namespace
        try:
            import principals
        except ImportError, e:
            log.err('Could not import principals %s' % str(e))
        d = self._dm.register_directory_component(self)
        d.addCallback(self._registered_with_dm)
        return d

    def _registered_with_dm(self, res):
        #Listen for name events to keep global groups up to date
        self.register_handler(Principal_name_event.static_get_name(),
                self.renamed_principal)
        self.register_handler(Group_name_event.static_get_name(),
                self.renamed_group)
        d = self._dm.add_configured_directory(SEPL_DIRECTORY_NAME,
                self.get_type(), 0, 0, ignore_if_dup_name=True)
        return d

    def getType(self):
        return SEPL_DIRECTORY_TYPE

    def getInterface(self):
        return str(sepl_directory)

    def renamed_principal(self, event):
        if demangle_name(event.oldname)[0] == SEPL_DIRECTORY_NAME:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        self.rename_group_member(None, event.type, event.oldname, 
                event.newname)
        return CONTINUE

    def renamed_group(self, event):
        if demangle_name(event.oldname)[0] == SEPL_DIRECTORY_NAME:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        self.rename_group_subgroup(None, event.type, event.oldname,
                event.newname)
        return CONTINUE

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return sepl_directory(ctxt)

    return Factory()
