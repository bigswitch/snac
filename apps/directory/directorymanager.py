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
import copy
import logging
import sys

from nox.lib.core import *
from nox.lib.netinet import netinet
from nox.lib.directory import *
from nox.apps.storage import TransactionalStorage
from nox.apps.storage.StorageTableUtil import *
from nox.apps.directory import pydirmanager
from nox.apps.directory.pynetinfo_mod_event import NetInfo_mod_event
from nox.apps.directory.pydirmanager import Principal_name_event
from nox.apps.directory.pydirmanager import Group_name_event
from nox.apps.directory.pydirmanager import Group_change_event
from nox.apps.directory.pydirmanager import Location_delete_event
from twisted.internet import defer
from twisted.python.failure import Failure
from nox.lib.netinet.netinet import datapathid
from nox.apps.user_event_log.pyuser_event_log import pyuser_event_log,LogEntry
from nox.apps.pyrt.pycomponent import CONTINUE
from nox.apps.authenticator.pyauth import Host_event

lg = logging.getLogger('directorymanager')

def demangle_name(name):
    """Convert name of type "directory;name" to (directory,name) tuple"""
    if not hasattr(name,"split"):
        return ("", name)
    name_list = name.split(';')
    if len(name_list) > 2:
        raise DirectoryException("Cannot demangle name '%s'" % name,\
                              DirectoryException.BADLY_FORMATTED_NAME)
    elif len(name_list) == 1:
        return ("", name_list[0])
    else:
        return (name_list[0], name_list[1])

def mangle_name(directory, name):
    if not isinstance(name, basestring):
        return name
    if directory == "":
        return name
    return  directory + ';' + name

def is_mangled_name(name):
    if not hasattr(name, "find"):
        return False
    return name.find(';') != -1

def _mangle_result_list(res, dir_instance):
    return [mangle_name(dir_instance._name, r) for r in res]

def _deconflict_directory_names(name_list):
    ret = ""
    for name in name_list:
        if name is not None and name != "":
            if ret == "":
                ret = name
            else:
                if ret != name:
                    raise DirectoryException(
                            "Directory name mismatch ('%s' != '%s'"
                            %(ret, name), 
                            DirectoryException.BADLY_FORMATTED_NAME)
    return ret

def demangle_and_deconflict_name(name, dir=""):
    """Demangle name and return (demangled_dir, demangled_query) tuple

    raises Directory exception if dir is not empty string and conflicts
    with demangled name
    """
    (dm_dir, dm_name) = demangle_name(name)
    return (_deconflict_directory_names((dm_dir, dir)), dm_name)

def demangle_and_deconflict_query(query_dict, dir=""):
    """Demangle name attribute in query_dict if present and return
    (demangled_dir, demangled_query) tuple

    raises Directory exception if dir is not empty string and conflicts
    with demangled name
    """
    if query_dict.has_key('name'):
        (dm_dir, dm_name) = demangle_name(query_dict['name'])
        if dm_dir != "":
            query_dict['name'] = dm_name
        dc_dir = _deconflict_directory_names((dm_dir, dir))
        return (dc_dir, query_dict)
    else:
        return (dir, query_dict)

def demangle_and_deconflict_info(info_obj, dir=""):
    """Replace name attribute of info_object with demangled name and \
    return (demangled_dir, demangled_info_obj) tuple

    raises Directory exception if dir is not empty string and conflicts
    with demangled name
    """
    if hasattr(info_obj, 'name'):
        (dm_dir, dm_name) = demangle_name(info_obj.name)
        if len(dm_dir) > 0:
            info_obj.name = dm_name
        dc_dir = _deconflict_directory_names((dm_dir, dir))
        return (dc_dir, info_obj)
    else:
        return (dir, info_obj)

def get_default_switch_name(dpid):
    return "switch " + str(dpid)

def get_default_loc_name(switch_name, port_name):
    return "%s:%s" %(switch_name, port_name)

def get_default_host_name(dladdr, nwaddr):
    if dladdr:
        return "host " + str(dladdr)
    elif nwaddr:
        return "host " + str(create_ipaddr(nwaddr))
    raise DirectoryException("No dladdr or nwaddr provided to name host",
                    DirectoryException.INSUFFICIENT_INPUT)

# this method exists so that C++ can create credential objects to 
# used as the parameter to a put_credential call
def create_credential(cred_type):
  if(cred_type == Directory_Factory.AUTH_SIMPLE ): 
    return PasswordCredential()
  if(cred_type == Directory_Factory.AUTHORIZED_CERT_FP): 
    return CertFingerprintCredential()
  raise DirectoryException(
      "Invalid credential type '%s' given to create_credential" % cred_type,
      DirectoryException.INVALID_CRED_TYPE)

# this method is lame b/c Directories do not use the same 
# notion of a name as does user_event_log / bindings_storage 
def log_rename(uel,principal_type,oldname,newname): 
    if principal_type == Directory.USER_PRINCIPAL: 
      uel.log("pydir_manager",LogEntry.INFO,"{su} renamed to {du}", 
                su=oldname, du=newname)
    elif principal_type == Directory.HOST_PRINCIPAL: 
      uel.log("pydir_manager",LogEntry.INFO,"{sh} renamed to {dh}", 
                sh=oldname, dh=newname)
    elif principal_type == Directory.LOCATION_PRINCIPAL: 
      uel.log("pydir_manager",LogEntry.INFO,"{sl} renamed to {dl}", 
                sl=oldname, dl=newname)
    elif principal_type == Directory.SWITCH_PRINCIPAL: 
      uel.log("pydir_manager",LogEntry.INFO,"{ss} renamed to {ds}", 
                ss=oldname, ds=newname)

def log_group_modification(uel, group_type, method, group_name, 
                          member_names, subgroup_names): 
    op_type = "??" 
    if method == "del_group_members":
      op_type = "removed from"
    elif method == "add_group_members": 
      op_type = "added to"

    group_name = group_name.encode('utf-8')
    members = []
    for name in member_names:
        if isinstance(name, unicode):
            members.append(name.encode('utf-8'))
        else:
            members.append(str(name))
        
    subgroup_names = [name.encode('utf-8') for name in subgroup_names]

    if group_type == Directory.USER_PRINCIPAL_GROUP: 
      if len(members) > 0:
        uel.log("pydir_manager",LogEntry.INFO,"{su} %s {sug}" \
          % op_type, su=members, sug=group_name)
      if len(subgroup_names) > 0: 
        uel.log("pydir_manager",LogEntry.INFO,"{dug} %s {sug}" \
          % op_type, dug=subgroup_names, sug=group_name)
    elif group_type == Directory.HOST_PRINCIPAL_GROUP: 
      if len(members) > 0:
        uel.log("pydir_manager",LogEntry.INFO,"{sh} %s {shg}" \
          % op_type, sh = members, shg=group_name)
      if len(subgroup_names) > 0: 
        uel.log("pydir_manager",LogEntry.INFO,"{dhg} %s {shg}" \
          % op_type, dhg=subgroup_names, shg=group_name)
    elif group_type == Directory.LOCATION_PRINCIPAL_GROUP: 
      if len(members) > 0:
        uel.log("pydir_manager",LogEntry.INFO,"{sl} %s {slg}" \
          % op_type, sl=members, slg=group_name)
      if len(subgroup_names) > 0: 
        uel.log("pydir_manager",LogEntry.INFO,"{dlg} %s {slg}" \
          % op_type, dlg=subgroup_names, slg=group_name)
    elif group_type == Directory.SWITCH_PRINCIPAL_GROUP: 
      if len(members) > 0:
        uel.log("pydir_manager",LogEntry.INFO,"{ss} %s {ssg}" \
          % op_type, ss= members, ssg=group_name)
      if len(subgroup_names) > 0: 
        uel.log("pydir_manager",LogEntry.INFO,"{dsg} %s {ssg}" \
          % op_type, dsg=subgroup_names, ssg=group_name)
  

class ConfiguredDirectoryRecord(StorageRecord):
    """Configured directory as stored in CDB.  Read in on startup.
    """
    _columns = {
            'name'         : str,
            'type'         : str,
            'search_order' : int,
            'config_id'    : int
    }
    __slots__ = _columns.keys()

    def __init__(self, name, type, search_order, config_id):
        self.name = name
        self.type = type
        self.search_order = search_order
        self.config_id    = config_id


class ConfiguredDirectoryTable(StorageTable):
    _table_name = 'nox_directories'
    _table_indices = (
        ('name_idx', ("name",)),
        ('type_idx', ("type",)),
    )

    def __init__(self, storage):
        StorageTable.__init__(self, storage, self._table_name,
                ConfiguredDirectoryRecord, self._table_indices,
                cache_contents=True)


#
# Directory instances managed by the directorymanager once
# read in from CDB.  Directory instances are expected to inherit from
# lib/directory.
#
class DirectoryInstanceDecorator:
    def __init__(self, dir_instance, name, confid, search_order):
        self._instance     = dir_instance
        self._name         = name
        self._config_id    = confid
        self._search_order = search_order
        self.stats = { 'auth_success' : 0,
                       'auth_denied'  : 0,
                       'auth_error'   : 0,
                     }


class directorymanager(Component):
    """provides interface to all installed directories."""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

        # do event registration
        NetInfo_mod_event.register_event_converter(self.ctxt)

        self.configured_dir_tbl = None

        #list of DirectoryInstanceDecorator ordered by search_order
        self.directory_instances = []
        self.instances_by_name   = {}
        self.directory_components = {}

        self.cdm = None
        self.storage = None
        
        # instance variables for special 'discovered' directory containing 
        # switches and hosts that exist on the 
        # network but are not named
        # may want to make this into a separate
        # component, but this works for now
        from nox.apps.directory.discovered_directory import discovered_directory
        self.discovered_dir = discovered_directory() 
        self.add_directory_instance(self.discovered_dir, 
                self.discovered_dir.name, config_id=0, order=sys.maxint)
        self.register_for_datapath_leave(self.dp_leave) 
        self.register_handler(Host_event.static_get_name(),self.host_event)
        # We don't technically need to listen for the following two
        # events since we're the component throwing them, but we do so to
        # ease extracting discovered directory in the future
        self.register_handler(Principal_name_event.static_get_name(),
                self.renamed_principal)
        self.register_handler(Group_name_event.static_get_name(),
                self.renamed_group)

    def getInterface(self):
        return str(directorymanager)

    # On installation, cache all configured directories from CDB.  Once
    # cached, registering directories will be instantiated for every
    # configured directory of the same type

    def init_cdb_tables(self, res=None):
        self.configured_dir_tbl = ConfiguredDirectoryTable(self.storage)
        d = self.configured_dir_tbl.ensure_table_exists()
        return d

    def install(self):
        self.uel = self.resolve(pyuser_event_log)
        self.cdm = self.resolve(pydirmanager.PyDirManager)
        if self.cdm is None:
            raise Exception("Unable to resolve required component '%s'"
                            %str(pydirmanager.PyDirManager))
        self.cdm.set_py_dm(self)
        self.cdm.set_create_dp(netinet.datapathid.from_host)
        self.cdm.set_create_eth(netinet.create_eaddr)
        self.cdm.set_create_ip(netinet.create_ipaddr)
        self.cdm.set_create_cidr(netinet.create_cidr_ipaddr)
        self.cdm.set_create_cred(create_credential)

        self.storage = self.resolve(TransactionalStorage)
        if self.storage is None:
            raise Exception("Unable to resolve required component '%s'"
                            %str(TransactionalStorage))

        def _init_eb(failure):
            lg.error("Failed to read configuration from transactional "\
                     "storage: %s"%failure)
            return failure
        d = self.init_cdb_tables()
        d.addErrback(_init_eb)
        return d

    ## --
    ## Directory Management
    ## --

    def get_directory_factories(self):
        """Return dict of directory_type->factory_object of all registered
        directory components"""
        return copy.copy(self.directory_components)

    def get_configured_directories(self, sorted=False):
        #since table is cached, the 'query' isn't as inefficient as it may seem
        ret = self.configured_dir_tbl.get_all_recs_for_query_s({})
        if sorted:
            ret.sort(cmp=lambda x,y: int(x.search_order - y.search_order))
        return ret

    def get_configured_directory(self, name):
        """Return the ConfiguredDirectoryInstance for name"""
        recs = self.configured_dir_tbl.get_all_recs_for_query_s({'name':name})
        if len(recs):
            return recs[0]
        return None

    def rename_configured_directory(self, old_name, new_name):
        """Change the name of directory named old_name to new_name

        Returns deferred returning the new ConfiguredDirectoryInstance
        """
        def _rename_conf_dir(res=None, conn=None, state='entry'):
            if state == 'entry':
                #remove the old configured dir record
                d = self.configured_dir_tbl.remove_all_rows_for_query(
                        query={'name':old_name}, conn=conn)
                d.addCallback(_rename_conf_dir, conn=conn, state='rem_old')
            elif state == 'rem_old':
                #add the new configured dir record
                d = self.configured_dir_tbl.put_record(new_cd, conn=conn)
                d.addCallback(_rename_conf_dir, conn=conn, state='put_new')
            elif state == 'put_new':
                #change directory instance decorator name
                self.instances_by_name[old_name]._name = new_name
                #change instances_by_name
                self.instances_by_name[new_name] = \
                        self.instances_by_name[old_name]
                del self.instances_by_name[old_name]
                #TODO: notify authenticator of change
                #TODO: notify directories supporting global groups of change
                return
            else:
                raise Exception("Invalid state: %s" %state)
            return d

        cd = self.get_configured_directory(old_name)
        if cd is None:
            deferred.fail(Failure("No directory named '%s' to rename"
                    %old_name))
        new_cd = copy.copy(cd)
        new_cd.name = new_name
        return call_in_txn(self.storage, _rename_conf_dir)

    def get_directory_instance(self, instance_name):
        """Return DirectoryInstanceDecorator corresponding to instance_name
        """
        return self.instances_by_name.get(instance_name)

    def is_valid_directory_name(self, instance_name):
        """Return True iff instance_name corresponds to an active
        directory instance.
        """
        return instance_name in self.instances_by_name

    def get_directory_instances(self):
        """Return all DirectoryInstanceDecorator in search order"""
        return self.directory_instances[:]

    def add_configured_directory(self, name, type, search_order=sys.maxint,
                                 config_id=0, ignore_if_dup_name=False):
        """Add a new directory instance to the list of configured directories

        The directory factory corresponding to 'type' must be registered
        with the directory manager prior to this call.

        @return: Deferred returning the new list of all configured directories
        """
        def _set_conf_dirs(res=None, conn=None, state='entry', instance=None):
            if state == 'entry':
                if instance is not None:
                    self.add_directory_instance(instance, cdir.name,
                            cdir.config_id, cdir.search_order)
                d = self.configured_dir_tbl.remove_all_rows_for_query(query={},
                        conn=conn)
                d.addCallback(_set_conf_dirs, conn=conn, state='removed_old')
            elif state == 'removed_old':
                newdirs = res[:]
                newdirs.sort(cmp=lambda x,y:int(x.search_order-y.search_order))
                newdirs.insert(cdir.search_order, cdir)
                i = 0
                for nd in newdirs:
                    nd.search_order = i
                    i += 1
                    if self.instances_by_name.has_key(nd.name):
                        self.instances_by_name[nd.name]._search_order = \
                                nd.search_order
                d = self.configured_dir_tbl.put_all_records(newdirs, conn=conn)
                d.addCallback(_set_conf_dirs, conn=conn, state='put_new')
            elif state == 'put_new':
                self.directory_instances.sort(
                    cmp=lambda x,y: int(x._search_order - y._search_order))
                return self.get_configured_directories(sorted=True)
            else:
                raise Exception("Invalid state: %s" %state)
            return d

        if config_id == 0:
            config_id = 1
            for rec in self.get_configured_directories():
                config_id = max(config_id, rec.config_id + 1)
        dirfactory = self.get_directory_factories().get(type)
        if dirfactory is None:
            raise DirectoryException("Invalid directory type '%s'" %type,
                    DirectoryException.INVALID_DIR_TYPE)
        if not dirfactory.supports_multiple_instances():
            #enforce max of one configured directory
            rec = self.configured_dir_tbl.get_all_recs_for_query_s(
                    {'type':type})
            if len(rec) and rec[0].name != name:
                raise DirectoryException("Can not add additional directory "\
                        "of type '%s': does not support multiple instances"
                        %type, DirectoryException.INVALID_DIR_TYPE)
        search_order = max(search_order, 0)
        cdir = ConfiguredDirectoryRecord(name, type, search_order, config_id)
        lg.debug("Adding configured directory '%s'" %cdir.name)
        rec = self.get_configured_directory(cdir.name)
        if rec is not None:
            if ignore_if_dup_name:
                return defer.succeed(
                        self.get_configured_directories(sorted=True))
            else:
                raise DirectoryException("Unable to add duplicate directory "\
                        "name '%s'" %cdir.name,
                        DirectoryException.RECORD_ALREADY_EXISTS)
        if cdir.type in self.directory_components and \
           not cdir.name in self.instances_by_name:
            factory = self.directory_components[cdir.type]
            d = factory.get_instance(cdir.name, cdir.config_id)
            d.addCallback(lambda inst : 
                    call_in_txn(self.storage, _set_conf_dirs, instance=inst))
        else:
            d = call_in_txn(self.storage, _set_conf_dirs)
        return d

    def del_configured_directory(self, name, remove_instance=True):
        """Delete the configured directory instance from the list of
        configured directories.

        @return: Deferred returning the ConfiguredDirectoryRecord removed
        """
        def _removed_cb(res):
            if len(res):
                return res[0]
            return None

        if remove_instance:
            self.remove_directory_instance(name)
        d = self.configured_dir_tbl.remove_all_rows_for_query(
                query={'name': name}, conn=None)
        d.addCallback(_removed_cb)
        return d

    def get_search_order(self):
        """Return sorted list of configured directory names in search order
        """
        return [di._name for di in self.get_directory_instances()]

    def set_search_order(self, sorted_instance_name_list):
        """Update directory search order to reflect the order in
        sorted_instance_name_list

        @return: Deferred returning list of directory instance names in
        new search order
        """
        def _set_conf_dir_order(res=None, conn=None, state='entry'):
            i = 0
            if state == 'entry':
                d = self.configured_dir_tbl.remove_all_rows_for_query(query={},
                        conn=conn)
                d.addCallback(_set_conf_dir_order, conn=conn,
                        state='removed_old')
            elif state == 'removed_old':
                name_to_order = {}
                for name in sorted_instance_name_list:
                    name_to_order[name] = i
                    i += 1
                newdirs = res[:]
                for cdir in newdirs:
                    cdir.search_order = name_to_order.get(cdir.name)
                d = self.configured_dir_tbl.put_all_records(newdirs, conn=conn)
            else:
                raise Exception("Invalid state: %s" %state)
            return d

        def _set_instance_order(res):
            self.directory_instances = []
            for name in sorted_instance_name_list:
                instance = self.instances_by_name.get(name)
                #instance may be None if configured instance is not active
                if instance is not None:
                    self.directory_instances.append(instance)
            return self.get_search_order()
        
        sorted_instance_name_list.append(self.discovered_dir.name)
        if len(set(sorted_instance_name_list) ^ set(self.get_search_order())):
            raise DirectoryException("One or more names in new search order "
                    "did not match currently configured directory instance",
                    DirectoryException.NONEXISTING_NAME)
        d = call_in_txn(self.storage, _set_conf_dir_order)
        d.addCallback(_set_instance_order)
        return d

    def add_directory_instance(self, instance, name, config_id, order):
        """Add instance as an active directory component instance

        No directory configuration information is persisted by this call

        @return: the new DirectoryInstanceDecorator
        """
        if instance is None:
            raise DirectoryException("Invalid instance type '%s' named '%s' "
                    "with config id '%s'" %(component.get_type(), name, id))
        if name in self.instances_by_name:
            raise DirectoryException("Instance named '%s' already added"
                    %name, DirectoryException.RECORD_ALREADY_EXISTS)
        did = DirectoryInstanceDecorator(instance, name, config_id, order)
        self.directory_instances.append(did)
        self.instances_by_name[name] = did
        
        self.directory_instances.sort(
            cmp=lambda x,y: int(x._search_order - y._search_order))

        # Bootstrap the discovered;gateways group from static registrations
        self.add_gateways_to_discovered(name) #don't need to block on deferred

        return did

    def remove_directory_instance(self, name):
        """Remove directory instance named 'name' from the list of
        active directory instances.

        @return: the DirectoryInstanceDecorator removed or None if no such name
        """
        ret = None
        if name == self.discovered_dir.name:
            raise DirectoryException("The directory named '%s' may not be "\
                    "removed" %name)
        if name in self.instances_by_name:
            ret = self.instances_by_name[name]
            del self.instances_by_name[name]
            self.directory_instances.remove(ret)
        return ret

    def register_directory_component(self, component):
        """Register the component as an available directory factory
        """
        def _verify_directory_instance(instance, name, id):
            if instance is None:
                raise DirectoryException("Failed to obtain instance of '%s' "
                        "named '%s' using config id %s"
                        %(component.get_type(), name, id))
            return instance

        def _get_config_records_cb(res, component):
            for rec in res:
                d = component.get_instance(rec.name, rec.config_id)
                d.addCallback(_verify_directory_instance, rec.name,
                        rec.config_id)
                d.addCallback(self.add_directory_instance, rec.name,
                        rec.config_id, rec.search_order)

        if not isinstance(component, Directory_Factory):
            raise Exception("Registered directory which isn't an "\
                            "instance of lib/directory")

        if self.directory_components.has_key(component.get_type()):
            #already added
            return defer.succeed(None)
        else:
            self.directory_components[component.get_type()] = component
            d = self.configured_dir_tbl.get_all_recs_for_query(
                    {'type' : component.get_type()})
            d.addCallback(_get_config_records_cb, component)
            return d


    ## --
    ## Authentication
    ##
    ## Authentication is attempted in each directory (in search order)
    ## configured to support the authentication type until successful, or
    ## there are no more directories to try.
    ##
    ## For available authentication types, see nox.lib.directory
    ## --

    def _delegate_until_stop(self, dir_instances, method_enabled_cb, 
            should_stop_cb, method, *args, **kwargs):
        """Returns [(directory name, result from directory), ...]
        results are sorted in order of dir_instances
        """
        def _delegate_until_stop_cb(res, last_instance_tried, instances_left, 
                results):
            if last_instance_tried is not None:
                results.append((last_instance_tried._name, res))
            d = None
            if last_instance_tried is None or (should_stop_cb is None 
                    or not should_stop_cb(last_instance_tried, res)):
                while d is None and len(instances_left) > 0:
                    instance = instances_left.pop(0)
                    if method_enabled_cb is None or \
                            method_enabled_cb(instance):
                        func = getattr(instance._instance, method)
                        d = func(*args, **kwargs)
            if d is None:
                #should_stop_check returned True or out of directories
                d = defer.succeed(results)
            else:
                d.addCallback(_delegate_until_stop_cb, instance,
                        instances_left, results)
                d.addErrback(_delegate_until_stop_cb, instance,
                        instances_left, results)
            return d
        return _delegate_until_stop_cb(None, None, dir_instances[:], [])

    def supports_authentication(self, auth_type=Directory.AUTH_SIMPLE):
        return self.enabled_auth_types_to_dir().get(auth_type) is not None

    def enabled_auth_types_to_dir(self):
        """Return dict of auth type to (priority ordered) list of directory
        names supporting it
        """
        ret = {}
        for instance in self.directory_instances:
            for auth_type in instance._instance.get_enabled_auth_types():
                dirlist = ret.get(auth_type, [])
                dirlist.append(instance._name)
                ret[auth_type] = dirlist
        return ret

    def get_credentials(self, principal_type, principal_name, 
                      cred_type=None, dir_name = ""): 
        (dm_dir, principal_name) = \
                demangle_and_deconflict_name(principal_name, dir_name)
        if cred_type is None:
            chk_method = lambda instance : True
        else:
            chk_method = lambda instance : \
                    cred_type in instance.get_enabled_auth_types()
        d = self._delegate_to_first(dm_dir, chk_method,
                'get_credentials', principal_type, principal_name, cred_type)
        d.addCallback(lambda res : res[1])
        return d

    def put_credentials(self, principal_type, principal_name, \
                        cred_list, cred_type=None, dir_name = ""): 
        ctypes = set()
        if cred_type is not None and len(cred_list) == 0: 
          ctypes.add(cred_type)
        for cred in cred_list:
            ctypes.add(cred.type)
        if cred_type is not None:
            if len(ctypes) > 1 or cred_type not in ctypes:
                raise DirectoryException("Credential type mismatch: %s %s"
                        %(cred_type, sorted(tuple(ctypes))) )
        (dm_dir, principal_name) = \
                demangle_and_deconflict_name(principal_name, dir_name)
        chk_method = lambda instance : \
            ctypes.issubset(set(instance.get_enabled_auth_types()))
        d = self._delegate_to_first(dm_dir, chk_method,
                'put_credentials', principal_type, principal_name,
                cred_list, cred_type)
        d.addCallback(lambda res : res[1])
        return d

    def simple_auth(self, username, password, dir_name=""):
        """Perform a simple username/password authentication.

        If dir_name is provided (and not blank), authentication will only
        be attempted with the specified directory.  Otherwise, each
        directory supporting simple_auth will be tried in search order
        until success.

        Arguments:
          username: login name of the user
          password: password provided by the user
          dir_name: (optional) directory to query or blank for all directories
                    in search order

        Returns:
          Deferred object returning an AuthResult class
        """
        def _supports_simple_auth_cb(dirinstance):
            return Directory.AUTH_SIMPLE in \
                    dirinstance._instance.get_enabled_auth_types()

        def _auth_result_cb(dirinstance, result):
            if dirinstance is not None:
                if not isinstance(result, AuthResult):
                    dirinstance.stats['auth_error'] += 1
                elif result.status == AuthResult.SUCCESS:
                    dirinstance.stats['auth_success'] += 1
                    return True
                elif result.status == AuthResult.INVALID_CREDENTIALS:
                    dirinstance.stats['auth_denied'] += 1
                elif result.status == AuthResult.ACCOUNT_DISABLED:
                    dirinstance.stats['auth_denied'] += 1
                else:
                    dirinstance.stats['auth_error'] += 1
            return False

        def _process_delegated_results(results):
            if len(results) == 0:
                raise DirectoryException("No directories configured "
                        "supporting simple_auth")
            lastdir, lastres = copy.deepcopy(results[-1])
            if not isinstance(lastres, AuthResult):
                #try to find a valid result to return
                results.reverse()
                for result in results:
                    if isinstance(result[1], AuthResult):
                        return result[1]
                raise DirectoryException("No directories returned a "
                        "valid auth result")

            lastres.groups = \
                    self._ensure_proper_mangling(lastdir, True, lastres.groups)
            if lastres.status == AuthResult.SUCCESS:
                lastres.username = mangle_name(lastdir, lastres.username)
            return lastres

        def _get_global_roles(result):
            def _process_roles(res):
                result.nox_roles = result.nox_roles | res
                return result
            if result.status != AuthResult.SUCCESS:
                return result
            d = self.get_global_user_roles(result.username, result.groups)
            d.addCallback(_process_roles)
            return d

        if dir_name is not None and dir_name != "":
            if not self.instances_by_name.has_key(dir_name):
                errmsg = "No directory found for simple_auth for name '%s'"\
                        %(dir_name)
                raise DirectoryException(errmsg,
                        DirectoryException.INVALID_DIR_TYPE)
            instances = [self.instances_by_name[dir_name]]
            if not _supports_simple_auth_cb(instances[0]):
                errmsg = "Directory '%s' doesn't support simple_auth" %dir_name
                raise DirectoryException(errmsg,
                        DirectoryException.OPERATION_NOT_PERMITTED)
        else:
            instances = self.directory_instances[:]

        d = self._delegate_until_stop(instances, _supports_simple_auth_cb,
                _auth_result_cb, 'simple_auth', username, password)
        d.addCallback(_process_delegated_results)
        d.addCallback(_get_global_roles)
        return d

    def get_global_user_roles(self, username, local_groups):
        """Returns deferred returning set of roles for the specified user
        """
        def _aggregate_roles(result_list):
            return set(result_list)
        chk_method = lambda instance : self._check_principal_support(instance,
                Directory.USER_PRINCIPAL, False)
        dirs = []
        for instance in self.directory_instances:
            if instance._instance.supports_global_groups():
                dirs.append(instance)
        d = self._delegate_to_all(None, None, {}, dirs, chk_method, 
                'get_user_roles', None, username, local_groups)
        d.addCallback(_aggregate_roles)
        return d

    ## --
    ## Principal Registration
    ##
    ## All methods return a deferred.  A DirectoryException is
    ## raised if if the method isn't enabled (by the specified directory
    ## if specified, or by any directory if not specified)
    ##
    ## Searches containing a mangled name will only be performed on that 
    ## directory.  Searches without a mangled name will return results
    ## from all directories supporting the method.
    ##
    ## Searches will return a Failure(DirectoryException) if none
    ## of the searched directories supported the query.
    ##
    ## Unless otherwise noted, if a specific directory is not targeted
    ## via mangled name or dir parameter, the first directory (in directory
    ## search order) supporting the method is used.
    ## --

    def _check_principal_support(self, dir_instance, principal_type, is_rw):
        support = dir_instance.principal_enabled(principal_type)
        if is_rw:
            return support == Directory.READ_WRITE_SUPPORT
        return support != Directory.NO_SUPPORT

    def _check_group_support(self, dir_instance, group_type, is_rw):
        support = dir_instance.group_enabled(group_type)
        if is_rw:
            return support == Directory.READ_WRITE_SUPPORT
        return support != Directory.NO_SUPPORT

    def _delegate_to_first(self, dir_name, chk_method, method, *args,
            **kwargs):
        def _tag_result_with_dir(res, dir_name):
            return (dir_name, res)

        if dir_name is not None and dir_name != "":
            # Name specifies particular directory
            if not self.instances_by_name.has_key(dir_name):
                errmsg = "No directory found (in d2f) for name '%s'" %(dir_name)
                lg.error(errmsg)
                raise DirectoryException(errmsg,
                        DirectoryException.NONEXISTING_NAME)
            instance = self.instances_by_name[dir_name]
            if not chk_method(instance._instance):
                msg = "Directory '%s' doesn't support method '%s'" \
                        %(dir_name, method)
                lg.error(msg)
                raise DirectoryException(msg,
                        DirectoryException.OPERATION_NOT_PERMITTED)
            func = getattr(instance._instance, method)
            d = func(*args, **kwargs)
        else:
            # Delegate to first directory that supports it
            d = None
            for instance in self.directory_instances:
                if chk_method(instance._instance):
                    dir_name = instance._name
                    func = getattr(instance._instance, method)
                    d = func(*args, **kwargs)
                    break
            if d is None:
                # Not enabled on any directory
                msg = "No directories found supporting method '%s'" %method
                lg.error(msg)
                raise DirectoryException(msg,
                        DirectoryException.OPERATION_NOT_PERMITTED)
        d.addCallback(_tag_result_with_dir, dir_name)
        return d

    def _delegate_to_all(self, res, instance, results, dir_instances,
            chk_method, method, result_mangler, *args, **kwargs):
        if instance is None:
            results = results or {}
        else:
            if result_mangler is not None:
                results[instance._name] = result_mangler(res, instance)
            else:
                results[instance._name] = res
        d = None
        while d is None and len(dir_instances) > 0:
            instance = dir_instances.pop(0)
            if chk_method(instance._instance):
                func = getattr(instance._instance, method)
                d = func(*args, **kwargs)
        if d is None:
            #out of directories
            ret = []
            for value in results.values():
                ret.extend(value)
            d = defer.succeed(ret)
        else:
            d.addCallback(self._delegate_to_all, instance, results,
                    dir_instances, chk_method, method,
                    result_mangler, *args, **kwargs)
        return d

    def _delegate_query_to_all(self, res, instance, results, dir_instances,
            chk_method, method, result_mangler, principal_type, query):
        if instance is None:
            results = results or {}
        else:
            if isinstance(res,Failure):
                if not isinstance(res.value, DirectoryException):
                    raise res
                results[instance._name] = res.value
            else:
                results[instance._name] = result_mangler(res, instance)
        d = None
        while d is None and len(dir_instances) > 0:
            instance = dir_instances.pop(0)
            if chk_method(instance._instance):
                func = getattr(instance._instance, method)
                # We may not be inside a deferred yet, so we have to
                # catch exceptions instead of waiting for a Failure
                try:
                    # copy query_dict to protect against directories mucking
                    # it up
                    d = func(principal_type, query.copy())
                except DirectoryException, e:
                    results[instance._name] = e

        if d is None:
            ret = []
            exc_count = 0
            for name, result in results.items():
                if isinstance(result, Exception):
                    exc_count += 1
                else:
                    ret.extend(result)
            if exc_count > 0 and exc_count == len(results):
                # If any of the exceptions were just an invalid query,
                # we return that, otherwise return any exception
                for exc in results.values():
                    if isinstance(exc, DirectoryException) \
                       and exc.code == DirectoryException.INVALID_QUERY:
                        return defer.fail(Failure(exc))
                exc = results.items()[0][1]
                if isinstance(exc, DirectoryException):
                    return defer.fail(exc)
                return defer.fail(Failure(DirectoryException(
                        "Query '%s' failed: '%s'" %(query, exc))))
            else:
                return defer.succeed(ret)
        else:
            d.addCallback(self._delegate_query_to_all, instance, results,
                    dir_instances, chk_method, method, result_mangler,
                    principal_type, query)
            d.addErrback(self._delegate_query_to_all, instance, results,
                    dir_instances, chk_method, method, result_mangler,
                    principal_type, query)
            return d

    def _get_dirs_for_group_name(self, name, group_type, dir_name,
            include_global=True):
        if name is None:
            dm_name = None
            dm_dir = dir_name
        else:
            (dm_dir, dm_name) = demangle_and_deconflict_name(name, dir_name)
        local_instances = []
        global_instances = []
        if dm_dir is not None and dm_dir != "":
            include_all_local=False
            #add specified directory
            if not self.instances_by_name.has_key(dm_dir):
                raise DirectoryException("No directory found for name '%s'"
                        %(dm_dir), DirectoryException.NONEXISTING_NAME)
            did = self.instances_by_name[dm_dir]
            instance = did._instance
            if self._check_group_support(instance, group_type, False):
                if instance.supports_global_groups():
                    if not include_global:
                        global_instances.append(did)
                    #else we'll add this (in order) when we add global groups
                else:
                    local_instances.append(did)
        else:
            include_all_local=True
        if include_global or include_all_local:
            for instance in self.directory_instances:
                if instance._instance.supports_global_groups():
                    if include_global:
                        global_instances.append(instance)
                elif include_all_local:
                    local_instances.append(instance)
        return (dm_name, dm_dir, local_instances, global_instances)

    @staticmethod
    def _ensure_proper_mangling(dirname, want_mangled, namelist):
        ret = []
        for name in namelist:
            if not isinstance(name, basestring):
                ret.append(name)
                continue
            (dm_directory, dm_name) = demangle_name(name)
            if dm_directory == "":
                #wasn't mangled
                if want_mangled:
                    ret.append(mangle_name(dirname, name))
                else:
                    ret.append(name)
            elif not want_mangled:
                #was mangled but we don't want it to be
                if dm_directory != dirname:
                    raise Exception("Directory name mismatch")
                ret.append(dm_name)
            else:
                #was mangled like we want
                ret.append(name)
        return ret

    def _delegate_mod_group_membership(self, group_type, group_name,
            member_names, subgroup_names, dir_name, add_members, chk_method):
        if add_members:
            method = 'add_group_members'
        else:
            method = 'del_group_members'

        (dm_dir, dm_name) = demangle_and_deconflict_name(group_name, dir_name)
        if dm_dir in self.instances_by_name:
            instance = self.instances_by_name[dm_dir]
            groups_global = instance._instance.supports_global_groups()
        else:
            raise DirectoryException("Required directory name not provided",
                    DirectoryException.BADLY_FORMATTED_NAME)
        member_names = self._ensure_proper_mangling(dm_dir, groups_global,
                member_names)
        subgroup_names = self._ensure_proper_mangling(dm_dir, groups_global,
                subgroup_names)

        m_group_name = mangle_name(dm_dir,dm_name)
        log_group_modification(self.uel, group_type, method, 
              m_group_name, member_names, subgroup_names)
        
        d = self._delegate_to_first(dm_dir, chk_method, method,
                group_type,dm_name, member_names, subgroup_names)

        def _mangle_delegate_res(delegate_res):
            (dm_dir, (member_names, subgroup_names)) = delegate_res
            if group_type != Directory.DLADDR_GROUP \
                    and group_type != Directory.NWADDR_GROUP:
                member_names = directorymanager._ensure_proper_mangling(dm_dir,
                        True, member_names)
                subgroup_names = directorymanager._ensure_proper_mangling(
                        dm_dir, True, subgroup_names)
            return (member_names, subgroup_names)

        def _post_modify_event(res):
            (member_names, subgroup_names) = res
            if add_members:
                m_change_type = Group_change_event.ADD_PRINCIPAL
                sg_change_type = Group_change_event.ADD_SUBGROUP
            else:
                m_change_type = Group_change_event.DEL_PRINCIPAL
                sg_change_type = Group_change_event.DEL_SUBGROUP
            for m in member_names:
                if isinstance(m, basestring):
                    memberstr = m.encode('utf-8')
                else:
                    memberstr = str(m)
                e = Group_change_event(group_type, m_group_name.encode('utf-8'),
                                       m_change_type, memberstr)
                self.post(e)
            for sg in subgroup_names:
                e = Group_change_event(group_type, m_group_name.encode('utf-8'),
                                       sg_change_type, sg.encode('utf-8'))
                self.post(e)
            return res
        d.addCallback(_mangle_delegate_res)
        d.addCallback(_post_modify_event)
        return d

    @staticmethod
    def _mangle_info_from_delegate(delegate_res):
        dir, info = delegate_res
        if info is None:
            return info
        info.name = mangle_name(dir, info.name)
        return info

    @staticmethod
    def _mangle_grpinfo_from_delegate(delegate_res, group_type):
        (dm_dir, groupinfo) = delegate_res
        if groupinfo is None:
            return groupinfo

        if group_type != Directory.DLADDR_GROUP \
                and group_type != Directory.NWADDR_GROUP:
            member_names = directorymanager._ensure_proper_mangling(dm_dir,
                    True, groupinfo.member_names)
            subgroup_names = directorymanager._ensure_proper_mangling(dm_dir,
                    True, groupinfo.subgroup_names)
        else:
            member_names = groupinfo.member_names
            subgroup_names = groupinfo.subgroup_names
        name = mangle_name(dm_dir, groupinfo.name)
        if hasattr(groupinfo, 'description'):
            desc = groupinfo.description
        else:
            desc = None
        return GroupInfo(name, desc, member_names, subgroup_names)

    def _post_host_event(self, hostinfo):
        for ni in hostinfo.netinfos:
            dladdr = create_eaddr(ni.dladdr or 0)
            nwaddr = create_ipaddr(ni.nwaddr or 0)
            dpid = ni.dpid or datapathid.from_host(0)
            port = ni.port or 0
            nime = NetInfo_mod_event(dladdr, nwaddr, dpid, port, 
                    ni.is_router, ni.is_gateway)
            self.post(nime)
        return hostinfo

    def _update_discovered_gws(self, hostinfo):
        def _err(failure):
            lg.warn("Failed to update group %s: %s"
                    %(self.discovered_dir.GATEWAYS_GROUP_NAME, failure))
        is_gw = False
        for ni in hostinfo.netinfos:
            is_gw = is_gw or ni.is_gateway
        if is_gw:
            d = self.discovered_dir.add_group_members(
                    Directory.HOST_PRINCIPAL_GROUP,
                    self.discovered_dir.GATEWAYS_GROUP_NAME, [hostinfo.name])
        else:
            d = self.discovered_dir.del_group_members(
                    Directory.HOST_PRINCIPAL_GROUP,
                    self.discovered_dir.GATEWAYS_GROUP_NAME, [hostinfo.name])
        d.addErrback(_err)
        return hostinfo

    ## --
    ## Principals
    ## --
    def add_principal(self, principal_type, principal_info, dir_name=""):
        (dm_dir, principal_info) = \
                demangle_and_deconflict_info(principal_info, dir_name)
        chk_method = lambda instance : \
                self._check_principal_support(instance, principal_type, True)
        d = self._delegate_to_first(dm_dir, chk_method,
                'add_principal', principal_type, principal_info)
        d.addCallback(self._mangle_info_from_delegate)
        if principal_type == Directory.HOST_PRINCIPAL:
            d.addCallback(self._post_host_event)
            d.addCallback(self._update_discovered_gws)
        return d

    def modify_principal(self, principal_type, principal_info, dir_name=""):
        (dm_dir, principal_info) = \
                demangle_and_deconflict_info(principal_info, dir_name)
        chk_method = lambda instance : \
                self._check_principal_support(instance, principal_type, True)
        d = self._delegate_to_first(dm_dir, chk_method,
                'modify_principal', principal_type, principal_info)
        d.addCallback(self._mangle_info_from_delegate)
        if principal_type == Directory.HOST_PRINCIPAL:
            d.addCallback(self._post_host_event)
            d.addCallback(self._update_discovered_gws)
        return d

    def add_or_modify_principal(self, principal_type, principal_info,
            dir_name=""):
        def _modify_if_existing(failure):
            if isinstance(failure.value, DirectoryException):
                if failure.value.code == \
                        DirectoryException.RECORD_ALREADY_EXISTS:
                    return self.modify_principal(principal_type,
                            principal_info, dir_name)
            return failure
        d = self.add_principal(principal_type, principal_info, dir_name)
        d.addErrback(_modify_if_existing)
        return d

    def rename_principal(self, principal_type, old_name, new_name,
            old_dir_name, new_dir_name):
        def _verify_does_not_exist(res):
            if res is not None:
                raise DirectoryException("Invalid rename. " + \
                        "Name '%s' already exists in "
                        "directory '%s'" %(new_name, new_dir_name),
                        DirectoryException.RECORD_ALREADY_EXISTS)
            return res
        
        def _verify_does_exist(res):
            if res is None:
                raise DirectoryException("Invalid rename. " +  \
                        "Name '%s' does not exist in "
                        "directory '%s'" %(new_name, new_dir_name),
                        DirectoryException.NONEXISTING_NAME)
            return res

        def _add_principal_to_new_dir(pinfo):
            if pinfo is None:
                raise DirectoryException("Principal '%s' not found"
                        %old_name, DirectoryException.NONEXISTING_NAME)
            pinfo.name = mangle_name(dm_newdir, dm_newname)
            return self.add_principal(principal_type, pinfo, dm_newdir)

        def _post_ren_event(res):
            oldname = mangle_name(dm_olddir, dm_oldname).encode('utf-8')
            newname = mangle_name(dm_newdir, dm_newname).encode('utf-8')
            log_rename(self.uel, principal_type,oldname,newname)
            pne = Principal_name_event(principal_type, oldname, newname)
            self.post(pne)

            if principal_type == Directory.SWITCH_PRINCIPAL and \
                    hasattr(res, 'locations'):
                for loc in res.locations:
                    if hasattr(loc, '_old_name'):
                        oldlname = mangle_name(dm_olddir, loc._old_name)
                    else:
                        oldlname = mangle_name(dm_olddir, loc.name)
                    oldlname = oldlname.encode('utf-8')
                    newlname = mangle_name(dm_newdir, loc.name)
                    newlname = newlname.encode('utf-8')
                    if newlname != oldlname:
                        lptype = Directory.LOCATION_PRINCIPAL
                        log_rename(self.uel, lptype, oldlname, newlname)
                        pne = Principal_name_event(lptype, oldlname, newlname)
                        self.post(pne)
            return res

        def _add_new_member_to_global_groups(res, instance):
            def _got_old_groups(to_add):
                to_add = list(to_add)
                if len(to_add) == 0:
                    return None
                groupname = to_add.pop()
                d = instance.add_group_members(gt, groupname,
                        [newname,])
                d.addCallback(lambda res : _got_old_groups(to_add))
                return d
            if principal_type in Directory.PRINCIPAL_TO_PRINCIPAL_GROUP:
                gt = Directory.PRINCIPAL_TO_PRINCIPAL_GROUP[principal_type]
                oldname = mangle_name(dm_olddir, dm_oldname).encode('utf-8')
                newname = mangle_name(dm_newdir, dm_newname).encode('utf-8')
                d = instance.get_group_membership(gt, oldname)
                d.addCallback(_got_old_groups)
                return d
            return defer.succeed(None)

        def _verify_creds_enabled(creds):
            new_cred_support = newdir_did._instance.get_enabled_auth_types()
            for cred in creds:
                if not cred.type in new_cred_support:
                    raise DirectoryException("Directory '%s' does not "
                            "support credentials for '%s'; move aborted"
                            %(dm_newdir, dm_oldname))
            return creds

        (dm_olddir, dm_oldname) = demangle_and_deconflict_name(old_name,
                old_dir_name)
        (dm_newdir, dm_newname) = demangle_and_deconflict_name(new_name,
                new_dir_name)
        same_dir = dm_olddir == dm_newdir
        same_name = dm_oldname == dm_newname
        if same_dir and same_name:
            chk_method = lambda instance : self._check_principal_support(
                    instance, principal_type, True)
            d = self._delegate_to_first(dm_olddir, chk_method,
                    'get_principal', principal_type, dm_oldname)
            d.addCallback(self._mangle_info_from_delegate)
            d.addCallback(_verify_does_exist)
            return d # do not post a rename event!
        elif same_dir:
            chk_method = lambda instance : self._check_principal_support(
                    instance, principal_type, True)
            d = self._delegate_to_first(dm_olddir, chk_method,
                    'rename_principal', principal_type, dm_oldname, dm_newname)
            d.addCallback(self._mangle_info_from_delegate)
        else:
            if principal_type == Directory.LOCATION_PRINCIPAL:
                raise DirectoryException("Locations may not be renamed "
                        "across directories, rename the switch instead",
                        DirectoryException.OPERATION_NOT_PERMITTED)
            olddir_did = self.instances_by_name.get(dm_olddir)
            newdir_did = self.instances_by_name.get(dm_newdir)
            if not olddir_did or not newdir_did:
                raise DirectoryException("Invalid directory name",
                        DirectoryException.NONEXISTING_NAME)
            if olddir_did._instance.principal_enabled(principal_type) \
                    != Directory.READ_WRITE_SUPPORT:
                raise DirectoryException("'%s' does not support writes"
                        %dm_olddir, DirectoryException.OPERATION_NOT_PERMITTED)
            if newdir_did._instance.principal_enabled(principal_type) \
                    != Directory.READ_WRITE_SUPPORT:
                raise DirectoryException("'%s' does not support writes"
                        %dm_newdir, DirectoryException.OPERATION_NOT_PERMITTED)

            d = self.get_principal(principal_type, dm_newname, dm_newdir)
            d.addCallback(_verify_does_not_exist)
            d.addCallback(lambda res : 
                    self.get_credentials(principal_type, dm_oldname,
                            None, dm_olddir))
            d.addCallback(_verify_creds_enabled)

            vargs = {}
            if principal_type == Directory.SWITCH_PRINCIPAL:
                vargs["include_locations"] = True
            d.addCallback(lambda res : 
                    self.get_principal(principal_type, dm_oldname,
                    dm_olddir, **vargs))
            d.addCallback(_add_principal_to_new_dir)
            #if old_dir supports global groups, add new_name as member
            #of all groups that old_name was a member of
            if olddir_did._instance.supports_global_groups():
                d.addCallback(_add_new_member_to_global_groups,
                        olddir_did._instance)
            d.addCallback(lambda res : 
                    self.get_credentials(principal_type, dm_oldname,
                            None, dm_olddir))
            d.addCallback(lambda creds :
                    self.put_credentials(principal_type, dm_newname,
                            creds, dir_name=dm_newdir))
            d.addCallback(lambda res : 
                    self.del_principal(principal_type, dm_oldname, dm_olddir,
                            post_event=False))
            #TODO: if del fails, try to del from new?
        d.addCallback(_post_ren_event)
        return d

    def del_principal(self, principal_type, name, dir_name="",
            post_event=True):
        def _add_default_loc(res, state='entry', old_loc=None):
            # NOX assumes a location for all switch ports, so we need to
            # add a new default location after one is deleted
            if state == 'entry':
                d = self.search_principals(Directory.SWITCH_PRINCIPAL, 
                        {'dpid': res.dpid})
                d.addCallback(_add_default_loc, state='got_sw', old_loc=res)
            elif state == 'got_sw':
                if len(res) == 0:
                    #Database consistency error
                    lg.error("Could not get switch name for location %s" 
                            %dm_name)
                    switch_name = "unknown_switch"
                else:
                    switch_name = res[0]
                loc_name = get_default_loc_name(switch_name, old_loc.port_name)
                li = LocationInfo(loc_name, old_loc.dpid, old_loc.port,
                        old_loc.port_name)
                d = self.add_principal(Directory.LOCATION_PRINCIPAL, li)
                d.addCallback(_add_default_loc, state='new_added')
            elif state == 'new_added':
                #post location delete event to clear dynamic data and rename
                oldname = mangle_name(dm_dir, dm_name).encode('utf-8')
                newname = res.name.encode('utf-8')
                # post a location_delete_event so components with dynamic
                # state can know about the "rename with deleted state"
                lde = Location_delete_event(oldname, newname, res.dpid,
                        res.port)
                self.post(lde)
                return res
            else:
                raise DirectoryException("Invalid state: %s" %state)
            return d

        def _post_del_event(pi):
            if pi is not None:
                #Post the principal name event for static data updates
                oldname = mangle_name(dm_dir, dm_name).encode('utf-8')
                pne = Principal_name_event(principal_type, oldname, '')
                self.post(pne)
                if principal_type == Directory.SWITCH_PRINCIPAL:
                    if hasattr(pi, 'locations'):
                        for loc in pi.locations:
                            if hasattr(loc, '_old_name'):
                                oldlname = mangle_name(dm_dir, loc._old_name)
                            else:
                                oldlname = mangle_name(dm_dir, loc.name)
                            oldlname = oldlname.encode('utf-8')
                            lptype = Directory.LOCATION_PRINCIPAL
                            pne = Principal_name_event(lptype, oldlname, '')
                            self.post(pne)
                    #close switch connection to remove switch from the network
                    self.ctxt.close_openflow_connection(pi.dpid.as_host())
                elif principal_type == Directory.HOST_PRINCIPAL:
                    # For now, authenticator listens for the principal name
                    # event and posts the host_event for us.  It may be
                    # cleaner for us to post this event in the future.
                    pass
                elif principal_type == Directory.USER_PRINCIPAL:
                    # For now, authenticator listens for the principal name
                    # event and posts the user_event for us.  It may be
                    # cleaner for us to post this event in the future.
                    pass
            return pi

        (dm_dir, dm_name) = demangle_and_deconflict_name(name, dir_name)
        chk_method = lambda instance : \
                self._check_principal_support(instance, principal_type, True)
        d = self._delegate_to_first(dm_dir, chk_method,
                'del_principal', principal_type, dm_name)
        d.addCallback(self._mangle_info_from_delegate)
        if post_event:
            if principal_type == Directory.LOCATION_PRINCIPAL:
                d.addCallback(_add_default_loc)
            d.addCallback(_post_del_event)
        return d

    def get_principal(self, principal_type, name, dir_name="", *args, **vargs):
        (dm_dir, dm_name) = demangle_and_deconflict_name(name, dir_name)
        chk_method = lambda instance : \
                self._check_principal_support(instance, principal_type, False)
        d = self._delegate_to_first(dm_dir, chk_method,
                'get_principal', principal_type, dm_name, *args, **vargs)
        d.addCallback(self._mangle_info_from_delegate)
        return d

    def search_principals(self, principal_type, query_dict, dir_name=""):
        """Pass the query to specified directory or all directories if
        directory is not specified via "dir_name" or mangled name in query_dict
        """
        (dm_dir, query_dict) = \
                demangle_and_deconflict_query(query_dict, dir_name)
        chk_method = lambda instance : \
                self._check_principal_support(instance, principal_type, False)
        if dm_dir is not None and dm_dir != "":
            #specific directory requested
            if not self.instances_by_name.has_key(dm_dir):
                errmsg = "No directory found (in sp) for name '%s'" %(dm_dir)
                lg.error(errmsg)
                return defer.fail(DirectoryException(errmsg))
            dir_instance = self.instances_by_name[dm_dir]._instance
            if not chk_method(dir_instance):
                return defer.fail(DirectoryException(
                        "Directory '%s' does not support %ss"
                        %(dm_dir,
                        Directory.PRINCIPAL_TYPE_TO_NAME[principal_type]),
                        DirectoryException.OPERATION_NOT_PERMITTED))
            dirs = [self.instances_by_name[dm_dir]]
        else:
            dirs = self.directory_instances[:]
        def _mangle_results(res, dir_instance):
            return [mangle_name(dir_instance._name, r) for r in res]
        d = self._delegate_query_to_all(None, None, {}, dirs, chk_method, 
                'search_principals', _mangle_results, principal_type,
                query_dict)
        return d

    ## --
    ## Groups
    ## --

    def search_groups(self, group_type, query_dict=None, dir_name=""):
        """Returns deferred returning list of group names

        Pass the query to specified directory or all directories if
        directory is not specified via "dir_name" or mangled name in query_dict

        Raises DirectoryException on invalid query parameter
        """
        query_dict = query_dict or {}
        (dm_dir, query_dict) = \
                demangle_and_deconflict_query(query_dict, dir_name)
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, False)
        if dm_dir is not None and dm_dir != "":
            if not self.instances_by_name.has_key(dm_dir):
                errmsg = "No directory found (in sg) for name '%s'" %(dm_dir)
                lg.error(errmsg)
                raise Exception(errmsg)
            dir_instance = self.instances_by_name[dm_dir]._instance
            if not chk_method(dir_instance):
                raise Exception("Directory '%s' does not support %ss"
                        %(dm_dir, Directory.GROUP_TYPE_TO_NAME[group_type]))
            dirs = [self.instances_by_name[dm_dir]]
        else:
            dirs = self.directory_instances[:]
        def _mangle_results(res, dir_instance):
            return [mangle_name(dir_instance._name, r) for r in res]
        d = self._delegate_query_to_all(None, None, {}, dirs, chk_method, 
                'search_groups', _mangle_results, group_type, query_dict)
        return d

    def get_group_membership(self, group_type, member_name=None, dir_name="",
            include_global=True):
        """Pass the group query to the appropriate directories

        If specific directory is not specified (via dir_name parameter or
        mangled member_name), all directories are searched.

        If include_global is True, group queries are also passed to all
        directories supporting global groups.
        """
        def _mangle_if_unmangled(res, dir_instance):
            #Global group directory may return the local_groups it was passed,
            #so check before mangling those again
            ret = []
            for name in res:
                if not is_mangled_name(name):
                    ret.append(mangle_name(dir_instance._name, name))
                else:
                    ret.append(name)
            return ret

        def local_group_cb(res):
            if len(global_instances) > 0:
                if isinstance(dm_name, basestring):
                    mangled_name = mangle_name(dm_dir, dm_name or "")
                else:
                    mangled_name = dm_name
                d = self._delegate_to_all(None, None, None, global_instances,
                        chk_method, 'get_group_membership',
                        _mangle_if_unmangled,
                        group_type, mangled_name, local_groups=res)
                d.addCallback(global_group_cb, res)
                return d
            else:
                return res

        def global_group_cb(res, local_groups):
            ret = set(res)
            ret |= set(local_groups)
            return list(ret)

        dm_dir = demangle_and_deconflict_name(member_name, dir_name)[0]
        dm_name, dm_dir, local_instances, global_instances = \
                self._get_dirs_for_group_name(member_name, group_type,
                        dm_dir, include_global)
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, False)
        d = self._delegate_to_all(None, None, None, local_instances,
                chk_method, 'get_group_membership',
                _mangle_result_list, group_type, dm_name)
        d.addCallback(local_group_cb)
        return d

    def get_group(self, group_type, group_name, dir_name=""):
        (dm_dir, dm_name) = demangle_and_deconflict_name(group_name, dir_name)
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, False)
        d = self._delegate_to_first(dm_dir, chk_method, 
                'get_group', group_type, dm_name)
        d.addCallback(self._mangle_grpinfo_from_delegate, group_type)
        return d

    def add_group(self, group_type, group_info, dir_name=""):
        """Directory must be specified via dir_name parameter or mangled
        name in group_info object
        """
        (dm_dir, group_info) = \
                demangle_and_deconflict_info(group_info, dir_name)
        if dm_dir in self.instances_by_name:
            instance = self.instances_by_name[dm_dir]
            groups_global = instance._instance.supports_global_groups()
        else:
            raise DirectoryException("Required directory name not provided",
                    DirectoryException.BADLY_FORMATTED_NAME)
        if groups_global:
            want_mangling = True
        else:
            want_mangling = False
        #ensure members and subgroups match our expected mangling
        group_info.member_names = self._ensure_proper_mangling(dm_dir,
                want_mangling, group_info.member_names)
        group_info.subgroup_names = self._ensure_proper_mangling(dm_dir,
                want_mangling, group_info.subgroup_names)

        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        d = self._delegate_to_first(dm_dir, chk_method,
                'add_group', group_type, group_info)
        d.addCallback(self._mangle_grpinfo_from_delegate, group_type)
        return d

    def modify_group(self, group_type, group_info, dir_name=""):
        (dm_dir, dm_name) = demangle_and_deconflict_info(group_info, dir_name)
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        d = self._delegate_to_first(dm_dir, chk_method,
                'modify_group', group_type, dm_name)
        d.addCallback(self._mangle_grpinfo_from_delegate, group_type)
        return d

    def get_group_parents(self, group_type, group_name, dir_name="",
            include_global=True):
        def _delegate_result(res, deferred, results=[]):
            results.append(res)
            if len(results) == 2:
                ret = []
                for result in results:
                    ret.extend(result)
                deferred.callback(ret)
        dm_name, dm_dir, local_instances, global_instances = \
                self._get_dirs_for_group_name(group_name, group_type, dir_name)
        mangled_name = mangle_name(dm_dir, dm_name or "")
        deferred = defer.Deferred()
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, False)
        #directories not supporting global groups get demangled name
        loc_def = self._delegate_to_all(None, None, None, local_instances,
                chk_method, 'get_group_parents',
                _mangle_result_list, group_type, dm_name)
        loc_def.addCallback(_delegate_result, deferred)
        #directories supporting global groups get mangled name
        all_def = self._delegate_to_all(None, None, None, global_instances,
                chk_method, 'get_group_parents',
                _mangle_result_list, group_type, mangled_name)
        all_def.addCallback(_delegate_result, deferred)
        return deferred

    def rename_group(self, group_type, old_name, new_name, old_dir_name,
            new_dir_name):
        def _migrate_sm(res, state, group=None):
            if state == "get_old_group":
                d = self.get_group(group_type, dm_oldname, dm_olddir)
                d.addCallback(_migrate_sm, state="add_to_new_dir")
            elif state == "add_to_new_dir":
                ginfo = res
                ginfo.name = dm_newname
                d = self.add_group(group_type, ginfo, dm_newdir)
                d.addCallback(_migrate_sm, state="added_to_new", group=ginfo)
            elif state == "added_to_new":
                d = defer.succeed(res)
                #if old_dir supports global groups, add new name as subgroup
                #of all groups that old_name was a subgroup of
                olddir_did = self.instances_by_name.get(dm_olddir)
                if olddir_did and olddir_did._instance.supports_global_groups():
                    d.addCallback(_add_new_subgroup_to_global_groups,
                            olddir_did._instance)
                d.addCallback(lambda res :
                        self.del_group(group_type, dm_oldname, dm_olddir,
                                post_event=False))
                d.addCallback(lambda res : group)
                d.addErrback(_del_new_group)
            else:
                raise DirectoryException("Invalid state: %s" %state)
            return d

        def _del_new_group(failure):
            deld = self.del_group(group_type, dm_newname, dm_newdir,
                                  post_event=False)
            deld.addCallbacks(lambda x : failure, lambda x : failure)
            return deld

        def _post_ren_event(res):
            gne = Group_name_event(group_type, oldname, newname)
            self.post(gne)
            return res

        def _add_new_subgroup_to_global_groups(res, instance):
            def _got_old_groups(to_add):
                if len(to_add) == 0:
                    return
                groupname = to_add.pop()
                d = instance.add_group_members(group_type, groupname,
                        [], [newname,])
                d.addCallback(lambda res : _got_old_groups(to_add))
                return d
            d = instance.get_group_parents(group_type, oldname)
            d.addCallback(lambda res : _got_old_groups(list(res)))
            return d

        (dm_olddir, dm_oldname) = demangle_and_deconflict_name(old_name,
                old_dir_name)
        (dm_newdir, dm_newname) = demangle_and_deconflict_name(new_name,
                new_dir_name)
        oldname = mangle_name(dm_olddir, dm_oldname).encode('utf-8')
        newname = mangle_name(dm_newdir, dm_newname).encode('utf-8')
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        if dm_olddir == dm_newdir:
            d = self._delegate_to_first(dm_olddir, chk_method,
                    'rename_group', group_type, dm_oldname, dm_newname)
            d.addCallback(self._mangle_grpinfo_from_delegate, group_type)
        else:
            d = _migrate_sm(None, state="get_old_group")
        d.addCallback(_post_ren_event)
        return d

    def del_group(self, group_type, group_name, dir_name="", post_event=True):
        def _post_del_event(gi):
            if gi is not None:
                gne = Group_name_event(group_type, gi.name.encode('utf-8'), '')
                self.post(gne)
            return gi

        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        (dm_dir, dm_name) = demangle_and_deconflict_name(group_name, dir_name)
        d = self._delegate_to_first(dm_dir, chk_method, 
                'del_group', group_type, dm_name)
        d.addCallback(self._mangle_grpinfo_from_delegate, group_type)
        if post_event:
            d.addCallback(_post_del_event)
        return d

    def add_group_members(self, group_type, group_name, member_names=[],
            subgroup_names=[], dir_name=""):
        """Directory must be specified via dir_name parameter or mangled
        name in group_info object
        """
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        return self._delegate_mod_group_membership(group_type, group_name,
                member_names, subgroup_names, dir_name,
                True, chk_method)

    def del_group_members(self, group_type, group_name, member_names=[],
            subgroup_names=[], dir_name=""):
        """Directory must be specified via dir_name parameter or mangled
        name in group_info object
        """
        chk_method = lambda instance : \
                self._check_group_support(instance, group_type, True)
        return self._delegate_mod_group_membership(group_type, group_name,
                member_names, subgroup_names, dir_name,
                False, chk_method)

    ## --
    ## Topology Properties
    ## --

    def _get_dir_instances(self, dir_name=None):
        if dir_name is not None and dir_name != '':
            if not self.instances_by_name.has_key(dir_name):
                errmsg = "No directory found for simple_auth for name '%s'"\
                        %(dir_name)
                raise DirectoryException(errmsg,
                        DirectoryException.NONEXISTING_NAME)
            instances = [self.instances_by_name[dir_name]]
        else:
            return self.directory_instances[:]

    @staticmethod
    def _get_last_result_as_bool(res):
        return len(res) > 0 and bool(res[-1][1])

    def _topology_properties_supported(self, instance):
        factory = self.directory_components.get(instance._instance.get_type())
        if factory is None:
            return False
        return factory.topology_properties_supported() != Directory.NO_SUPPORT

    def is_gateway(self, dladdr, dir_name=""):
        chk_method = self._topology_properties_supported
        d = self._delegate_until_stop(self._get_dir_instances(dir_name),
                chk_method, lambda inst, res: res is not None, 'is_gateway',
                dladdr)
        d.addCallback(self._get_last_result_as_bool)
        return d

    def is_router(self, dladdr, dir_name=""):
        chk_method = self._topology_properties_supported
        d = self._delegate_until_stop(self._get_dir_instances(dir_name),
                chk_method, lambda inst, res: res is not None, 'is_router',
                dladdr)
        d.addCallback(self._get_last_result_as_bool)
        return d

    ## --
    ## Principal name checks
    ## --

    def is_principal(self, principal_type, principal_name):
        d = self.search_principals(principal_type, {'name' : principal_name})
        d.addCallback(lambda x : len(x) > 0)
        return d

    def is_group(self, group_type, group_name):
        d = self.search_groups(group_type, {'name' : group_name})
        d.addCallback(lambda x : len(x) > 0)
        return d

    ## --
    ## Discovered principals
    ## --
    @staticmethod
    def _ignore_dir_dup(failure, ret_if_dup):
        if isinstance(failure.value, DirectoryException) and \
           failure.value.code == DirectoryException.RECORD_ALREADY_EXISTS:
            return ret_if_dup
        return failure

    def get_discovered_switch_name(self, dpid, ensure_in_dir=False):
        name = get_default_switch_name(dpid)
        mangled_name = mangle_name(self.discovered_dir.name, name)
        if not ensure_in_dir:
            return defer.succeed(mangled_name)
        si = SwitchInfo(name, dpid)
        d = self.discovered_dir.add_principal(Directory.SWITCH_PRINCIPAL, si)
        d.addCallback(lambda x : mangled_name)
        d.addErrback(self._ignore_dir_dup, mangled_name)
        return d

    def get_discovered_location_name(self, switch_name, port_name, dpid,
            port_number, ensure_in_dir=False):
        demangled = demangle_name(switch_name)
        if demangled[0] == "":
            demangled[0] = self.discovered_dir.name
        name = get_default_loc_name(demangled[1], port_name)
        mangled_name = mangle_name(demangled[0], name)
        if not ensure_in_dir:
            return defer.succeed(mangled_name)
        li = LocationInfo(name, dpid, port_number, port_name)
        d = self.add_principal(Directory.LOCATION_PRINCIPAL, li, demangled[0])
        d.addCallback(lambda x : mangled_name)
        d.addErrback(self._ignore_dir_dup, mangled_name)
        return d

    def get_discovered_host_name(self, dladdr, nwaddr, ensure_in_dir=False):
        if dladdr is not None:
            name = "host " + str(dladdr)
        elif nwaddr:
            name = "host " + str(create_ipaddr(nwaddr))
        else:
            raise DirectoryException(
                    "No dladdr or nwaddr provided to name host")
        mangled_name = mangle_name(self.discovered_dir.name, name)
        if not ensure_in_dir:
            return defer.succeed(mangled_name)
        nis = []
        if dladdr:
            nis.append(NetInfo(dladdr=dladdr))
        if nwaddr:
            nis.append(NetInfo(nwaddr=nwaddr))
        hi = HostInfo(name=name, netinfos=nis)
        d = self.discovered_dir.add_principal(Directory.HOST_PRINCIPAL, hi)
        d.addCallback(lambda x : mangled_name)
        d.addErrback(self._ignore_dir_dup, mangled_name)
        return d

    def add_discovered_switch(self, dpid):
      #used by default_switch_approval
      switch_name = get_default_switch_name(dpid)
      self.discovered_dir.add_switch(SwitchInfo(switch_name,dpid))
      return mangle_name(self.discovered_dir.name, switch_name)

    # called by authenticator to get a discovered directory name
    # for a host that has appeared on the network.  This method
    # DOES NOT ADD A HOST TO THE DIRECTORY.  That will happen 
    # when discovered directory receives a host-join event 
    # containing a disovered directory name.  
#    def get_discovered_host_name(self,dpid,port,dladdr,nwaddr,use_ip_name):
#      if use_ip_name: 
#        host_name = get_default_host_name(None, nwaddr)
#      else: 
#        host_name = default_host_name(dladdr, None)
#      return mangle_name(self.discovered_dir.name, host_name)
  
    # hack: we need to know if a name given to us 
    # was generated with 'use_ip_name'.  We assume
    # that a period will only appear in a name as 
    # part of an ip addresss, and (of course) that all 
    # ip addresses use periods as delimiters.  
    def is_discovered_ip_name(self,name):
      return name.find(".") != -1

    # registered handler for Host_events, which occur
    # on both host join and host leave.  
    def host_event(self, event):
      dir,pname = demangle_name(event.name) 
      if dir != self.discovered_dir.name: 
        return CONTINUE 

      if pname in self.discovered_dir.restricted_names: 
        return CONTINUE 

      if(event.action == Host_event.JOIN):
        fn = self.host_join
      else: 
        fn = self.host_leave
      mac = create_eaddr(event.dladdr) 
      dpid = datapathid.from_host(event.datapath_id)
      use_ip_name = self.is_discovered_ip_name(pname)
      fn(pname, use_ip_name, dpid,event.port,mac,event.nwaddr) 
      return CONTINUE 

    def host_join(self,name,use_ip_name,dpid,port,dladdr,nwaddr):
      if use_ip_name: 
        ninfo = NetInfo(nwaddr=nwaddr)
      else : 
        ninfo = NetInfo(dladdr=dladdr) 

      def err(res): 
        lg.error("error handling host_join for discovered dir: %s" % str(res))
      def get_ok(host_info): 
        if host_info == None: 
          hinfo = HostInfo(name=name,netinfos=[ninfo])
          hinfo._refcount = 1
          d = self.discovered_dir.add_host(hinfo)
        else:
          if not hasattr(host_info, "_refcount"):
            host_info._refcount = 0
          new_netinfo = True
          for n in host_info.netinfos:
            if n == ninfo:
              new_netinfo = False
          if new_netinfo == True: 
            host_info.netinfos.append(ninfo) 
          host_info._refcount += 1
          d = self.discovered_dir.modify_host(host_info)
        d.addErrback(err)
      
      d = self.discovered_dir.get_host(name) 
      d.addCallback(get_ok)
      d.addErrback(err) 
    
    def host_leave(self,name,use_ip_name,dpid,port,dladdr,nwaddr): 
      def err(res): 
        lg.error("error removing host from discovered dir: %s" % res)
      def get_ok(host_info): 
        if host_info: 
          if host_info._refcount > 1:
            host_info._refcount -= 1
            d = self.discovered_dir.modify_host(host_info) 
          else: 
            d = self.discovered_dir.del_host(name) 
          d.addErrback(err) 

      d = self.discovered_dir.get_host(name) 
      d.addCallback(get_ok)
      d.addErrback(err) 

    # we can just listen for datapath leave events 
    # since it does not introduce a circular dependancy
    def dp_leave(self,dpid):
      def err(res): 
        lg.error("error removing switch from discovered dir: %s" % str(res))
      def ok(res): 
        for switchname in res: 
          self.discovered_dir.del_switch(switchname) 
          # ignore deferred

      q = {"dpid": datapathid.from_host(dpid) }
      d = self.discovered_dir.search_switches(q) 
      d.addCallback(ok)
      d.addErrback(err) 
      return CONTINUE 

    #TODO: handle port_status events for port leaves (when the switch stays)

    def add_gateways_to_discovered(self, dir_name):
        def _err(failure):
            lg.debug("Ignoring gateways on directory %s : %s"
                    %(dir_name, failure.value))
        def _add_gw(host_list):
            if len(host_list):
                return self.discovered_dir.add_group_members(
                        Directory.HOST_PRINCIPAL_GROUP,
                        self.discovered_dir.GATEWAYS_GROUP_NAME, host_list, [])
            return defer.succeed(((),()))
        q = {'is_gateway' : True}
        d = self.search_principals(Directory.HOST_PRINCIPAL,
                {'is_gateway' : True}, dir_name)
        d.addCallbacks(_add_gw, _err)
        return d

    def renamed_principal(self, event):
        if demangle_name(event.oldname)[0] == self.discovered_dir.name:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        self.discovered_dir.rename_group_member(None, event.type,
                 event.oldname, event.newname)
        return CONTINUE

    def renamed_group(self, event):
        if demangle_name(event.oldname)[0] == self.discovered_dir.name:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        self.discovered_dir.rename_group_subgroup(None, event.type,
                 event.oldname, event.newname)
        return CONTINUE


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return directorymanager(ctxt)

    return Factory()
