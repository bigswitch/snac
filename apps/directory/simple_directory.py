# Copyright 2008 (C) Nicira, Inc.
# 
# This file is part of NOX.
# 
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.

from twisted.python import log
from twisted.internet import defer
from nox.apps.directory.cidr_group_cache import cidr_group_cache
from nox.apps.directory.dir_utils import glob_to_regex,filter_list
from nox.apps.directory.directorymanager import is_mangled_name, mangle_name,\
         demangle_name, get_default_switch_name, get_default_loc_name
from nox.lib.core import Component
from nox.lib.netinet import netinet
from nox.lib.directory import Directory, SwitchInfo, LocationInfo, NetInfo, \
    HostInfo, UserInfo, GroupInfo, DirectoryException
from nox.lib.directory_factory import Directory_Factory
import re
import inspect
import copy 

# this is a simple in-memory directory, which has been refactored out of the 
# sepl_directory for wider use. It is NOT a component itself, but is meant to
# instantiated by other components that need a directory but do not require persistence

class simple_directory(Directory):

    def __init__(self):
        Directory.__init__(self)
        self.switches = {}
        self.switch_bindings = {}
        self.locations = {}
        self.location_bindings = {}
        self.hosts = {}
        self.host_loc_bindings = {}
        self.host_dl_bindings = {}
        self.host_nw_bindings = {}
        self.users = {}
        self.routers = {}
        self.gateways = {}
        self.restricted_names = set()
        self.groups = {}
        self.parent_groups = {}
        for group_type in Directory.ALL_GROUP_TYPES:
            self.groups[group_type] = {}
            self.parent_groups[group_type] = {}
        self.cidr_cache = cidr_group_cache()

    def get_type(self):
        return "simple directory"
    
    # a subclass should reimplement these two methods
    # if it can be configured via the web interface
    def get_config_params(self):
        return {}
    def set_config_params(self,params):
        return defer.succeed({}) # ignore any configuration 

    # by default, simple_directory is a singleton
    # to implement different directories, create a
    # new class that sub-classes simple_directory 
    def get_instance(self, name, config_id):
        return defer.succeed(self)

    def supports_multiple_instances(self):
        return False

    def get_status(self):
        return Directory.DirectoryStatus(Directory.DirectoryStatus.OK)

    def all_names_global(self):
        return False

    def supports_global_groups(self):
        return True

    def supported_auth_types(self):
      return ( Directory_Factory.AUTHORIZED_CERT_FP, )


    def _del_member_from_groups(self, retval, group_type, member_name):
        grouptbl = self.groups[group_type]
        def _del_member(groups):
            for groupname in groups:
                groupname = demangle_name(groupname)[1]
                if member_name in grouptbl[groupname].member_names:
                    grouptbl[groupname].member_names.remove(member_name)
            return retval
        d = self.get_group_membership(group_type, member_name)
        d.addCallback(_del_member)
        return d

    def rename_group_member(self, retval, principal_type, old_name, new_name):
        def _update_group_member(res):
            grouptbl = self.groups[gt]
            for groupname in res:
                if old_name in grouptbl[groupname].member_names:
                    grouptbl[groupname].member_names.remove(old_name)
                    if new_name:
                        grouptbl[groupname].member_names.append(new_name)
            return retval
        if principal_type in Directory.PRINCIPAL_TO_PRINCIPAL_GROUP:
            gt = Directory.PRINCIPAL_TO_PRINCIPAL_GROUP[principal_type]
            d = self.get_group_membership(gt, old_name)
            d.addCallback(_update_group_member)
            return d
        return defer.succeed(retval)

    def rename_group_subgroup(self, retval, group_type, old_name, new_name):
        grouptbl = self.groups[group_type]
        for group_name in self._get_group_parents_s(group_type, old_name):
            if old_name in grouptbl[group_name].subgroup_names:
                grouptbl[group_name].subgroup_names.remove(old_name)
                if new_name:
                    grouptbl[groupname].subgroup_names.append(new_name)
        return defer.succeed(retval)

    def rename_principal(self, principal_type, old_name, new_name):
        def _rename(pdict):
            if pdict.has_key(new_name):
                raise DirectoryException("Record with name '%s' already exists"
                                         %new_name, DirectoryException.RECORD_ALREADY_EXISTS)
            if not old_name in pdict:
                raise DirectoryException("No record found with name '%s'"
                        %old_name, DirectoryException.NONEXISTING_NAME)
            info = pdict[old_name]
            del pdict[old_name]
            info.name = new_name
            pdict[new_name] = info
            #update group membership
            return self.rename_group_member(copy.copy(pdict[new_name]),
                    principal_type, old_name, new_name)

        def _rename_switch_locations(switchinfo):
            """Rename locations with names beginning with old switch name"""
            def ren_locs(loc_names):
                switchname = switchinfo.name
                switchinfo.locations = []
                for loc_name in loc_names:
                    li = self.locations[loc_name]
                    def_name = get_default_loc_name(old_name, li.port_name)
                    if loc_name == def_name:
                        newname = get_default_loc_name(new_name, li.port_name)
                        self.locations.pop(loc_name)
                        li.name = newname
                        self.locations[newname] = li
                        li_copy = copy.deepcopy(li)
                        li_copy._old_name = loc_name
                        switchinfo.locations.append(li_copy)
                    else:
                        switchinfo.locations.append(
                                copy.deepcopy(self.locations[loc_name]))
                return switchinfo
            d = self.search_locations({'dpid' : switchinfo.dpid})
            d.addCallback(ren_locs)
            return d

        if principal_type == Directory.SWITCH_PRINCIPAL:
            d = _rename(self.switches)
            d.addCallback(_rename_switch_locations)
            return d
        elif principal_type == Directory.LOCATION_PRINCIPAL:
            return _rename(self.locations)
        elif principal_type == Directory.HOST_PRINCIPAL:
            return _rename(self.hosts)
        elif principal_type == Directory.USER_PRINCIPAL:
            return _rename(self.users)
        raise DirectoryException("Unsupported principal type '%s' in "
                "rename_principal" %principal_type)

    def rename_group(self, group_type, old_name, new_name):
        if not group_type in self.groups:
            raise DirectoryException("Unsupported group type '%s' in "
                    "rename_group" %group_type)
        grouptbl = self.groups[group_type]
        groupparenttbl = self.parent_groups[group_type]
        if grouptbl.has_key(new_name):
            raise DirectoryException("Record with name '%s' already exists"
                                     %new_name)
        if not old_name in grouptbl:
            raise DirectoryException("No record found with name '%s'"
                    %old_name)
        #update our group
        info = grouptbl[old_name]
        info.name = new_name
        del grouptbl[old_name]
        grouptbl[new_name] = info
        if group_type == Directory.NWADDR_GROUP:
            self.cidr_cache.ren_cidr(old_name, new_name)
        #update our parent group set
        if groupparenttbl.has_key(old_name):
            pgs = groupparenttbl[old_name]
            del groupparenttbl[old_name]
            groupparenttbl[new_name] = pgs
        #update groups referencing us as parent groups
        for subgroup_name in info.subgroup_names:
            groupparenttbl[subgroup_name].discard(old_name)
            groupparenttbl[subgroup_name].add(new_name)
        return defer.succeed(copy.copy(info))

    def switches_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_switch(self, switch_info):
        if switch_info.name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot add switch - ' 'invalid name.',
                    DirectoryException.OPERATION_NOT_PERMITTED))
        elif switch_info.dpid == None:
            return defer.fail(DirectoryException(
                    'Cannot add switch - dpid must be set.'))
        elif self.switches.has_key(switch_info.name):
            return defer.fail(DirectoryException(
                    'Cannot add switch - switch already exists.',
                    DirectoryException.RECORD_ALREADY_EXISTS))
        dpid = switch_info.dpid.as_host()
        if self.switch_bindings.has_key(dpid):
            return defer.fail(DirectoryException(
                    'Cannot add switch - dpid already bound.',
                    DirectoryException.RECORD_ALREADY_EXISTS))
        si = copy.deepcopy(switch_info)
        si.locations = []
        si._fp_credentials = [] 
        self.switches[si.name] = si
        self.switch_bindings[dpid] = si

        if hasattr(switch_info, 'locations'):
            for loc in switch_info.locations:
                self.add_location(loc)

        return defer.succeed(copy.deepcopy(switch_info))

    def modify_switch(self, switch_info):
        if switch_info.dpid == None:
            return defer.fail(DirectoryException(
                    'Cannot modify switch - dpid must be set.'))
        if not self.switches.has_key(switch_info.name):
            return defer.fail(DirectoryException(
                    'Cannot modify switch - does not exist.',
                    DirectoryException.RECORD_ALREADY_EXISTS))
        if switch_info.name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot modify switch %s.'
                    % switch_info.name,
                    DirectoryException.OPERATION_NOT_PERMITTED))
        dpid = switch_info.dpid.as_host()
        old_info = self.switches[switch_info.name]
        if switch_info.dpid != old_info.dpid:
            if self.switch_bindings.has_key(dpid):
                return defer.fail(DirectoryException(
                        'Cannot modify switch - dpid already bound.',
                        DirectoryException.RECORD_ALREADY_EXISTS))
            del self.switch_bindings[old_info.dpid.as_host()]
        
        if hasattr(old_info, '_fp_credentials') and \
            not hasattr(switch_info,'_fp_credentials'): 
          switch_info._fp_credentials = old_info._fp_credentials
        
        self.switches[switch_info.name] = switch_info
        self.switch_bindings[dpid] = switch_info
        return defer.succeed(copy.deepcopy(switch_info))

    def del_switch(self, switch_name):
        if not self.switches.has_key(switch_name):
            return defer.fail(DirectoryException(
                    'Cannot delete switch - does not exist.',
                    DirectoryException.NONEXISTING_NAME))
        if switch_name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot delete switch %s.'
                    % switch_name, DirectoryException.OPERATION_NOT_PERMITTED))
        ret = self.switches[switch_name]
        del self.switches[switch_name]
        del self.switch_bindings[ret.dpid.as_host()]

        #delete the associated locations
        locations = self.locations.values()
        filter_list(locations, lambda location : location.dpid != ret.dpid)
        ret.locations = locations
        for loc in locations:
            key = loc.dpid.as_host() + (loc.port << 48)
            del self.locations[loc.name]
            del self.location_bindings[key]
            #delete location from groups - ignore deferred result as the
            #call is actually synchronous
            self._del_member_from_groups(ret, Directory.LOCATION_PRINCIPAL,
                    mangle_name(self.name, loc))

        return self._del_member_from_groups(ret, Directory.SWITCH_PRINCIPAL,
                mangle_name(self.name, switch_name))

    def get_switch(self, switch_name, include_locations=False):
        if self.switches.has_key(switch_name):
            si = copy.deepcopy(self.switches[switch_name])
            if include_locations:
                locations = self.locations.values()
                filter_list(locations, lambda loc : loc.dpid != si.dpid)
                si.locations = locations
            return defer.succeed(si)
        elif switch_name in self.restricted_names:
            return defer.succeed(SwitchInfo(switch_name))
        return defer.succeed(None)

    def search_switches(self, query):
        checked = 0
        switches = None
        if query.has_key('name'):
            name = query['name']
            if self.switches.has_key(name):
                switches = [ self.switches[name] ]
            # FIXME
            elif name in self.restricted_names and len(query) == 1:
                return defer.succeed([name])
            else:
                switches = []
            checked = checked + 1

        if query.has_key('dpid'):
            dpid = query['dpid']
            if switches == None:
                key = dpid.as_host()
                if self.switch_bindings.has_key(key):
                    switches = [ self.switch_bindings[key] ]
                else:
                    switches = []
            else:
                filter_list(switches, lambda switch : switch.dpid != dpid)
            checked = checked + 1
        
        if query.has_key('name_glob'):
            regex_str = glob_to_regex(query['name_glob'])
            regex = re.compile(regex_str)
            if switches == None:
                switches = self.switches.values()
            filter_list(switches, lambda sw : not regex.search(sw.name) )
            checked = checked + 1
            
        if checked != len(query):
            raise DirectoryException('Unsupported query parameters',
                    DirectoryException.INVALID_QUERY)
        elif switches == None:
            return defer.succeed(self.switches.keys())
        return defer.succeed([switch.name for switch in switches])

    def locations_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_location(self, location_info):
        if location_info.name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot add location - invalid name.',
                    DirectoryException.OPERATION_NOT_PERMITTED))
        if location_info.dpid == None or location_info.port == None:
            return defer.fail(DirectoryException(
                    'Cannot add location - dpid and port must be set.'))
        if self.locations.has_key(location_info.name):
            return defer.fail(DirectoryException(
                    'Cannot add location - location already exists.',
                    DirectoryException.RECORD_ALREADY_EXISTS))
        key = location_info.dpid.as_host() + (location_info.port << 48)
        if self.location_bindings.has_key(key):
            return defer.fail(DirectoryException(
                    'Cannot add location - dpid/port already bound.',
                    DirectoryException.RECORD_ALREADY_EXISTS))

        if not self.switch_bindings.has_key(location_info.dpid.as_host()):
            def readd_loc(res, linfo):
                return self.add_location(linfo)
            si = SwitchInfo(get_default_switch_name(location_info.dpid),
                            location_info.dpid)
            d = self.add_switch(si)
            d.addCallback(readd_loc, location_info)
            
        li = copy.deepcopy(location_info)
        li._fp_credentials = [] 
        self.locations[location_info.name] = li
        self.location_bindings[key] = li
        return defer.succeed(copy.deepcopy(location_info))

    def modify_location(self, location_info):
        if location_info.dpid == None or location_info.port == None:
            return defer.fail(DirectoryException(
                    'Cannot modify location - dpid and port must be set.'))
        if not self.locations.has_key(location_info.name):
            return defer.fail(DirectoryException(
                    'Cannot modify location - location does not exist.',
                    DirectoryException.NONEXISTING_NAME))
        if location_info.name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot modify location %s.' % location_info.name))
        old_info = self.locations[location_info.name]

        if hasattr(old_info, '_fp_credentials') and \
            not hasattr(location_info,'_fp_credentials'): 
          location_info._fp_credentials = old_info._fp_credentials
        key = location_info.dpid.as_host() + (location_info.port << 48)
        old_key = old_info.dpid.as_host() + (old_info.port << 48)
        if old_key != key:
            if self.location_bindings.has_key(key):
                return defer.fail(DirectoryException(
                        'Cannot modify location - dpid/port already bound.',
                        DirectoryException.RECORD_ALREADY_EXISTS))
            del self.location_bindings[old_key]
        li = copy.deepcopy(location_info)
        self.locations[location_info.name] = li
        self.location_bindings[key] = li
        return defer.succeed(location_info)

    def del_location(self, location_name):
        if not self.locations.has_key(location_name):
            return defer.fail(DirectoryException(
                    'Cannot delete location - does not exist.',
                    DirectoryException.NONEXISTING_NAME))
        if location_name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot delete location %s.' % location_name,
                    DirectoryException.OPERATION_NOT_PERMITTED))
        ret = self.locations[location_name]
        key = ret.dpid.as_host() + (ret.port << 48)
        del self.locations[location_name]
        del self.location_bindings[key]
        return self._del_member_from_groups(ret, Directory.LOCATION_PRINCIPAL,
                mangle_name(self.name, location_name))

    def get_location(self, location_name):
        if self.locations.has_key(location_name):
            return defer.succeed(copy.deepcopy(self.locations[location_name]))
        elif location_name in self.restricted_names:
            return defer.succeed(LocationInfo(location_name))
        return defer.succeed(None)

    def search_locations(self, query):
        checked = 0
        locations = None
        if query.has_key('name'):
            name = query['name']
            if self.locations.has_key(name):
                locations = [ self.locations[name] ]
            elif name in self.restricted_names and len(query) == 1:
                return defer.succeed([name])
            else:
                locations = []
            checked = checked + 1

        if query.has_key('dpid'):
            dpid = query['dpid']
            if query.has_key('port'):
                key = dpid.as_host() + (query['port'] << 48)
                if self.location_bindings.has_key(key):
                    match = self.location_bindings[key]
                    if locations == None or match in locations:
                        locations = [ match ]
                    else:
                        locations = []
                else:
                    locations = []
                checked = checked + 1
            else:
                if locations == None:
                    locations = self.locations.values()
                filter_list(locations, lambda location : location.dpid != dpid)
            checked = checked + 1
        elif query.has_key('port'):
            port = query['port']
            if locations == None:
                locations = self.locations.values()
            filter_list(locations, lambda location : location.port != port)
            checked = checked + 1
        
        if query.has_key('name_glob'):
            regex_str = glob_to_regex(query['name_glob']) 
            regex = re.compile(regex_str)
            if locations == None:
                locations = self.locations.values()
            filter_list(locations, lambda loc : not regex.search(loc.name) )
            checked = checked + 1
            
        if checked != len(query):
            raise DirectoryException('Unsupported query parameters',
                    DiretoryException.INVALID_QUERY)
        elif locations == None:
            return defer.succeed(self.locations.keys())
        return defer.succeed([location.name for location in locations])


    def hosts_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def __check_netinfo_key__(self, info, locs, dls, nws, old_info=None):
        if info.dpid != None:
            if info.port == None:
                return False
            elif info.dladdr != None or info.nwaddr != None:
                return False
            key = info.dpid.as_host() + (info.port << 48)
            if key in locs \
                    or (self.host_loc_bindings.has_key(key)\
                            and self.host_loc_bindings[key] != old_info):
                return False
            locs.append(key)
            return True
        elif info.port != None:
            return False
        elif info.dladdr != None:
            if info.nwaddr != None:
                return False 
            key = info.dladdr.hb_long()
            if key in dls \
                    or (self.host_dl_bindings.has_key(key)\
                            and self.host_dl_bindings[key] != old_info):
                return False
            dls.append((key, info.is_router, info.is_gateway))
            return True
        elif info.nwaddr != None:
            if info.nwaddr in nws \
                    or (self.host_nw_bindings.has_key(info.nwaddr) \
                            and self.host_nw_bindings[info.nwaddr] != old_info):
                return False
            nws.append(info.nwaddr)
            return True
        return False

            
    def add_host(self, host_info):
        if host_info.name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot add host - invalid name.',
                    DirectoryException.OPERATION_NOT_PERMITTED))
        if self.hosts.has_key(host_info.name):
            return defer.fail(DirectoryException(
                    'Cannot add host - already exists.',
                    DirectoryException.RECORD_ALREADY_EXISTS))
        locs = []
        dls = []
        nws = []
        for info in host_info.netinfos:
            if not self.__check_netinfo_key__(info, locs, dls, nws):
                return defer.fail(DirectoryException(
                        'Cannot add host - already bound.',
                        DirectoryException.RECORD_ALREADY_EXISTS))
        hi = copy.deepcopy(host_info)
        hi._fp_credentials = [] 
        self.hosts[host_info.name] = hi
        for loc in locs:
            self.host_loc_bindings[loc] = hi
        for dl, is_r, is_g in dls:
            self.host_dl_bindings[dl] = hi
            self.routers[dl] = is_r
            self.gateways[dl] = is_g
        for nw in nws:
            self.host_nw_bindings[nw] = hi
        return defer.succeed(copy.deepcopy(host_info))

    def modify_host(self, host_info):
        if not self.hosts.has_key(host_info.name):
            return defer.fail(DirectoryException(
                    'Cannot modify host - does not exist.',
                    DirectoryException.NONEXISTING_NAME))
        if host_info.name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot modify host %s.' % host_info.name,
                    DirectoryException.OPERATION_NOT_PERMITTED))
        
        locs = []
        dls = []
        nws = []
        old_info = self.hosts[host_info.name]
        for info in host_info.netinfos:
            if not self.__check_netinfo_key__(info, locs, dls, nws, old_info):
                return defer.fail(DirectoryException(
                        'Cannot modify host - already bound.',
                        DirectoryException.RECORD_ALREADY_EXISTS))
        
        if hasattr(old_info, '_refcount') and \
            not hasattr(host_info,'_refcount'): 
          host_info._refcount = old_info._refcount
        if hasattr(old_info, '_fp_credentials') and \
            not hasattr(host_info,'_fp_credentials'): 
          host_info._fp_credentials = old_info._fp_credentials
        
        for info in old_info.netinfos:
            if info.dpid != None:
                del self.host_loc_bindings[info.dpid.as_host() + (info.port << 48)]
            elif info.dladdr != None:
                dl = info.dladdr.hb_long()
                del self.host_dl_bindings[dl]
                del self.routers[dl]
                del self.gateways[dl]
            elif info.nwaddr != None:
                del self.host_nw_bindings[info.nwaddr]

        self.hosts[host_info.name] = host_info
        for loc in locs:
            self.host_loc_bindings[loc] = host_info
        for dl, is_r, is_g in dls:
            self.host_dl_bindings[dl] = host_info
            self.routers[dl] = is_r
            self.gateways[dl] = is_g
        for nw in nws:
            self.host_nw_bindings[nw] = host_info
        return defer.succeed(copy.deepcopy(host_info))        

    def del_host(self, host_name):
        if not self.hosts.has_key(host_name):
            return defer.fail(DirectoryException(
                    'Cannot delete host - does not exist.',
                    DirectoryException.NONEXISTING_NAME))
        if host_name in self.restricted_names:
            return defer.fail(DirectoryException(
                    'Cannot delete host %s.' % host_name,
                    DirectoryException.OPERATION_NOT_PERMITTED))
        ret = self.hosts[host_name]
        del self.hosts[host_name]
        for info in ret.netinfos:
            if info.dpid != None:
                del self.host_loc_bindings[info.dpid.as_host() + (info.port << 48)]
            elif info.dladdr != None:
                dl = info.dladdr.hb_long()
                del self.host_dl_bindings[dl]
                del self.routers[dl]
                del self.gateways[dl]
            elif info.nwaddr != None:
                del self.host_nw_bindings[info.nwaddr]
        for alias in ret.aliases:
            self._del_member_from_groups(ret, Directory.HOST_PRINCIPAL,
                    mangle_name(self.name, alias))
        return self._del_member_from_groups(ret, Directory.HOST_PRINCIPAL,
                mangle_name(self.name, host_name))

    def get_host(self, host_name):
        if self.hosts.has_key(host_name):
            return defer.succeed(copy.deepcopy(self.hosts[host_name]))
        elif host_name in self.restricted_names:
            return defer.succeed(HostInfo(host_name))
        return defer.succeed(None)

    @staticmethod
    def host_netinfo_nomatch(match_fn):
        def fn(host):
            for info in host.netinfos:
                if match_fn(info):
                    return False
            return True
        return fn

    def search_hosts(self, query):
        checked = 0
        hosts = None
        if query.has_key('name'):
            name = query['name']
            if self.hosts.has_key(name):
                hosts = [ self.hosts[name] ]
            elif name in self.restricted_names and len(query) == 1:
                return defer.succeed([name])
            else:
                hosts = []
            checked = checked + 1
        
        if query.has_key('dpid'):
            dpid = query['dpid']
            if query.has_key('port'):
                key = dpid.as_host() + (query['port'] << 48)
                if self.host_loc_bindings.has_key(key):
                    match = self.host_loc_bindings[key]
                    if hosts == None or match in hosts:
                        hosts = [ match ]
                    else:
                        hosts = []
                else:
                    hosts = []
                checked = checked + 1
            else:
                if hosts == None:
                    hosts = self.hosts.values()
                filter_list(hosts, self.host_netinfo_nomatch(lambda info : info.dpid == dpid))
            checked = checked + 1
        elif query.has_key('port'):
            port = query['port']
            if hosts == None:
                hosts = self.hosts.values()
            filter_list(hosts, self.host_netinfo_nomatch(lambda info : info.port == port))
            checked = checked + 1

        if query.has_key('dladdr'):
            dladdr = query['dladdr'].hb_long()
            if self.host_dl_bindings.has_key(dladdr):
                match = self.host_dl_bindings[dladdr]
                if hosts == None or match in hosts:
                    hosts = [ match ]
                else:
                    hosts = []
            else:
                hosts = []
            checked = checked + 1
            
        if query.has_key('nwaddr'):
            nwaddr = query['nwaddr']
            if self.host_nw_bindings.has_key(nwaddr):
                match = self.host_nw_bindings[nwaddr]
                if hosts == None or match in hosts:
                    hosts = [ match ]
                else:
                    hosts = []
            else:
                hosts = []
            checked = checked + 1

        if query.has_key('is_gateway'):
            is_gway = query['is_gateway']
            if hosts == None:
                hosts = self.hosts.values()
            filter_list(hosts, self.host_netinfo_nomatch(
                    lambda info : info.is_gateway == is_gway))
            checked = checked + 1

        if query.has_key('is_router'):
            is_rter = query['is_router']
            if hosts == None:
                hosts = self.hosts.values()
            filter_list(hosts, self.host_netinfo_nomatch(
                    lambda info : info.is_router == is_rter))
            checked = checked + 1

        if query.has_key('alias'):
            alias = query['alias']
            if hosts == None:
                hosts = self.hosts.values()
            filter_list(hosts, lambda host : alias not in host.aliases)
            checked = checked + 1
        
        if query.has_key('name_glob'):
            regex_str = glob_to_regex(query['name_glob'])
            regex = re.compile(regex_str)
            if hosts == None:
                hosts = self.hosts.values()
            filter_list(hosts, lambda host : not regex.search(host.name) )
            checked = checked + 1

        if checked != len(query):
            raise DirectoryException('Unsupported query parameters',
                    DirectoryException.INVALID_QUERY)
        elif hosts == None:
            return defer.succeed(self.hosts.keys())
        return defer.succeed([host.name for host in hosts])

    def users_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_user(self, user_info):
        if user_info.name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot add user - invalid '
                    'name.', DirectoryException.RECORD_ALREADY_EXISTS))
        if self.users.has_key(user_info.name):
            return defer.fail(DirectoryException('Cannot add user - already '
                    'exists.', DirectoryException.RECORD_ALREADY_EXISTS))
        
        ui = copy.deepcopy(user_info)
        ui._fp_credentials = [] 
        self.users[user_info.name] = ui
        return defer.succeed(copy.deepcopy(user_info))

    def modify_user(self, user_info):
        if not self.users.has_key(user_info.name):
            return defer.fail(DiretoryException('Cannot modify user - does '
                    'not exist.', DiretoryException.NONEXISTING_NAME))
        if user_info.name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot modify user %s.' 
                    % user_info.name,
                    DirectoryException.OPERATION_NOT_PERMITTED))
        old_info = self.users[user_info.name]

        if hasattr(old_info, '_fp_credentials') and \
            not hasattr(user_info,'_fp_credentials'): 
          user_info._fp_credentials = old_info._fp_credentials
        self.users[user_info.name] = user_info
        return defer.succeed(copy.deepcopy(user_info))

    def del_user(self, user_name):
        if not self.users.has_key(user_name):
            return defer.fail(DirectoryException('Cannot delete user - does '
                    'not exist.', DirectoryException.NONEXISTING_NAME))
        if user_name in self.restricted_names:
            return defer.fail(DirectoryException('Cannot delete user %s.'
                    % user_name, DirectoryException.OPERATION_NOT_PERMITTED))
        ret = self.users[user_name]
        del self.users[user_name]
        return self._del_member_from_groups(ret, Directory.USER_PRINCIPAL,
                mangle_name(self.name, user_name))

    def get_user(self, user_name):
        if self.users.has_key(user_name):
            return defer.succeed(copy.deepcopy(self.users[user_name]))
        elif user_name in self.restricted_names:
            return defer.succeed(UserInfo(user_name))
        return defer.succeed(None)

    def search_users(self, query):
        checked = 0
        users = None
        if query.has_key('name'):
            name = query['name']
            if self.users.has_key(name):
                users = [ self.users[name] ]
            elif name in self.restricted_names and len(query) == 1:
                return defer.succeed([name])
            else:
                users = []
            checked = checked + 1
        
        if query.has_key('name_glob'):
            regex_str = glob_to_regex(query['name_glob']) 
            regex = re.compile(regex_str)
            if users == None:
                users = self.users.values()
            filter_list(users, lambda user : not regex.search(user.name) ) 
            checked = checked + 1

        if checked != len(query):
            raise DirectoryException('Unsupported query parameters',
                    DirectoryException.INVALID_QUERY)
        elif users == None:
            return defer.succeed(self.users.keys())
        return defer.succeed([user.name for user in users])

    def group_supported(self, group_type):
        if group_type in Directory.ALL_GROUP_TYPES:
            return Directory.READ_WRITE_SUPPORT
        return Directory.NO_SUPPORT

    def get_group_membership(self, group_type, member_name=None,
            local_groups=None):
        group_dict = self.groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type '%s'" %group_type))
        if member_name is None \
                or (isinstance(member_name, basestring) and member_name == ""):
            return defer.succeed(group_dict.keys())
        groups = set()
        if is_mangled_name(member_name):
            mangled_name = member_name
        else:
            mangled_name = mangle_name(self.name, member_name)
        if isinstance(member_name, netinet.cidr_ipaddr):
            groups.update(self.cidr_cache.get_groups(member_name))
        else:
            for group, gi in group_dict.iteritems():
                if mangled_name in gi.member_names:
                    groups.add(group)
        parentgroups = set()
        for group in groups:
            parentgroups.update(set(self._get_group_parents_s(group_type,
                    mangle_name(self.name, group))))
        for lgroup in (local_groups or []):
            parentgroups.update(set(self._get_group_parents_s(group_type,
                    lgroup)))
        return defer.succeed(tuple(groups | parentgroups))

    def search_groups(self, group_type, query_dict):
        group_dict = self.groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type '%s'" %group_type))
        if len(set(query_dict.keys()) - set(['name', 'name_glob'])):
            raise DirectoryException("Unsupported query in search_groups")
        groups = None
        if query_dict.has_key('name'):
            name = query_dict['name']
            if group_dict.has_key(name):
                groups = [name]
            elif name in self.restricted_names and len(query_dict) == 1:
                return defer.succeed([name])
            else:
                groups = []

        if query_dict.has_key('name_glob'):
            regex_str = glob_to_regex(query_dict['name_glob'])
            regex = re.compile(regex_str)
            if groups == None:
                groups = group_dict.keys()
            filter_list(groups, lambda group : not regex.search(group) )

        if groups == None:
            return defer.succeed(group_dict.keys())
        return defer.succeed(groups)

    def get_group(self, group_type, group_name):
        group_dict = self.groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type '%s'" %group_type))
        if group_dict.has_key(group_name):
            return defer.succeed(copy.deepcopy(group_dict[group_name]))
        return defer.succeed(None)

    def _get_group_parents_s(self, group_type, group_name):
        parent_group_dict = self.parent_groups.get(group_type)
        if parent_group_dict is None:
            raise DirectoryException(
                    "Invalid or unsupported group type '%s'" %group_type)
        if parent_group_dict.has_key(group_name):
            return tuple(parent_group_dict[group_name])
        return tuple()

    def get_group_parents(self, group_type, group_name):
        return defer.succeed(self._get_group_parents_s(group_type, group_name))

    def add_group(self, group_type, group_info):
        group_dict = self.groups.get(group_type)
        parent_group_dict = self.parent_groups.get(group_type)
        if group_dict is None or parent_group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type %s" %group_type))
        # TODO: check member
        # TODO: check subgroups
        if group_info.name == None or group_info.name == "":
            return defer.fail(DirectoryException('Cannot add group None.'))
        if group_dict.has_key(group_info.name):
            return defer.fail(DirectoryException('Cannot add group - already '
                    'exists.', DirectoryException.RECORD_ALREADY_EXISTS))
        group_dict[group_info.name] = group_info
        for sg in group_info.subgroup_names:
            parent_group_set = parent_group_dict.get(sg) or set()
            parent_group_set.add(group_info.name)
            parent_group_dict[sg] = parent_group_set
        if group_type == Directory.NWADDR_GROUP:
            for member in group_info.member_names:
                self.cidr_cache.add_cidr(group_info.name, member)
        return defer.succeed(copy.deepcopy(group_info))

    def modify_group(self, group_type, group_info):
        group_dict = self.groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type %s" %group_type))
        name = getattr(group_info, "name")
        if not group_dict.has_key(name):
            return defer.fail(DirectoryException("No group named '%s' exists"
                    %name, DirectoryException.NONEXISTING_NAME))
        gi = group_dict[name]
        gi.description = group_info.description
        return defer.succeed(copy.deepcopy(gi))

    def del_group(self, group_type, group_name):
        group_dict = self.groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type %s" %group_type))
        if not group_dict.has_key(group_name):
            return defer.fail(
                    DirectoryException('Cannot delete group - does not exist.',
                            DirectoryException.NONEXISTING_NAME))
        parent_group_dict = self.parent_groups.get(group_type)
        mangled_gname = mangle_name(self.name, group_name)
        #remove index to our parent groups
        if parent_group_dict.has_key(mangled_gname):
            for pg in parent_group_dict[mangled_gname]:
                group_dict[pg].subgroup_names.remove(mangled_gname)
            del parent_group_dict[mangled_gname]
        ret = group_dict[group_name]
        #remove subgroups parent group reference to us
        for sg in ret.subgroup_names:
            if sg in parent_group_dict:
                parent_group_dict[sg].discard(group_name)
        #remove the group from the cidr lookup cache
        if group_type == Directory.NWADDR_GROUP:
            for member in ret.member_names:
                self.cidr_cache.del_cidr(group_info.name, member)
        #remove the group
        del group_dict[group_name]
        return defer.succeed(ret)

    def add_group_members(self, group_type, group_name, member_names=[],
                              subgroup_names=[]):
        group_dict = self.groups.get(group_type)
        parent_group_dict = self.parent_groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type %s" %group_type))
        # TODO: check member
        # TODO: check subgroups
        if not group_dict.has_key(group_name):
            return defer.fail(
                    DirectoryException('Cannot modify group - does not exist.',
                            DirectoryException.NONEXISTING_NAME))
        group = group_dict[group_name]
        added_names = []
        added_subgroups = []
        for name in member_names:
            if name not in group.member_names:
                group.member_names.append(name)
                added_names.append(name)
                if group_type == Directory.NWADDR_GROUP:
                    self.cidr_cache.add_cidr(group_name, name)
        for subgroup in subgroup_names:
            if subgroup not in group.subgroup_names:
                group.subgroup_names.append(subgroup)
                added_subgroups.append(subgroup)
                #add parent_group pointer to subgroup
                parent_group_set = parent_group_dict.get(subgroup) or set()
                parent_group_set.add(group_name)
                parent_group_dict[subgroup] = parent_group_set
        return defer.succeed((added_names, added_subgroups))

    def del_group_members(self, group_type, group_name, member_names=[],
                              subgroup_names=[]):
        group_dict = self.groups.get(group_type)
        parent_group_dict = self.parent_groups.get(group_type)
        if group_dict is None:
            return defer.fail(DirectoryException(
                    "Invalid or unsupported group type %s" %group_type))
        if not group_dict.has_key(group_name):
            return defer.fail(
                    DirectoryException('Cannot modify group - does not exist.',
                            DirectoryException.NONEXISTING_NAME))
        group = group_dict[group_name]
        removed_names = []
        removed_subgroups = []
        for name in member_names:
            if name in group.member_names:
                group.member_names.remove(name)
                removed_names.append(name)
                if group_type == Directory.NWADDR_GROUP:
                    self.cidr_cache.del_cidr(group_name, name)
        for subgroup in subgroup_names:
            if subgroup in group.subgroup_names:
                group.subgroup_names.remove(subgroup)
                removed_subgroups.append(subgroup)
                #remove parent_group pointer
                parent_group_set = parent_group_dict.get(subgroup)
                if parent_group_set:
                    parent_group_set.discard(group_name)
        return defer.succeed((removed_names, removed_subgroups))


    def topology_properties_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def is_gateway(self, dladdr):
        dl = dladdr.hb_long()
        if self.gateways.has_key(dl):
            return defer.succeed(self.gateways[dl])
        return defer.succeed(None)

    def is_router(self, dladdr):
        dl = dladdr.hb_long()
        if self.routers.has_key(dl):
            return defer.succeed(self.routers[dl])
        return defer.succeed(None)

    def get_credentials(self,principal_type, principal_name, cred_type=None):
        if cred_type == None:
          cred_type = Directory_Factory.AUTHORIZED_CERT_FP
        def get_creds(p_info):
          if p_info == None: 
            raise DirectoryException("get_credentials on unknown name: %s" \
                % principal_name) 
          return p_info._fp_credentials
        d = self.get_principal(principal_type,principal_name)
        d.addCallback(get_creds)
        return d

    def put_credentials(self,principal_type, principal_name, cred_list, 
                        cred_type=None):
        if cred_type == None:
          cred_type = Directory_Factory.AUTHORIZED_CERT_FP
        if cred_type != Directory_Factory.AUTHORIZED_CERT_FP: 
            raise DirectoryException(\
                "simple_directory only supports '%s' credentials" \
                 % Directory_Factory.AUTHORIZED_CERT_FP)
        def done(p_info): 
          return p_info._fp_credentials
        
        def set_creds(p_info): 
          p_info._fp_credentials = cred_list
          return self.modify_principal(principal_type,p_info)
  
        d = self.get_principal(principal_type,principal_name)
        d.addCallback(set_creds)
        d.addCallback(done)
        return d
