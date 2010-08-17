#
# Copyright 2008 (C) Nicira, Inc.
#
import logging
import md5
import string
import time
from random import SystemRandom
from twisted.internet import defer, reactor, threads
from twisted.python.failure import Failure

from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *
from nox.lib.util import __dladdr_check__, __nwaddr_check__

from nox.netapps.directory.cidr_group_cache import cidr_group_cache
from nox.netapps.directory.directorymanager import *
from nox.netapps.directory.dir_utils import glob_to_regex
from nox.netapps.directory.pydirmanager import Principal_name_event
from nox.netapps.directory.pydirmanager import Group_name_event
from nox.netapps.storage import TransactionalStorage
from nox.netapps.storage.storage import Storage, StorageException
from nox.netapps.storage.StorageTableUtil import *

from nox.lib.directory import *
from nox.lib.netinet.netinet import ethernetaddr, ipaddr, create_eaddr,\
    create_ipaddr, c_htonl, c_ntohl, cidr_ipaddr

NOX_DIRECTORY_NAME = "Built-in"

lg = logging.getLogger('builtin_directory')

class PasswordCredentialRecord(StorageRecord):
    _salt_chars = string.ascii_letters + string.digits + string.punctuation
    _columns = { 
        'name'                  : str,
        'principal_type'        : int,
        'password_salt'         : str,
        'password_hash'         : str,
        'password_update_epoch' : int,
        'password_expire_epoch' : int,
    }
    __slots__ = _columns.keys()

    def __init__(self, name, principal_type, password=None, pw_salt=None,
            password_update_epoch=0, password_expire_epoch=0):
        password_update_epoch = password_update_epoch or 0
        password_expire_epoch = password_expire_epoch or 0
        if pw_salt is None:
            pw_salt = self._get_salt()
        self.name = name
        self.principal_type = principal_type
        self.password_salt = pw_salt 
        self.password_hash = self._get_pw_hash(password, pw_salt)
        if not password_update_epoch:
            password_update_epoch = int(time.time())
        self.password_update_epoch = password_update_epoch
        self.password_expire_epoch = password_expire_epoch

    def check_password(self, password):
        """Return True if password is valid for user, else False
        """
        if self.password_expire_epoch != 0 and \
                time.time() > self.password_expire_epoch:
            lg.debug("Password invalid for user '%s': user password is expired"\
                    %self.name)
            return False
        if self.password_hash is None:
            lg.debug("Password invalid for user '%s': user has no password set"\
                    %self.name)
            return False
        hash = self._get_pw_hash(password, self.password_salt)
        if hash != self.password_hash:
            lg.debug("Password invalid for user '%s': password does not match"\
                    %self.name)
            return False
        else:
            return True

    def _get_salt(self, length=10):
        rand = SystemRandom()
        return ''.join([rand.choice(PasswordCredentialRecord._salt_chars) \
                for c in [None]*length])

    def _get_pw_hash(self, password, salt):
        pwbytes = password.encode('utf-8')
        if password != None:
            m = md5.new()
            m.update(salt)
            m.update(pwbytes)
            return m.hexdigest()
        else:
            return None

    def to_credential(self):
        ret = PasswordCredential()
        if self.password_update_epoch != -1:
            ret.password_update_epoch = self.password_update_epoch
        if self.password_expire_epoch != -1:
            ret.password_expire_epoch = self.password_expire_epoch
        return ret
    
class PasswordCredentialTable(StorageTable):
    _table_name = 'nox_passwords'
    _table_indices = (
        ('name_type_idx', ("name", "principal_type")),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name,
                              PasswordCredentialRecord, self._table_indices,
                              cache_contents)

    def set_password(self, name, principal_type, password, pw_salt=None,
                     password_update_epoch=None, password_expire_epoch=None):
        def _del_old_pw(res, conn):
            d = self.remove_all_rows_for_query({'name':name,
                    'principal_type':principal_type}, conn=conn)
            d.addCallback(_pw_deleted, conn)
            return d
        def _pw_deleted(res, conn):
            if len(res):
                pwrec = res[0]
                pwrec.password_salt = pw_salt or pwrec.password_salt
                pwrec.password_hash = pwrec._get_pw_hash(password,
                        pwrec.password_salt)
                if password_expire_epoch is not None:
                    pwrec.password_expire_epoch = password_expire_epoch
                pwrec.password_update_epoch = password_update_epoch
            else:
                pwrec = PasswordCredentialRecord(name, principal_type,
                        password, pw_salt, password_update_epoch,
                        password_expire_epoch)
            d = self.put_record_no_dup(pwrec, ('name_type_idx',), conn=conn)
            d.addCallback(_pw_put, conn)
            return d
        def _pw_put(res, conn):
            lg.debug("Password for %s '%s' set" %(principal_type, name))
            return res

        if not password_update_epoch:
            password_update_epoch = int(time.time())
        return call_in_txn(self.storage, _del_old_pw)

class CertFpCredRecord(StorageRecord):
    _columns = {
        'name'           : str,
        'principal_type' : int,
        'fingerprint'    : str,
        'is_approved'    : int,
    }
    __slots__ = _columns.keys()

    def __init__(self, name, principal_type, fingerprint, is_approved=0):
        self.name = name
        self.principal_type = principal_type
        self.fingerprint = fingerprint
        self.is_approved = is_approved

    def to_credential(self):
        return CertFingerprintCredential(self.fingerprint.encode('utf8'),
                bool(self.is_approved))

class CertFpCredTable(StorageTable):
    _table_name = 'nox_cert_fingerprints'
    _table_indices = (
        ('name_type_idx', ("name", "principal_type")),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name,
                CertFpCredRecord, self._table_indices, cache_contents)

class UserRecord(StorageRecord):
    _columns = { 
        'user_id'               : int,
        'name'                  : str,
        'user_real_name'        : str,
        'description'           : str, 
        'location'              : str,
        'phone'                 : str, 
        'user_email'            : str,
    }
    __slots__ = _columns.keys()

    #--- Members ---
    def __init__(self, user_id, name, user_real_name=None, description=None,
            location=None, phone=None, user_email=None):
        self.user_id = user_id
        self.name = name
        self.user_real_name = user_real_name
        self.description = description
        self.location = location
        self.phone = phone
        self.user_email = user_email

    def to_UserInfo(self):
        ret = UserInfo(self.name, self.user_id)
        for attr in ['user_real_name', 'description', 'location',
                     'phone', 'user_email']:
            val = getattr(self, attr)
            if val is not None and len(val) > 0:
                setattr(ret, attr, val)
        return ret

class UserTable(StorageTable):
    _table_name = 'nox_users'
    _table_indices = (
        ('name_idx',        ("name",)),
        ('uid_idx',         ("user_id",)),
        ('real_name_idx',   ("user_real_name",)),
        ('description_idx', ("description",)),
        ('location_idx',    ("location",)),
        ('phone_idx',       ("phone",)),
        ('email_idx',       ("user_email",)),
    )

    def __init__(self, storage, pwcred_tbl, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, UserRecord, 
                              self._table_indices, cache_contents)
        self.pwcred_tbl = pwcred_tbl
        self.max_uid = -1

    def ensure_table_exists_cb(self, res):
        def _verify_admin_account(res):
            d = self.get_all_recs_for_query({'user_id': 0})
            d.addCallback(_create_admin_if_none)
            return d
        def _create_admin_if_none(res):
            def _set_pw_if_none(res, name):
                if not res:
                    lg.warn("Resetting default admin password for account '%s'"
                            %name)
                    d = self.pwcred_tbl.set_password(name,
                            Directory.USER_PRINCIPAL, 'admin')
                    return d
            if not res:
                lg.info("No admin account exists, adding default")
                return self._bootstrap_default_admin_user()
            else:
                d = self.pwcred_tbl.get_all_recs_for_query(
                        {"name": res[0].name,
                        'principal_type': Directory.USER_PRINCIPAL})
                d.addCallback(_set_pw_if_none, res[0].name)
        StorageTable.ensure_table_exists_cb(self, res)
        d = self._reset_max_uid()
        d.addCallback(_verify_admin_account)
        return d

    def _reset_max_uid(self):
        def _get_all_users_callback(res):
            for user in res:
                self.max_uid = max(self.max_uid, user.user_id)
            return self.max_uid
        #get all records to determine the max UID
        d = self.get_all_recs_for_query({})
        d.addCallback(_get_all_users_callback)
        return d

    def get_unique_uid(self):
        self.max_uid += 1
        return self.max_uid

    def _bootstrap_default_admin_user(self):
        def _set_admin_password(res):
            return self.pwcred_tbl.set_password(res.name,
                    Directory.USER_PRINCIPAL, 'admin')
        self.state = "Adding initial admin account"
        adminuser = UserRecord(user_id=0, name='admin',
                               description="Default administrator account")
        self.max_uid = 0
        d = self.put_record(adminuser)
        d.addCallbacks(self._add_user_callback, self._init_error)
        d.addCallback(_set_admin_password)
        return d

    def add_user(self, user_record, conn=None):
        old_max_uid = self.max_uid
        if user_record.user_id is None:
            user_record.user_id = self.get_unique_uid()
        else:
            self.max_uid = max(user_record.user_id, self.max_uid)
        d = self.put_record_no_dup(user_record,
                ('name_idx', 'uid_idx'), conn=conn)
        d.addErrback(self._add_user_errback)
        d.addCallback(self._add_user_callback)
        return d

    def _add_user_callback(self, res):
        lg.debug("Added user '%s'"%res.name)
        return res

    def _add_user_errback(self, failure):
        lg.info("Failure while adding user: %s" %str(failure.value))
        #TODO: race condition here
        d = self._reset_max_uid()
        returnRes = lambda x : failure
        d.addCallbacks(returnRes, returnRes)
        return d

    def _init_error(self, failure):
        lg.debug("Error '%s' initializing table '%s' while '%s'"
                %(failure, self._table_name, self.state))
        return failure

class GroupRecord(StorageRecord):
    # Usage overloaded: if memberName and subgroupName are empty,
    # this is the main group record.
    # Description is only valid for main group record.
    # Only one of memberName or subgroupName or description may be set
    # within a given member.

    # We stash the indices here since they are common to multiple tables
    # using this record format
    _table_indices = (
        ('name_idx',                ("name",)),
        ('memberName_idx',          ("memberName",)),
        ('subgroupName_idx',        ("subgroupName",)),
        ('groupMemberSubgroup_idx', ("name", "memberName", "subgroupName")),
    )

    # We store member names instead of GUIDs because we support global groups
    _columns = { 
        'name'         : str,
        'memberName'   : str,
        'subgroupName' : str,
        'description'  : str,
    }
    __slots__ = _columns.keys()

    def __init__(self, groupName, memberName=None, subgroupName=None,
            description=None):
        self.name = groupName
        self.memberName = memberName
        self.subgroupName = subgroupName
        self.description = description

class UserGroupTable(StorageTable):
    _table_name = 'nox_user_groups'

    def __init__(self, storage, user_tbl, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, GroupRecord,
                              GroupRecord._table_indices, cache_contents)
        self.user_tbl = user_tbl

    def ensure_table_exists_cb(self, res):
        StorageTable.ensure_table_exists_cb(self, res)
        d = self._ensure_nox_role_groups()
        d.addCallback(self._ensure_admin_group)
        return d

    def _ensure_nox_role_groups(self):
        def _created_cb(res, results=[]):
            results.append(res)
            if len(results) == len(NoxDirectory._nox_group_to_roles):
                lg.debug("All NOX Role groups created dropped")
                ret.callback(None)
        ret = defer.Deferred()
        for group_name, nox_role in NoxDirectory._nox_group_to_roles.items():
            rec = GroupRecord(group_name, description=nox_role)
            d = self.put_record_no_dup(rec, ('groupMemberSubgroup_idx',))
            d.addCallbacks(_created_cb, _created_cb)
        return ret

    def _ensure_admin_group(self, res=None, state="entry"):
        #if acct with UID 0 is not a member of 'network_admin_superusers',
        #make it so
        if state == "entry":
            d = self.user_tbl.get_all_recs_for_query({'USER_ID' : 0})
            d.addCallback(self._ensure_admin_group, state="get_admin_name")
        elif state == "get_admin_name":
            if len(res) != 1:
                raise Exception("Missing expected admin account")
            rec = GroupRecord("network_admin_superusers",
                    mangle_name(NOX_DIRECTORY_NAME, res[0].name))
            d = self.put_record_no_dup(rec, ('groupMemberSubgroup_idx',))
            d.addCallback(self._ensure_admin_group, state="group_added")
            d.addErrback(self._ensure_admin_group, state="group_add_error")
        elif state == "group_added":
            return
        elif state == "group_add_error":
            if type(res.value) == tuple and \
                    res.value[0] == Storage.INVALID_ROW_OR_QUERY:
                #group already existed - that's fine
                return
            else:
                return res
        else:
            raise Exception("Invalid state")
        return d

    def _init_error(self, failure):
        lg.debug("Error '%s' initializing table '%s' while '%s'"
                %(failure, self._table_name, self.state))
        return failure

class HostAliasRecord(StorageRecord):
    # Usage overloaded: if alias == name, this is the canonical host name.
    # description is only valid for canonical host name
    _columns = { 
        'name'        : str,
        'alias'       : str,
        'description' : str
    }
    __slots__ = _columns.keys()

    def __init__(self, name=None, alias=None, description=None):
        self.name        = name
        self.alias       = alias
        self.description = description

class HostAliasTable(StorageTable):
    _table_name = 'nox_host_aliases'
    _table_indices = (
        ('name_idx',       ("name",)),
        ('alias_idx',      ("alias",)),
        ('name_alias_idx', ("name","alias")),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name,
                              HostAliasRecord, self._table_indices,
                              cache_contents)

class HostNetInfoRecord(StorageRecord):
    StorageRecord._default_type_values[type(0)] = -1
    _columns = { 
        'name'         : str,
        'dladdr'       : int,
        'nwaddr'       : int,
        'dpid'         : int,
        'port'         : int, 
        'is_router'    : int,
        'is_gateway'   : int,
    }
    __slots__ = _columns.keys()

    def __init__(self, dpid, port, dladdr, nwaddr, name, is_router,
            is_gateway):
        self.dpid = dpid
        self.port = port
        self.nwaddr = nwaddr
        self.dladdr = dladdr
        self.name = name
        self.is_router = is_router
        self.is_gateway = is_gateway

    def to_NetInfo(self):
        dpid = None
        port = None
        dladdr = None
        nwaddr = None
        if self.dpid is not None and self.dpid != -1:
            dpid = datapathid.from_host(self.dpid)
        if self.port is not None and self.port != -1:
            port = self.port
        if self.dladdr is not None and self.dladdr != -1:
            dladdr = ethernetaddr(self.dladdr)
        if self.nwaddr is not None and self.nwaddr != -1:
            nwaddr = self.nwaddr
        return NetInfo(dpid, port, dladdr, nwaddr, bool(self.is_router),
                bool(self.is_gateway))

class HostNetInfoTable(StorageTable):
    _table_name = 'nox_host_net_info'
    _table_indices = (
        ('name_idx',      ("name",)),
        ('dladdr_idx',    ("dladdr",)),
        ('nwaddr_idx',    ("nwaddr",)),
        ('dpid_idx',      ("dpid",)),
        ('port_idx',      ("port",)),
        ('dpid_port_idx', ("dpid","port")),
        ('all_idx',       ("name","dladdr","nwaddr","dpid","port")),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name,
                              HostNetInfoRecord, self._table_indices,
                              cache_contents)

class HostGroupTable(StorageTable):
    _table_name = 'nox_host_groups'

    def __init__(self, storage, hostalias_tbl, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, GroupRecord,
                              GroupRecord._table_indices, cache_contents)
        self.hostalias_tbl = hostalias_tbl

class SwitchRecord(StorageRecord):
    _columns = { 
        'name' : str,
        'dpid' : int,
    }
    __slots__ = _columns.keys()

    def __init__(self, dpid, name):
        self.dpid = dpid
        self.name = name

    def to_SwitchInfo(self):
        ret = SwitchInfo(self.name)
        if self.dpid is not None and self.dpid != -1:
            ret.dpid = datapathid.from_host(self.dpid)
        return ret

class SwitchTable(StorageTable):
    _table_name = 'nox_switches'
    _table_indices = (
        ('dpid_idx', ("dpid",)),
        ('name_idx', ("name",)),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, SwitchRecord, 
                              self._table_indices, cache_contents)

class SwitchGroupTable(StorageTable):
    _table_name = 'nox_switch_groups'

    def __init__(self, storage, switch_table, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, GroupRecord,
                              GroupRecord._table_indices, cache_contents)
        self.switch_table = switch_table

class LocRecord(StorageRecord):
    _columns = { 
        'name'        : str,
        'dpid'        : int,
        'port'        : int,
        'port_name'   : str,

        'speed'       : int,
        'duplex'      : int,
        'auto_neg'    : int,
        'neg_down'    : int,
        'admin_state' : int,
    }
    __slots__ = _columns.keys()

    def __init__(self, dpid, port, name, port_name, speed, duplex,
            auto_neg, neg_down, admin_state):
        self.dpid = dpid
        self.port = port
        self.name = name
        self.port_name = port_name
        self.speed = speed
        self.duplex = duplex
        self.auto_neg = auto_neg
        self.neg_down = neg_down
        self.admin_state = admin_state

    def to_LocationInfo(self):
        ret = LocationInfo(self.name)
        if self.dpid is not None and self.dpid != -1:
            ret.dpid = create_datapathid_from_host(self.dpid)
        if self.port is not None and self.port != -1:
            ret.port = self.port
        if self.port_name is not None and self.port_name != '':
            ret.port_name = self.port_name
        if self.speed is not None and self.speed != -1:
            ret.speed = self.speed
        if self.duplex is not None and self.duplex != -1:
            ret.duplex = self.duplex
        if self.auto_neg is not None and self.auto_neg != -1:
            ret.auto_neg = self.auto_neg
        if self.neg_down is not None and self.neg_down != -1:
            ret.neg_down = self.neg_down
        if self.admin_state is not None and self.admin_state != -1:
            ret.admin_state = self.admin_state
        return ret

class LocTable(StorageTable):
    _table_name = 'nox_locations'
    _table_indices = (
        ('dpid_idx',      ("dpid",)),
        ('port_idx',      ("port",)),
        ('dpid_port_idx', ("dpid", "port")),
        ('name_idx',      ("name",)),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, LocRecord,
                              self._table_indices, cache_contents)

class LocGroupTable(StorageTable):
    _table_name = 'nox_location_groups'

    def __init__(self, storage, loc_table, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, GroupRecord,
                              GroupRecord._table_indices, cache_contents)
        self.loc_table = loc_table

class AddressGroupRecord(StorageRecord):
    # Usage overloaded: if memberAddr and subgroupName are empty,
    # this is the main group record.
    # Description is only valid for main group record.
    # Only one of memberAddr or subgroupName or description may be set
    # within a given member.

    _columns = {
        'name'         : str,
        'memberAddr'   : int,
        'prefixLen'    : int,
        'subgroupName' : str,
        'description'  : str,
    }
    __slots__ = _columns.keys()

    def __init__(self, groupName, memberAddr=None, prefixLen=None,
            subgroupName=None, description=None):
        self.name = groupName
        self.memberAddr = memberAddr
        self.prefixLen = prefixLen
        self.subgroupName = subgroupName
        self.description = description

class AddrGroupTable(StorageTable):
    _table_indices = (
        ('name_idx',                ("name",)),
        ('memberAddr_idx',          ("memberAddr","prefixLen")),
        ('subgroupName_idx',        ("subgroupName",)),
        ('groupMemberSubgroup_idx', ("name", "memberAddr", "prefixLen",
                                     "subgroupName")),
    )

    def __init__(self, storage, cache_contents=False):
        StorageTable.__init__(self, storage, self._table_name, 
                AddressGroupRecord, self._table_indices,
                cache_contents, version=1)

class DladdrGroupTable(AddrGroupTable):
    _table_name = 'nox_dladdr_groups'

class NwaddrGroupTable(AddrGroupTable):
    _table_name = 'nox_nwaddr_groups'

ALL_TABLE_NAMES = (UserTable._table_name, UserGroupTable._table_name,
                   HostNetInfoTable._table_name, HostAliasTable._table_name,
                   HostGroupTable._table_name,
                   LocTable._table_name, LocGroupTable._table_name,
                   SwitchTable._table_name, SwitchGroupTable._table_name, 
                   DladdrGroupTable._table_name, NwaddrGroupTable._table_name,
                   PasswordCredentialTable._table_name,
                   CertFpCredTable._table_name)

class NoxDirectory(Component, Directory):
    """Simple auth system for authenticating users against CDB table"""
    _default_groups_module = "nox.ext.apps.directory_nox.default_groups"
    _table_cnt = 7
    _nox_group_to_roles = {
        'network_admin_superusers'   : 'Superuser',
# NOTE: the following roles are disabled pending further UI functionality
#        'NOX_Policy_administrators' : 'Policy Administrator',
#        'NOX_Network_operators'     : 'Network Operator',
#        'NOX_Security_operators'    : 'Security Operator',
#        'NOX_Viewer'                : 'Viewer',
#        'NOX_No_access'             : 'No Access',
    }

    def __init__(self, ctxt):
        Directory.__init__(self)
        Component.__init__(self, ctxt)
        self.storage = None
        self.conn = None
        self._is_registered = False

        self.user_tbl        = None
        self.usergroup_tbl   = None
        self.switch_tbl      = None
        self.switchgroup_tbl = None
        self.loc_tbl         = None
        self.locgroup_tbl    = None
        self.hostalias_tbl   = None
        self.hostni_tbl      = None
        self.hostgroup_tbl   = None
        self.pwcred_tbl      = None
        self.dladdrgroup_tbl = None
        self.nwaddrgroup_tbl = None

        self.cidr_cache = cidr_group_cache()
        self.group_to_table = {}
        self.cred_to_table = {}

    def install(self):
        self.storage = self.resolve(TransactionalStorage)
        if self.storage is None:
            raise Exception("Unable to resolve required component '%s'"
                            %str(TransactionalStorage))
        self.dirmgr = self.resolve(directorymanager)
        if self.dirmgr is None:
            raise Exception("Unable to resolve required component '%s'"
                            %str(directorymanager))

        def _init_conn_cb(res):
            result, conn = res
            if result[0] != Storage.SUCCESS:
                lg.error("Failed to connect to transactional storage: %d (%s)"
                        %(result[0], result[1]))
                return
            lg.debug("Connected to transactional storage, initializing schema")
            self.conn = conn
            d =  self.init_tables()
            d.addCallback(_tables_ready)
            return d

        def _tables_ready(res):
            d = self.create_default_groups()
            d.addCallback(_default_groups_created)
            return d

        def _default_groups_created(res):
            d = self.dirmgr.register_directory_component(self)
            d.addCallback(_component_registered)
            return d

        def _component_registered(res):
            # Ensure that there is one instance of nox_directory
            d = self.dirmgr.add_configured_directory(
                    NOX_DIRECTORY_NAME, self.get_type(), 0, 0,
                    ignore_if_dup_name=True)
            d.addCallback(_is_configured_cb)
            return d

        def _is_configured_cb(res):
            #Listen for name events to keep global groups up to date
            self.register_handler(Principal_name_event.static_get_name(),
                    self.handle_principal_name_event)
            self.register_handler(Group_name_event.static_get_name(),
                    self.handle_group_name_event)
            #done with init
            self._is_registered = True

        def _init_eb(failure):
            lg.error("Failed to initialize schema: %s" %failure)
            failure.raiseException()

        d = self.storage.get_connection()
        d.addCallbacks(_init_conn_cb, _init_eb)
        return d

    def init_tables(self, res=None, state='entry'):
        lg.debug("Initializing schema in state '%s'" %state)
        if state == 'entry':
            self.pwcred_tbl = PasswordCredentialTable(self.storage)
            d = self.pwcred_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'pwcred_exists')
        elif state == 'pwcred_exists':
            self.cred_to_table[Directory.AUTH_SIMPLE] = self.pwcred_tbl
            self.certfpcred_tbl = CertFpCredTable(self.storage)
            d = self.certfpcred_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'certfpcred_exists')
        elif state == 'certfpcred_exists':
            self.cred_to_table[Directory.AUTHORIZED_CERT_FP] = \
                    self.certfpcred_tbl
            self.user_tbl = UserTable(self.storage, self.pwcred_tbl)
            d = self.user_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'user_exists')
        elif state == 'user_exists':
            self.usergroup_tbl = UserGroupTable(self.storage,
                    self.user_tbl)
            d = self.usergroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'usergroup_exists')
        elif state == 'usergroup_exists':
            self.group_to_table[Directory.USER_PRINCIPAL_GROUP] = \
                    self.usergroup_tbl
            self.hostni_tbl = HostNetInfoTable(self.storage)
            d = self.hostni_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'hostni_exists')
        elif state == 'hostni_exists':
            self.hostalias_tbl = HostAliasTable(self.storage)
            d = self.hostalias_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'hostalias_exists')
        elif state == 'hostalias_exists':
            self.hostgroup_tbl = HostGroupTable(self.storage,
                    self.hostalias_tbl)
            d = self.hostgroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'hostgroup_exists')
        elif state == 'hostgroup_exists':
            self.group_to_table[Directory.HOST_PRINCIPAL_GROUP] = \
                    self.hostgroup_tbl
            self.switch_tbl = SwitchTable(self.storage)
            d = self.switch_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'switch_exists')
        elif state == 'switch_exists':
            self.switchgroup_tbl = SwitchGroupTable(self.storage,
                    self.switch_tbl)
            d = self.switchgroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'switchgroup_exists')
        elif state == 'switchgroup_exists':
            self.group_to_table[Directory.SWITCH_PRINCIPAL_GROUP] = \
                    self.switchgroup_tbl
            self.loc_tbl = LocTable(self.storage)
            d = self.loc_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'loc_exists')
        elif state == 'loc_exists':
            self.locgroup_tbl = LocGroupTable(self.storage, self.loc_tbl)
            d = self.locgroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'locgroup_exists')
        elif state == 'locgroup_exists':
            self.group_to_table[Directory.LOCATION_PRINCIPAL_GROUP] = \
                    self.locgroup_tbl
            self.dladdrgroup_tbl = DladdrGroupTable(self.storage)
            d = self.dladdrgroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'dladdrgroup_exists')
        elif state == 'dladdrgroup_exists':
            self.group_to_table[Directory.DLADDR_GROUP] = \
                    self.dladdrgroup_tbl
            self.nwaddrgroup_tbl = NwaddrGroupTable(self.storage)
            d = self.nwaddrgroup_tbl.ensure_table_exists()
            d.addCallback(self.init_tables, 'nwaddrgroup_exists')
        elif state == 'nwaddrgroup_exists':
            self.group_to_table[Directory.NWADDR_GROUP] = \
                    self.nwaddrgroup_tbl
            d = self.nwaddrgroup_tbl.get_all_recs_for_query({})
            d.addCallback(self.init_tables, 'nwaddrgroup_query_result')
        elif state == 'nwaddrgroup_query_result':
            self._cache_cidr_recs(res)
            return
        else:
            raise Exception("Invalid State")
        return d

    def create_default_groups(self):
        def _create_cb(res, results=[]):
            results.append(res)
            if len(results) == len(default_groups):
                lg.debug("All default groups created")
                ret.callback(None)
        ret = defer.Deferred()
        try:
            groups_module = __import__(self._default_groups_module,
                    fromlist='*')
            default_groups = getattr(groups_module, 'default_groups', None)
            if default_groups is not None:
                if len(default_groups) == 0:
                    ret.callback(None)
                for group_rec in default_groups:
                    table = self.group_to_table.get(group_rec[0])
                    if table is None:
                        msg = "Invalid group type for group '%s' in default "\
                              "groups file" %group_rec[1]
                        lg.warn(msg)
                        ret.errback(DirectoryException(msg))
                    lg.debug("Creating default group type '%s' named '%s'"
                            %(Directory.GROUP_TYPE_TO_NAME[group_rec[0]],
                            group_rec[1]))
                    if group_rec[0] == Directory.DLADDR_GROUP \
                       or group_rec[0] == Directory.NWADDR_GROUP:
                        rec = AddressGroupRecord(group_rec[1],
                                description=group_rec[2])
                    else:
                        rec = GroupRecord(group_rec[1],
                                description=group_rec[2])
                    d = table.put_record_no_dup(rec,
                            ('groupMemberSubgroup_idx',))
                    d.addCallbacks(_create_cb, _create_cb)
            else:
                msg = "Failed to load default groups file: "\
                      "default_groups not defined"
                lg.warn(msg)
                ret.errback(DirectoryException(msg))
        except Exception, e:
            msg = "Failed to load default groups file: %s" %e
            lg.warn(msg)
            ret.errback(DirectoryException(msg))
        return ret

    def _is_initialized(self):
        if self._is_registered:
            return True
        return False

    def getInterface(self):
        return str(NoxDirectory)

    def _not_initialized_deferred(self):
        lg.debug("Unable to perform NoxDirectory operation, not initialized")
        return deferred.fail(Failure(exc_value=Exception("Not initialized")))

    # --
    # Meta information
    # --

    def get_type(self):
        return NOX_DIRECTORY_NAME

    def get_config_params(self):
        return {}
    
    def set_config_params(self,params): 
        lg.error("%s is ignoring the following params:" %NOX_DIRECTORY_NAME)
        for key,value in params.iteritems():
            lg.error("%s = %s" % (key,value)) 
        return defer.succeed({})

    def get_instance(self, name=None, config_id=None):
        #special case for nox_directory; "...there can be only one."
        lg.debug("Returning %s instance" %NOX_DIRECTORY_NAME)
        return defer.succeed(self)

    def supports_multiple_instances(self):
        return False

    def supports_global_groups(self):
        return True

    def get_status(self):
        return Directory.DirectoryStatus(Directory.DirectoryStatus.OK)

    # --
    # Authentication
    # --

    def supported_auth_types(self):
        return (Directory.AUTHORIZED_CERT_FP, Directory.AUTH_SIMPLE,)

    def _get_password_credential(self, name, principal_type):
        def _get_pwcred_cb(res):
            if len(res) == 0:
                return None
            assert(len(res) == 1, "Password credential for %s:%s not unique "\
                    "like it should be" %(principal_type, name))
            return res[0]
        d = self.pwcred_tbl.get_all_recs_for_query(
                {"name":name, 'principal_type':principal_type})
        d.addCallback(_get_pwcred_cb)
        return d

    def get_credentials(self, principal_type, principal_name, cred_type=None):
        def _get_creds(res, cred_tables, ret):
            if res is not None:
                ret.extend(res)
            if len(cred_tables) == 0:
                return ret
            table = cred_tables.pop()
            d = table.get_all_recs_for_query(
                    {"name":principal_name, 'principal_type':principal_type})
            d.addCallback(_get_creds, cred_tables, ret)
            return d

        if cred_type is not None and cred_type not in self.cred_to_table:
            raise DirectoryException("Unsupported credential type '%s'"
                    %cred_type)
        if cred_type is None:
            cred_tables = self.cred_to_table.values()
        else:
            cred_tables = [self.cred_to_table[cred_type]]
        d = _get_creds(None, cred_tables, [])
        d.addCallback(lambda recs : [rec.to_credential() for rec in recs])
        return d

    def put_credentials(self, principal_type, principal_name, cred_list,\
                              cred_type=None):
        def _do_put(res, tbl_to_recs, conn=None):
            d = _del_all_creds(res, tbl_to_recs.keys(), conn)
            d.addCallback(_set_creds, tbl_to_recs, conn, [])
            return d

        def _del_all_creds(res, tables_left, conn):
            if len(tables_left) == 0:
                return
            table = tables_left.pop()
            d = table.remove_all_rows_for_query(
                    {'name':principal_name, 'principal_type':principal_type},
                    conn=conn)
            d.addCallback(_del_all_creds, tables_left, conn)
            return d

        def _set_creds(res, tbl_to_recs, conn, ret):
            if len(tbl_to_recs) == 0: 
                return ret  #all done
            (table, cred_list) = tbl_to_recs.popitem()
            d = table.put_all_records_no_dup(cred_list, ('name_type_idx',), 
                    conn=conn)
            d.addCallback(lambda res : 
                    ret.extend([rec.to_credential() for rec in res]))
            d.addCallback(_set_creds, tbl_to_recs, conn, ret)
            return d

        def _cred_to_rec(cred):
            if cred.type == Directory.AUTH_SIMPLE:
                return PasswordCredentialRecord(principal_name, principal_type,
                        cred.password, None, cred.password_update_epoch,
                        cred.password_expire_epoch)
            elif cred.type == Directory.AUTHORIZED_CERT_FP:
                return CertFpCredRecord(principal_name, principal_type,
                        cred.fingerprint, int(cred.is_approved))
            raise DirectoryException("Unsupported credential type '%s'"
                    %cred_type)

        tbl_to_recs = {}
        if cred_type is None:
            for credtbl in self.cred_to_table.values():
                tbl_to_recs[credtbl] = []
        else: 
            tbl_to_recs[self.cred_to_table[cred_type]] = [] 
        for cred in cred_list:
            if not cred.type in self.cred_to_table:
                raise DirectoryException("Unsupported credential type '%s'"
                        %cred_type)
            table = self.cred_to_table[cred.type]
            tbl_to_recs[table] = tbl_to_recs.get(table) or []
            tbl_to_recs[table].append(_cred_to_rec(cred))

        if Directory.AUTH_SIMPLE in tbl_to_recs and \
                len(tbl_to_recs[Directory.AUTH_SIMPLE]) > 1:
            raise DirectoryException("Only one password may be supplied")
        d = call_in_txn(self.storage, _do_put, tbl_to_recs)
        return d

    def simple_auth(self, name, password, user=None):
        """Return deferred returning User object if auth successful, else None
        """
        if not self._is_initialized():
            return self._not_initialized_deferred()
        def _do_auth(res=None, state="entry", user=None):
            if state == 'entry':
                d = self.get_user_record(name)
                d.addCallback(_do_auth, state="got_user", user=None)
            elif state == 'got_user':
                if res is None:
                    lg.debug("Authentication failed for user '%s': user"\
                             "does not exist" %name)
                    return AuthResult(AuthResult.INVALID_CREDENTIALS, name)
                d = self._get_password_credential(name,
                        Directory.USER_PRINCIPAL)
                d.addCallback(_do_auth, state="got_credential", user=res)
            elif state == 'got_credential':
                if res is None:
                    lg.debug("Authentication failed for user '%s': user"\
                             "has no password set" %name)
                    return AuthResult(AuthResult.INVALID_CREDENTIALS, name)
                pwcred = res
                if pwcred.check_password(password):
                    d = self.get_group_membership(
                            Directory.USER_PRINCIPAL_GROUP, user.name)
                    d.addCallback(_do_auth, state="got_groups", user=user)
                else:
                    lg.debug("Authentication failed for user '%s': invalid "\
                             "password" %name)
                    return AuthResult(AuthResult.INVALID_CREDENTIALS, name)
            elif state == 'got_groups':
                ret = AuthResult(AuthResult.SUCCESS, name)
                ret.groups = ret.groups | set(res)
                for grp in res:
                    if self._nox_group_to_roles.has_key(grp):
                        ret.nox_roles = ret.nox_roles | \
                                set((self._nox_group_to_roles[grp],))
                return ret
            else:
                raise Exception("Invalid State")
            return d
        return _do_auth()

    def get_user_roles(self, username, local_groups=None):
        def _got_groups(group_list):
            ret = set()
            for grp in group_list:
                if self._nox_group_to_roles.has_key(grp):
                    ret = ret | set((self._nox_group_to_roles[grp],))
            return ret
        d = self.get_group_membership(Directory.USER_PRINCIPAL_GROUP, username, 
                local_groups)
        d.addCallback(_got_groups)
        return d

    ## --
    ## Network topology properties
    ## --

    def topology_properties_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def is_gateway(self, dladdr):
        def _got_netinfos(res):
            if len(res) == 0:
                return None
            for rec in res:
                if rec.is_gateway:
                    return True
            return False
        if dladdr is not None:
            dladdr = dladdr.hb_long()
        d = self.hostni_tbl.get_all_recs_for_query({'dladdr' : dladdr})
        d.addCallback(_got_netinfos)
        return d

    def is_router(self, dladdr):
        def _got_netinfos(res):
            if len(res) == 0:
                return None
            for rec in res:
                if rec.is_router:
                    return True
            return False
        if dladdr is not None:
            dladdr = dladdr.hb_long()
        d = self.hostni_tbl.get_all_recs_for_query({'dladdr' : dladdr})
        d.addCallback(_got_netinfos)
        return d

    # --
    # Principal Registration
    # --
    
    def _fail_unless_storage_success(self, res):
        #Storage may return callback, even if operation failed.  If not
        #success, branch to errback like directory.py dictates
        result, guid = res
        if result[0] != Storage.SUCCESS:
            return Failure(res)
        return res

    @staticmethod
    def _is_storage_failure(failure):
        if hasattr(failure, 'value') \
                and isinstance(failure.value, tuple) \
                and len(failure.value) == 2:
            return True
        return False

    def _fail_unless_single_item_list(self, res):
        if type(res) != list or len(res) != 1:
            return Failure("Expected list with 1 entry, got '%s'" %res)
        return res

    def _translate_query_to_db_types(self, query):
        if query.has_key('dpid'):
            assert(type(query['dpid']) == datapathid)
            query['dpid'] = query['dpid'].as_host()
        if query.has_key('dladdr'):
            assert(type(query['dladdr']) == ethernetaddr)
            query['dladdr'] = query['dladdr'].hb_long()
        return query

    def _manually_check_query(self, record, query):
        for key,val in query.items():
            if getattr(record, key) != val:
                return False
        return True
        
    def _search_table(self, table, qp):
        def _get_names_from_recs(res):
            return [rec.name for rec in res]
        exact_params = {}
        regex_params = {}
        for key, val in qp.items():
            if key.endswith('_glob'):
                regex_str = glob_to_regex(val)
                regex_params[key.rstrip('_glob')] = regex_str
            else:
                exact_params[key] = val
        d = table.get_all_recs_for_unindexed_query(exact_params, regex_params)
        d.addCallback(_get_names_from_recs)
        def err(res):
          raise Exception(res)
        d.addErrback(err)
        return d

    @staticmethod
    def _get_demangled_local_name(name):
        dm_dir, dm_name = demangle_name(name)
        if dm_dir == NOX_DIRECTORY_NAME:
            return dm_name
        return name

    @staticmethod
    def _ensure_mangled_name(name):
        if not isinstance(name, basestring):
            return name
        if not is_mangled_name(name):
            name = mangle_name(NOX_DIRECTORY_NAME, name)
        return name

    def _update_records(self, table, oldquery, newquery, update_cb, conn=None):
        def _ren(res, state="entry", conn=None):
            if state == "entry":
                if newquery is not None:
                    d = table.get_all_recs_for_query(newquery, conn=conn)
                    d.addCallback(_ren, state="searched_for_new", conn=conn)
                else:
                    return _ren([], state="searched_for_new", conn=conn)
            elif state == "searched_for_new":
                if len(res):
                    raise DirectoryException(
                            "Records already exist matching %s" %newquery,
                            DirectoryException.RECORD_ALREADY_EXISTS)
                d = table.get_all_recs_for_query(oldquery, conn=conn)
                d.addCallback(_ren, state="got_old", conn=conn)
            elif state == "got_old":
                for rec in res:
                    update_cb(rec)
                d = table.modify_all_records(res, conn=conn)
                d.addCallback(_ren, state="done", conn=conn)
            elif state == "done":
                lg.debug("Updated %d records" %len(res))
                return res
            else:
                raise Exception("Invalid state '%s'" %state)
            return d
        d = call_in_txn(self.storage, _ren, conn=conn)
        return d

    def rename_principal(self, principal_type, old_name, new_name):
        def _raise_ex_if_empty(res):
            if len(res) == 0:
                raise DirectoryException("No record found with name '%s'"
                        %old_name, DirectoryException.NONEXISTING_NAME)
            return res

        def _ren_host(res, conn):
            def _alias_ren_cb(rec):
                if rec.alias == rec.name:
                    rec.alias = new_name
                rec.name = new_name
            def _ren_aliases():
                d = self._update_records(self.hostalias_tbl, {'name':old_name},
                        {'alias':new_name}, _alias_ren_cb, conn=conn)
                d.addCallback(_raise_ex_if_empty)
                d.addCallback(self._rename_group_member, self.hostgroup_tbl,
                        old_name, new_name, conn=conn)
                d.addCallback(_aliases_renamed)
                return d
            def _aliases_renamed(res):
                infoobj = HostInfo()
                for aliasrec in res:
                    if aliasrec.name == aliasrec.alias:
                        infoobj.name = aliasrec.name
                        infoobj.description = aliasrec.description
                    else:
                        infoobj.aliases.append(aliasrec.alias)
                def _update_name_cb(rec):
                    rec.name = new_name
                d = self._update_records(self.hostni_tbl, {'name':old_name},
                        {'name':new_name}, _update_name_cb, conn=conn)
                d.addCallback(_nis_renamed, infoobj)
                d.addCallback(self._rename_creds, principal_type, old_name,
                        new_name, conn)
                return d
            def _nis_renamed(res, infoobj):
                for ni in res:
                    infoobj.netinfos.append(ni.to_NetInfo())
                return infoobj
            return _ren_aliases()

        def _ren_switch(res, conn):
            def _update_loc_groups(switchinfo, locs_left):
                if locs_left:
                    loc = locs_left.pop()
                    d = self._rename_group_member(switchinfo,
                            self.locgroup_tbl, loc._old_name, loc.name,
                            conn=conn)
                    d.addCallback(lambda x :
                            _update_loc_groups(switchinfo, locs_left))
                    return d
                else:
                    return switchinfo
            def _ren_locations(switchinfo):
                switchinfo.locations = []
                def _loc_ren_cb(locrec):
                    def_name = get_default_loc_name(old_name, locrec.port_name)
                    if locrec.name == def_name:
                        locrec.name = get_default_loc_name(new_name,
                                locrec.port_name)
                        li = locrec.to_LocationInfo()
                        li._old_name = def_name
                        switchinfo.locations.append(li)
                #get all associated locs
                oq = {'dpid' : switchinfo.dpid.as_host()}
                d = self._update_records(self.loc_tbl, oq, None,
                        _loc_ren_cb, conn=conn)
                d.addCallback(lambda res :
                        _update_loc_groups(switchinfo, switchinfo.locations[:]))
                return d

            d = _ren(None, self.switch_tbl, self.switchgroup_tbl, conn)
            d.addCallback(_ren_locations)
            return d

        def _ren(res, p_table, g_table, conn):
            def _update_name_cb(rec):
                rec.name = new_name
            d = self._update_records(p_table, {'name':old_name},
                    {'name':new_name}, _update_name_cb, conn=conn)
            d.addCallback(_raise_ex_if_empty)
            d.addCallback(self._rename_group_member, g_table, old_name,
                    new_name, conn=conn)
            if principal_type == self.SWITCH_PRINCIPAL:
                d.addCallback(lambda res : res[0].to_SwitchInfo())
            elif principal_type == self.LOCATION_PRINCIPAL:
                d.addCallback(lambda res : res[0].to_LocationInfo())
            elif principal_type == self.USER_PRINCIPAL:
                d.addCallback(lambda res : res[0].to_UserInfo())
            d.addCallback(self._rename_creds, principal_type, old_name,
                    new_name, conn)
            return d

        if principal_type == self.HOST_PRINCIPAL:
            d = call_in_txn(self.storage, _ren_host)
        elif principal_type == self.SWITCH_PRINCIPAL:
            d = call_in_txn(self.storage, _ren_switch)
        elif principal_type == self.LOCATION_PRINCIPAL:
            d = call_in_txn(self.storage, _ren, self.loc_tbl,
                    self.locgroup_tbl)
        elif principal_type == self.USER_PRINCIPAL:
            d = call_in_txn(self.storage, _ren, self.user_tbl,
                    self.usergroup_tbl)
        else:
            raise DirectoryException("Unsupported principal type '%s' in "
                    "rename_principal" %principal_type)
        return d

    def _rename_creds(self, pinfo, ptype, old_name, new_name, conn):
        def _ren(res, conn, tables_left=None):
            if tables_left is None:
                tables_left = self.cred_to_table.values()[:]
            if len(tables_left) == 0:
                return pinfo
            cred_tbl = tables_left.pop()
            def _update_name_cb(rec):
                rec.name = new_name
            d = self._update_records(cred_tbl,
                    {'name' : old_name, 'principal_type' : ptype},
                    None, _update_name_cb, conn=conn)
            d.addCallback(_ren, conn, tables_left)
            return d
        return call_in_txn(self.storage, _ren, conn=conn)
        
    def _rename_group_member(self, res, table, old_name, new_name, conn,
            memberField='memberName', state='entry', ret=None):
        if state == "entry":
            old_name = self._ensure_mangled_name(old_name)
            new_name = self._ensure_mangled_name(new_name)
            if old_name == new_name:
                return defer.succeed(res)
            q = {memberField : old_name}
            d = table.get_all_recs_for_query(q, conn=conn)
            d.addCallback(self._rename_group_member, table, old_name,
                    new_name, conn, memberField=memberField, 
                    state="got_old_members", ret=res)
        elif state == "got_old_members":
            for rec in res:
                setattr(rec, memberField, new_name)
            d = table.modify_all_records(res, conn=conn)
            d.addCallback(self._rename_group_member, table, old_name,
                    new_name, conn, memberField=memberField, 
                    state="done", ret=ret)
        elif state == "done":
            lg.debug("Updated %d group %s records ('%s' => '%s')"
                    %(len(res), memberField, old_name, new_name))
            return ret
        else:
            raise DirectoryException("Invalide state: '%s'" %state)
        return d
        
    def handle_principal_name_event(self, event):
        if demangle_name(event.oldname)[0] == NOX_DIRECTORY_NAME:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        lg.debug("Global principal renamed: %s %s=>%s" %(event.type,
                event.oldname, event.newname))
        self.global_principal_renamed(event.type, event.oldname, event.newname)
        return CONTINUE

    def handle_group_name_event(self, event):
        if demangle_name(event.oldname)[0] == NOX_DIRECTORY_NAME:
            # directorymanager has already added the new name to global groups
            return CONTINUE
        if event.newname is None:
            lg.debug("Group deleted: %s %s=>%s" %(event.type, event.oldname))
        else:
            lg.debug("Group renamed: %s %s=>%s" %(event.type, event.oldname,
                    event.newname))
        self.global_group_renamed(event.type, event.oldname, event.newname)
        return CONTINUE

    def global_principal_renamed(self, principal_type, old_name, new_name):
        if demangle_name(new_name)[0] == NOX_DIRECTORY_NAME:
            return defer.succeed(None)
        group_type = Directory.PRINCIPAL_TO_PRINCIPAL_GROUP.get(principal_type)
        if group_type is None:
            return defer.succeed(None)
        table = self._get_table_for_group(group_type)
        if new_name is None or new_name == '':
            #deleted
            d = table.remove_all_rows_for_query(
                    query={'memberName' : old_name})
        else:
            d = self._rename_group_member(None, table, old_name, new_name,
                    None)
        return d

    def global_group_renamed(self, group_type, old_name, new_name):
        table = self._get_table_for_group(group_type)
        if new_name is None or new_name == '':
            #deleted
            d = table.remove_all_rows_for_query(
                    query={'subgroupName' : old_name})
        else:
            d = self._rename_group_member(None, table, old_name, new_name,
                    None, memberField='subgroupName')
        return d

    @staticmethod
    def _raise_add_exception(failure):
        if isinstance(failure.value, tuple) and len(failure.value) == 2:
            if failure.value[0] == Storage.INVALID_ROW_OR_QUERY:
                raise DirectoryException(failure.value[1],
                        DirectoryException.RECORD_ALREADY_EXISTS)
        raise DirectoryException(failure.value,
                DirectoryException.UNKNOWN_ERROR)

    def _del_creds(self, pinfo, ptype, conn):
        def _del(res, conn, tables_left=None):
            if tables_left is None:
                tables_left = self.cred_to_table.values()[:]
            if len(tables_left) == 0:
                return pinfo
            cred_tbl = tables_left.pop()
            d = cred_tbl.remove_all_rows_for_query(
                    {'name' : pinfo.name, 'principal_type' : ptype},
                    conn=conn)
            d.addCallback(_del, conn, tables_left)
            return d
        d = call_in_txn(self.storage, _del, conn=conn)
        return d

    # --
    # Switches
    # --

    def switches_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_switch(self, switch_info, conn=None):
        def _add(res, conn=None):
            rec = SwitchRecord(switch_info.dpid.as_host(), switch_info.name)
            d = self.switch_tbl.put_record_no_dup(rec, ('name_idx', 'dpid_idx'),
                    conn=conn)
            d.addCallback(_added, conn=conn)
            d.addErrback(self._raise_add_exception)
            return d
        def _added(res, conn):
            si = res.to_SwitchInfo()
            if hasattr(switch_info, 'locations'):
                si.locations = []
                return _add_locs(None, si, conn=conn)
            return si
        def _add_locs(res, new_switch_info, to_add=None, conn=None):
            if res is None:
                to_add = switch_info.locations[:]
            else:
                new_switch_info.locations.append(res)
            if len(to_add) == 0:
                return new_switch_info
            loc = to_add.pop()
            d = self.add_location(loc, conn)
            d.addCallback(_add_locs, new_switch_info, to_add, conn=conn)
            return d
        d = call_in_txn(self.storage, _add, conn=conn)
        return d

    def modify_switch(self, switch_info):
        def _del(res, conn=None):
            d = self.del_switch(switch_info.name, conn=conn, isModify=True)
            d.addCallback(_removed, conn)
            return d
        def _removed(res, conn):
            return self.add_switch(switch_info, conn=conn)
        d = call_in_txn(self.storage, _del)
        return d

    def del_switch(self, switch_name, conn=None, isModify=False):
        def _del_switch(res, conn=None):
            d = self.switch_tbl.remove_all_rows_for_query(
                    {'name' : switch_name}, conn=conn)
            d.addCallback(_switchinfo_from_del_result, conn=conn)
            if not isModify:
                d.addCallback(_del_switch_group_membership, conn=conn)
                d.addCallback(_del_locations, conn=conn)
                d.addCallback(_del_loc_group_membership, conn=conn)
                d.addCallback(self._del_creds, Directory.SWITCH_PRINCIPAL,
                        conn)
            return d
        def _switchinfo_from_del_result(res, conn):
            if len(res) == 0:
                return Failure("No switch named '%s' to delete" %switch_name)
            si = res[0].to_SwitchInfo()
            si.locations = []
            return si
        def _del_locations(si, conn):
            def _locs_removed(loc_recs, si):
                for rec in loc_recs:
                    si.locations.append(rec.to_LocationInfo())
                return si
            d = self.loc_tbl.remove_all_rows_for_query(
                    {'dpid' : si.dpid.as_host()}, conn=conn)
            d.addCallback(_locs_removed, si)
            return d
        def _del_switch_group_membership(si, conn):
            d = self.switchgroup_tbl.remove_all_rows_for_query(
                    {'memberName' : self._ensure_mangled_name(si.name)},
                    conn=conn)
            d.addCallback(lambda res : si)
            return d
        def _del_loc_group_membership(si, conn):
            def _del(res, to_del):
                if len(to_del) == 0:
                    return si
                loc = to_del.pop()
                d = self.locgroup_tbl.remove_all_rows_for_query(
                        {'memberName' : self._ensure_mangled_name(loc)},
                        conn=conn)
                d.addCallback(_del, to_del)
                return d
            return _del(None, [loc.name for loc in si.locations])
        return call_in_txn(self.storage, _del_switch, conn=conn)

    def get_switch(self, switch_name, include_locations=False):
        def _get_switch_cb(res):
            if len(res) == 0:
                return None
            si = res[0].to_SwitchInfo()
            if include_locations:
                si.locations = []
                d = self.loc_tbl.get_all_recs_for_query(
                        {'dpid' : si.dpid.as_host()})
                d.addCallback(_add_locations, si)
                return d
            return si
        def _add_locations(loc_recs, si):
            for rec in loc_recs:
                si.locations.append(rec.to_LocationInfo())
            return si
        d = self.switch_tbl.get_all_recs_for_query({'name' : switch_name})
        d.addCallback(_get_switch_cb)
        return d

    def search_switches(self, query_param):
        qp = query_param.copy()
        self._translate_query_to_db_types(qp)
        return self._search_table(self.switch_tbl, qp)

    # --
    # Locations
    # --

    def locations_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_location(self, loc_info, conn=None):
        def _added(res):
            return res.to_LocationInfo()
        rec = LocRecord(loc_info.dpid.as_host(), loc_info.port, loc_info.name,
                loc_info.port_name, loc_info.speed, loc_info.duplex,
                loc_info.auto_neg, loc_info.neg_down, loc_info.admin_state)
        d = self.loc_tbl.put_record_no_dup(rec, ('name_idx', 'dpid_port_idx'),
                conn=conn)
        d.addCallback(_added)
        d.addErrback(self._raise_add_exception)
        return d

    def modify_location(self, loc_info):
        if loc_info.dpid == None or loc_info.port == None:
            raise DirectoryException("Missing required dpid and/or port in "
                    "modify_location")
        def _del(res, conn=None):
            d = self.del_location(loc_info.name, conn=conn, isModify=True)
            d.addCallback(_removed, conn)
            return d
        def _removed(res, conn):
            return self.add_location(loc_info, conn=conn)

        return call_in_txn(self.storage, _del)

    def del_location(self, loc_name, conn=None, isModify=False):
        def _del_loc(res, conn=None):
            d = self.loc_tbl.remove_all_rows_for_query({'name' : loc_name},
                    conn=conn)
            d.addCallback(_locinfo_from_del_result)
            if not isModify:
                d.addCallback(_del_loc_group_membership, conn=conn)
            return d
        def _locinfo_from_del_result(res):
            if len(res) > 0:
                return res[0].to_LocationInfo()
            else:
                raise DirectoryException("No location named '%s' to delete"
                        %loc_name)
        def _del_loc_group_membership(li, conn):
            d = self.locgroup_tbl.remove_all_rows_for_query(
                    {'memberName' : self._ensure_mangled_name(li.name)},
                    conn=conn)
            d.addCallback(lambda res : li)
            return d
        return call_in_txn(self.storage, _del_loc, conn=conn)

    def get_location(self, loc_name):
        def _get_loc_cb(res):
            if len(res) == 0:
                return None
            return res[0].to_LocationInfo()
        d = self.loc_tbl.get_all_recs_for_query({'name' : loc_name})
        d.addCallback(_get_loc_cb)
        return d

    def search_locations(self, query_param):
        qp = query_param.copy()
        self._translate_query_to_db_types(qp)
        return self._search_table(self.loc_tbl, qp)

    # --
    # Hosts
    # --

    def hosts_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def _validate_hostinfo(self, host_info):
        if host_info.name is None or host_info.name == "":
            return False
        for netinfo in host_info.netinfos:
            if not netinfo.is_valid_static_dir_record():
                return False
        return True

    def add_host(self, host_info, conn=None):
        if not self._validate_hostinfo(host_info):
            raise Exception("Invalid HostInfo provided")
        def _do_add(res, host_info, conn=conn):
            rec = HostAliasRecord(host_info.name, host_info.name,
                    host_info.description)
            d = self.hostalias_tbl.put_record_no_dup(rec, ('alias_idx',),
                    conn=conn)
            d.addCallback(_add_aliases, host_info.aliases, conn, HostInfo())
            return d
        def _add_aliases(res, aliases, conn, infoobj):
            #intentionally build infoobj from results
            infoobj.name = res.name
            infoobj.description = res.description
            if len(aliases) == 0:
                return _add_netinfos(None, host_info, conn, infoobj)
            aliasrecs = []
            for alias in aliases:
                aliasrecs.append(HostAliasRecord(host_info.name, alias, None))
            d = self.hostalias_tbl.put_all_records_no_dup(aliasrecs,
                    ('name_alias_idx',), conn=conn)
            d.addCallback(_add_netinfos, host_info, conn, infoobj)
            return d
        def _add_netinfos(res, host_info, conn, infoobj):
            if res is not None:
                for aliasrec in res:
                    infoobj.aliases.append(aliasrec.alias)
            if len(host_info.netinfos) == 0:
                return _construct_return(None, infoobj)
            nirecs = []
            for ni in host_info.netinfos:
                dpid = None
                dladdr = None
                if ni.dpid is not None:
                    dpid = ni.dpid.as_host()
                if ni.dladdr is not None:
                    dladdr = ni.dladdr.hb_long()
                nirecs.append(HostNetInfoRecord(dpid, ni.port, dladdr,
                                                ni.nwaddr, host_info.name,
                                                ni.is_router,
                                                ni.is_gateway))
            d = self.hostni_tbl.put_all_records_no_dup(nirecs,
                    ('all_idx',), conn=conn)
            d.addCallback(_construct_return, infoobj)
            return d
        def _construct_return(res, infoobj):
            if res is not None:
                for ni in res:
                    infoobj.netinfos.append(ni.to_NetInfo())
            return infoobj
        d = call_in_txn(self.storage, _do_add, host_info, conn=conn)
        d.addErrback(self._raise_add_exception)
        return d

    def modify_host(self, host_info):
        def _del(res, conn=None):
            d = self.del_host(host_info.name, conn=conn, isModify=True)
            d.addCallback(_removed, conn)
            return d
        def _removed(res, conn):
            return self.add_host(host_info, conn=conn)
        d = call_in_txn(self.storage, _del)
        return d

    def del_host(self, host_name, conn=None, isModify=False):
        def _del_host(res, host_name, conn=conn):
            d = self.hostalias_tbl.remove_all_rows_for_query(
                    {'name' : host_name}, conn=conn)
            d.addCallback(_aliases_removed, conn, HostInfo())
            return d
        def _aliases_removed(res, conn, infoobj):
            if len(res) == 0:
                raise DirectoryException("No host named '%s' to delete"
                        %host_name)
            for aliasrec in res:
                if aliasrec.name == aliasrec.alias:
                    #canonical rec
                    infoobj.name = aliasrec.name
                    infoobj.description = aliasrec.description
                else:
                    infoobj.aliases.append(aliasrec.alias)
            d = self.hostni_tbl.remove_all_rows_for_query(
                    {'name' : host_name}, conn=conn)
            d.addCallback(_nis_removed, conn, infoobj)
            return d
        def _nis_removed(res, conn, infoobj):
            for ni in res:
                infoobj.netinfos.append(ni.to_NetInfo())
            if isModify:
                return infoobj
            else:
                d = _del_host_group_membership(None, infoobj, conn=conn)
                d.addCallback(self._del_creds, Directory.HOST_PRINCIPAL, conn)
                return d
        def _del_host_group_membership(res, infoobj, conn, to_purge=None):
            if res is None:
                to_purge = [infoobj.name]
                to_purge.extend(infoobj.aliases or [])
            if len(to_purge) == 0:
                return defer.succeed(infoobj)
            name = to_purge.pop(0)
            d = self.hostgroup_tbl.remove_all_rows_for_query(
                    {'memberName' : self._ensure_mangled_name(name)},
                    conn=conn)
            d.addCallback(_del_host_group_membership, infoobj, conn, to_purge)
            return d
        return call_in_txn(self.storage, _del_host, host_name, conn=conn)

    def get_host(self, host_name):
        def _got_aliases(res):
            infoobj = None
            if len(res) == 0:
                return None
            infoobj=HostInfo()
            for aliasrec in res:
                if aliasrec.name == aliasrec.alias:
                    #canonical rec
                    infoobj.name = aliasrec.name
                    infoobj.description = aliasrec.description
                else:
                    infoobj.aliases.append(aliasrec.alias)
            d = self.hostni_tbl.get_all_recs_for_query({'name' : host_name})
            d.addCallback(_got_netinfos, infoobj)
            return d
        def _got_netinfos(res, infoobj):
            if infoobj is None and len(res):
                infoobj=HostInfo()
            for ni in res:
                infoobj.netinfos.append(ni.to_NetInfo())
            return infoobj
        d = self.hostalias_tbl.get_all_recs_for_query({'name' : host_name})
        d.addCallback(_got_aliases)
        return d

    def search_hosts(self, query_param):
        # valid query params: 
        #     name, description, alias, dladdr, nwaddr, dpid, port
        def _verify_netinfos(names, ni_query):
            d = self._search_table(self.hostni_tbl, ni_query)
            d.addCallback(_name_intersection, names)
            return d
        def _name_intersection(res, names):
            return tuple(set(res).intersection(names))
        qp = query_param.copy()
        alias_query = {}
        for attr in ['name', 'name_glob', 'alias', 'description']:
            if attr in qp:
                alias_query[attr] = qp.pop(attr)
        ni_query = {}
        for attr in ['dladdr', 'nwaddr', 'dpid', 'port', 'is_gateway',
                     'is_router']:
            if attr in qp:
                ni_query[attr] = qp.pop(attr)
        self._translate_query_to_db_types(ni_query)
        if len(qp):
            lg.error("Invalid query parameter(s) in search_hosts")
            raise DirectoryException("Invalid query parameters in search_hosts",
                    DirectoryException.INVALID_QUERY)
        if len(alias_query) == 0 and len(ni_query) == 0:
            #special case returns all records
            return self._search_table(self.hostalias_tbl, alias_query)
        if len(alias_query):
            d = self._search_table(self.hostalias_tbl, alias_query)
            if ni_query:
                d.addCallback(_verify_netinfos, ni_query)
            return d
        else:
            return self._search_table(self.hostni_tbl, ni_query)

    # --
    # Users
    # --

    def users_supported(self):
        return Directory.READ_WRITE_SUPPORT

    def add_user(self, user_info, conn=None):
        def _added(res):
            return res.to_UserInfo()
        rec = UserRecord(user_info.user_id, user_info.name, 
                user_real_name=user_info.user_real_name,
                description=user_info.description,
                location=user_info.location, phone=user_info.phone,
                user_email=user_info.user_email)
        d = self.user_tbl.add_user(rec, conn=conn)
        d.addCallback(_added)
        d.addErrback(self._raise_add_exception)
        return d

    def modify_user(self, user_info):
        def _del(res, conn=None):
            d = self.del_user(user_info.name, conn=conn, isModify=True)
            d.addCallback(_removed, conn)
            return d
        def _removed(res, conn):
            return self.add_user(user_info, conn=conn)
        d = call_in_txn(self.storage, _del)
        return d

    def del_user(self, user_name, conn=None, isModify=False):
        def _del_user(res, conn=None):
            d = self.user_tbl.remove_all_rows_for_query({'name' : user_name},
                    conn=conn)
            d.addCallback(_userinfo_from_del_result)
            if not isModify:
                d.addCallback(_del_user_group_membership, conn=conn)
                d.addCallback(self._del_creds, Directory.USER_PRINCIPAL, conn)
            return d
        def _userinfo_from_del_result(res):
            if len(res) > 0:
                return res[0].to_UserInfo()
            else:
                raise DirectoryException("No user named '%s' to delete"
                        %user_name)
        def _del_user_group_membership(ui, conn):
            d = self.usergroup_tbl.remove_all_rows_for_query(
                    {'memberName' : self._ensure_mangled_name(ui.name)},
                    conn=conn)
            d.addCallback(lambda res : ui)
            return d
        return call_in_txn(self.storage, _del_user, conn=conn)

    def get_user_record(self, name):
        def _get_user_cb(res):
            if len(res) == 0:
                return None
            assert(len(res) == 1, "Name field not unique like it should be")
            return res[0]
        if not self._is_initialized():
            return self._not_initialized_deferred()
        d = self.user_tbl.get_all_recs_for_query({"name":name})
        d.addCallback(_get_user_cb)
        return d

    def get_user(self, user_name):
        def _get_user_cb(res):
            if len(res) == 0:
                return None
            assert(len(res) == 1, "Name field not unique like it should be")
            return res[0].to_UserInfo()
        d = self.user_tbl.get_all_recs_for_query({'name' : user_name})
        d.addCallback(_get_user_cb)
        return d

    def search_users(self, query_param):
        return self._search_table(self.user_tbl, query_param)

    # --
    # Groups
    # --

    @staticmethod
    def _is_addr_group(group_type):
        return group_type == Directory.DLADDR_GROUP or \
               group_type == Directory.NWADDR_GROUP

    @staticmethod
    def _get_member_type(group_type):
        if group_type == Directory.DLADDR_GROUP:
            return ethernetaddr
        elif group_type == Directory.NWADDR_GROUP:
            return cidr_ipaddr
        return str

    def _get_table_for_group(self, group_type):
        if group_type == self.SWITCH_PRINCIPAL_GROUP:
            return self.switchgroup_tbl
        elif group_type == self.LOCATION_PRINCIPAL_GROUP:
            return self.locgroup_tbl
        elif group_type == self.HOST_PRINCIPAL_GROUP:
            return self.hostgroup_tbl
        elif group_type == self.USER_PRINCIPAL_GROUP:
            return self.usergroup_tbl
        elif group_type == self.DLADDR_GROUP:
            return self.dladdrgroup_tbl
        elif group_type == self.NWADDR_GROUP:
            return self.nwaddrgroup_tbl
        else:
            raise NotImplementedError("Group type '%s' not supported"
                    %group_type)

    def _get_parent_groups(self, table, group_name):
        def _get_names_from_recs(recs):
            return [rec.name for rec in recs]
        mangled_gn = self._ensure_mangled_name(group_name)
        d = table.get_all_recs_for_query(
                {'subgroupName' : mangled_gn})
        d.addCallback(_get_names_from_recs)
        return d

    def _del_group(self, group_table, group_name, memberType=str):
        def _del_subgroups(res, conn=None):
            d = group_table.remove_all_rows_for_query(
                    {'subgroupName' : group_name}, conn=conn)
            d.addCallback(_del_main_group, conn)
            return d
        def _del_main_group(res, conn):
            d = group_table.remove_all_rows_for_query( {'name' : group_name},
                    conn=conn)
            d.addCallback(self._get_groupInfo_from_recs, memberType)
            return d
        return call_in_txn(self.storage, _del_subgroups)

    def _get_groupInfo_from_recs(self, recs, memberType=str):
        if len(recs) == 0:
            return None
        ret = GroupInfo()
        for rec in recs:
            if memberType == str:
                name = rec.memberName
                hasName = name != ''
            else:
                if rec.memberAddr != -1:
                    hasName = True
                    if memberType == ethernetaddr:
                        name = create_eaddr(rec.memberAddr)
                    elif memberType == cidr_ipaddr:
                        name = cidr_ipaddr(create_ipaddr(rec.memberAddr),
                                rec.prefixLen)
                    else:
                        raise Exception("Invalid member type")
                else:
                    hasName = False
            if hasName:
                ret.member_names.append(name)
            elif rec.subgroupName:
                ret.subgroup_names.append(rec.subgroupName)
            else:
                ret.name = demangle_name(rec.name)[1]
                if rec.description:
                    ret.description = rec.description
        return ret

    def _get_group_member_recs(self, group_name, member_names,
            subgroup_names, isAddrGrp):
        recs = []
        for member in member_names:
            if isinstance(member, ethernetaddr):
                recs.append(AddressGroupRecord(group_name,
                        member.hb_long(), 48))
            elif isinstance(member, cidr_ipaddr):
                recs.append(AddressGroupRecord(group_name,
                        c_ntohl(member.addr.addr), member.get_prefix_len()))
            elif isinstance(member, basestring):
                if is_mangled_name(member):
                    name = member
                else:
                    name = mangle_name(NOX_DIRECTORY_NAME, member)
                recs.append(GroupRecord(group_name, name))
            else:
                raise DirectoryException("Invalid group member",
                        DirectoryException.OPERATION_NOT_PERMITTED)
        for subgroup in subgroup_names:
            if not is_mangled_name(subgroup):
                subgroup = mangle_name(NOX_DIRECTORY_NAME, subgroup)
            if isAddrGrp:
                rec = AddressGroupRecord(group_name, subgroupName=subgroup)
            else:
                rec = GroupRecord(group_name, subgroupName=subgroup)
            recs.append(rec)
        return recs

    def _get_recs_from_groupInfo(self, groupinfo, isAddrGrp):
        (dm_dir, dm_name) = demangle_name(groupinfo.name)
        recs = self._get_group_member_recs(dm_name,
                groupinfo.member_names, groupinfo.subgroup_names, isAddrGrp)
        if isAddrGrp:
            grpRec = AddressGroupRecord(dm_name,
                    description=groupinfo.description)
        else:
            grpRec = GroupRecord(dm_name, description=groupinfo.description)
        recs.append(grpRec)
        return recs

    def group_supported(self, group_type):
        if group_type in Directory.ALL_GROUP_TYPES:
            return Directory.READ_WRITE_SUPPORT
        return Directory.NO_SUPPORT

    def get_group_membership(self, group_type, member, local_groups=None):
        def _get_groups_cb(res):
            groups = set([rec.name for rec in res])
            if local_groups is not None:
                groups = groups.union(set(local_groups))
            if id is None:
                return tuple([self._get_demangled_local_name(rec)
                        for rec in groups])
            return _get_parentgroups([], groups)

        def _get_parentgroups(res, to_search, results=None):
            results = results or set()
            for rec in res:
                if not rec.name in results:
                    to_search.add(rec.name)
            if len(to_search) > 0:
                groupName = to_search.pop()
                results.add(groupName)
                mangled_group_name = self._ensure_mangled_name(groupName)
                d = group_table.get_all_recs_for_query(
                        {'subgroupName' : mangled_group_name})
                d.addCallback(_get_parentgroups, to_search, results)
                return d
            return tuple([self._get_demangled_local_name(rec)
                    for rec in results])

        group_table = self. _get_table_for_group(group_type)

        if member is None:
            d = group_table.get_all_recs_for_query({})
        else:
            if group_type == Directory.DLADDR_GROUP:
                addr = member.hb_long()
                #TODO search for both oui and full MAC
                d = group_table.get_all_recs_for_query(
                        {'memberAddr' : addr, 'prefixLen' : 48})
            elif group_type == Directory.NWADDR_GROUP:
                addr = c_ntohl(member.addr.addr)
                cidrs = self.cidr_cache.get_groups(member)
                d = defer.succeed(cidrs)
                d.addCallback(lambda res: _get_parentgroups([], res))
                return d
            else:
                if not is_mangled_name(member):
                    member = mangle_name(NOX_DIRECTORY_NAME, member)
                d = group_table.get_all_recs_for_query({'memberName' : member})
        d.addCallback(_get_groups_cb)
        return d

    def search_groups(self, group_type, query_dict):
        if len(set(query_dict.keys()) - set(['name', 'name_glob'])):
            raise DirectoryException("Unsupported query in search_groups")
        group_table = self. _get_table_for_group(group_type)
        qd = query_dict.copy()
        if self._is_addr_group(group_type):
            qd['memberAddr'] = -1
        else:
            qd['memberName'] = ''
        qd['subgroupName'] = ''
        d = self._search_table(group_table, qd)
        return d

    def get_group(self, group_type, group_name, conn=None):
        group_table = self. _get_table_for_group(group_type)
        d = group_table.get_all_recs_for_query({'name' : group_name}, conn=conn)
        d.addCallback(self._get_groupInfo_from_recs,
                memberType=self._get_member_type(group_type))
        return d

    def get_group_parents(self, group_type, group_name):
        group_table = self. _get_table_for_group(group_type)
        mangled_gn = self._ensure_mangled_name(group_name)
        d = group_table.get_all_recs_for_query({'subgroupName' : mangled_gn})
        d.addCallback(lambda recs : [rec.name for rec in recs])
        return d

    def _cache_cidr_recs(self, addr_grp_recs):
        for rec in addr_grp_recs:
            if rec.memberAddr != -1:
                cidr = cidr_ipaddr(create_ipaddr(rec.memberAddr),
                        rec.prefixLen)
                self.cidr_cache.add_cidr(rec.name, cidr)
        return addr_grp_recs

    def _del_cidr_recs(self, addr_grp_recs):
        for rec in addr_grp_recs:
            if rec.memberAddr != -1:
                cidr = create_cidr_ipaddr(create_ipaddr(rec.memberAddr),
                        rec.prefixLen)
                self.cidr_cache.del_cidr(rec.name, cidr)
        return addr_grp_recs

    def add_group(self, group_type, group_info):
        def _translate_storage_err(failure):
            if self._is_storage_failure(failure) \
                    and failure.value[0] == Storage.INVALID_ROW_OR_QUERY:
                return Failure(DirectoryException("Group with same name "
                        "already exists in new directory",
                        DirectoryException.RECORD_ALREADY_EXISTS))
        group_table = self. _get_table_for_group(group_type)
        recs = self._get_recs_from_groupInfo(group_info,
                self._is_addr_group(group_type))
        mtype = self._get_member_type(group_type)
        d = group_table.put_all_records_no_dup(recs,
                ('groupMemberSubgroup_idx',))
        d.addErrback(_translate_storage_err)
        if group_type == Directory.NWADDR_GROUP:
            d.addCallback(self._cache_cidr_recs)
        d.addCallback(self._get_groupInfo_from_recs, memberType=mtype)
        return d

    def modify_group(self, group_type, group_info):
        def _got_group_recs(recs):
            group_rec = None
            if self._is_addr_group(group_type):
                for rec in recs:
                    if rec.memberAddr == -1 and rec.subgroupName == '':
                        group_rec = rec
                        break;
            else:
                for rec in recs:
                    if rec.memberName == '' and rec.subgroupName == '':
                        group_rec = rec
                        break
            if group_rec is None:
                raise DirectoryException("No group with name '%s' exists"
                        %group_info.name, DirectoryException.NONEXISTING_NAME)
            rec.description = group_info.description
            d = group_table.modify_record(rec)
            d.addCallback(lambda x : recs)
            return d

        group_table = self._get_table_for_group(group_type)
        d = group_table.get_all_recs_for_query({'name' : group_info.name})
        d.addCallback(_got_group_recs)
        d.addCallback(self._get_groupInfo_from_recs,
                memberType=self._get_member_type(group_type))
        return d

    def rename_group(self, group_type, old_name, new_name):
        def _ren_group(res, conn):
            def _update_name_cb(rec):
                rec.name = new_name
            d = self._update_records(table, {'name':old_name},
                    {'name':new_name}, _update_name_cb, conn=conn)
            d.addCallback(_ren_subgroups, conn)
            d.addCallback(lambda x : self.get_group(group_type, new_name,
                    conn=conn))
            if group_type == Directory.NWADDR_GROUP:
                d.addCallback(_ren_cidr_cache)
            return d
        def _ren_cidr_cache(res):
            self.cidr_cache.ren_group(old_name, new_name)
            return res
        def _ren_subgroups(res, conn, state='entry', recs=None):
            if state == "entry":
                mangled_sg = self._ensure_mangled_name(old_name)
                q = {'subgroupName' : mangled_sg}
                d = table.get_all_recs_for_query(q, conn=conn)
                d.addCallback(_ren_subgroups, state="got_old_sg",
                        conn=conn, recs=res)
            elif state == "got_old_sg":
                for rec in res:
                    rec.subgroupName=self._ensure_mangled_name(new_name)
                d = table.modify_all_records(res, conn=conn)
                d.addCallback(_ren_subgroups, state="done", conn=conn,
                        recs=recs)
            elif state == "done":
                lg.debug("Updated subgroup record names ('%s' => '%s')"
                        %(old_name, new_name))
                ret = recs
                ret.extend(res)
                return ret
            else:
                raise DirectoryException("Invalide state: '%s'" %state)
            return d

        table = self._get_table_for_group(group_type)
        return call_in_txn(self.storage, _ren_group)

    def del_group(self, group_type, group_name):
        def _del_subgroups(res, conn=None):
            mangled_gn = self._ensure_mangled_name(group_name)
            d = group_table.remove_all_rows_for_query(
                    {'subgroupName' : mangled_gn}, conn=conn)
            if group_type == Directory.NWADDR_GROUP:
                d.addCallback(self._del_cidr_recs)
            d.addCallback(_del_main_group, conn)
            return d
        def _del_main_group(res, conn):
            d = group_table.remove_all_rows_for_query( {'name' : group_name},
                    conn=conn)
            d.addCallback(self._get_groupInfo_from_recs,
                    self._get_member_type(group_type))
            if group_type == Directory.NWADDR_GROUP:
                d.addCallback(_del_cidr_cache)
            return d
        def _del_cidr_cache(res):
            for cidr in res.member_names:
                self.cidr_cache.del_cidr(res.name, cidr)
            return res
        group_table = self. _get_table_for_group(group_type)
        return call_in_txn(self.storage, _del_subgroups)

    def add_group_members(self, group_type, group_name, members=None,
            subgroup_names=None):
        def _get_group_recs_cb(res):
            if len(res) == 0:
                return Failure("Group '%s' does not exist" %group_name)
            recs = self._get_group_member_recs(group_name, members,
                    subgroup_names, self._is_addr_group(group_type))
            d = group_table.put_all_records_no_dup(recs,
                    ('groupMemberSubgroup_idx', ))
            if group_type == Directory.NWADDR_GROUP:
                d.addCallback(self._cache_cidr_recs)
            d.addCallback(_recs_added_cb)
            return d
        def _recs_added_cb(res):
            gi = self._get_groupInfo_from_recs(res,
                    self._get_member_type(group_type))
            return (gi.member_names, gi.subgroup_names)
        #verify group exists
        group_table = self. _get_table_for_group(group_type)
        d = group_table.get_all_recs_for_query({'name' : group_name})
        d.addCallback(_get_group_recs_cb)
        return d

    def del_group_members(self, group_type, group_name, members=None,
            subgroup_names=None):
        def _del_members(res, conn=None, queries=None, results=None):
            if queries is None:
                #entry
                queries = []
                results = ([], [])
                for member in members:
                    if memberType == str:
                        queries.append({'name' : group_name,
                                'memberName' : member, 'subgroupName' : "" })
                    elif memberType == ethernetaddr:
                        queries.append({'name' : group_name,
                                'memberAddr' : member.hb_long(),
                                'prefixLen'    : 48,
                                'subgroupName' : "" })
                    elif memberType == cidr_ipaddr:
                        queries.append({'name' : group_name,
                                'memberAddr' : c_ntohl(member.addr.addr),
                                'prefixLen'    : member.get_prefix_len(),
                                'subgroupName' : "" })
                    else:
                        raise Exception("Invalid member type")
            else:
                #in recursion, handle return from previous delete
                if len(res) == 0:
                    return Failure("Specified member not in group")
                #there should only be one record returned, but handle
                #multiple anyway
                if memberType == str:
                    results[0].extend([rec.memberName for rec in res])
                elif memberType == ethernetaddr:
                    results[0].extend(
                            [create_eaddr(rec.memberAddr) for rec in res])
                else:
                    for rec in res:
                        ip = create_ipaddr(rec.memberAddr)
                        prefixLen = rec.prefixLen
                        cidr = cidr_ipaddr(ip, rec.prefixLen)
                        results[0].append(cidr)
            if len(queries) == 0:
                return _del_subgroups(None, conn, None, results)
            query = queries.pop()
            d = group_table.remove_all_rows_for_query(query, conn)
            d.addCallback(_del_members, conn, queries, results)
            return d
        def _del_subgroups(res, conn, queries, results):
            if queries is None:
                #entry
                queries = []
                for subgroup in subgroup_names or []:
                    if not is_mangled_name(subgroup):
                        subgroup = mangle_name(NOX_DIRECTORY_NAME, subgroup)
                    if memberType == str:
                        queries.append({'name' : group_name, 'memberName' : "", 
                                'subgroupName' : subgroup })
                    else:
                        queries.append({'name' : group_name, 'memberAddr' : -1, 
                                'subgroupName' : subgroup, 'prefixLen' : -1})
            else:
                #in recursion, handle return from previous delete
                if len(res) == 0:
                    raise DirectoryException("Specified subgroup not in group")
                #there should only be one record returned, but handle
                #multiple anyway
                results[1].extend([rec.subgroupName for rec in res])
            if len(queries) == 0:
                if memberType == cidr_ipaddr:
                    for cidr in results[0]:
                        self.cidr_cache.del_cidr(group_name, cidr)
                return results
            query = queries.pop()
            d = group_table.remove_all_rows_for_query(query, conn)
            d.addCallback(_del_subgroups, conn, queries, results)
            return d
        group_table = self. _get_table_for_group(group_type)
        memberType = self._get_member_type(group_type)
        d = call_in_txn(self.storage, _del_members)
        return d

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return NoxDirectory(ctxt)

    return Factory()


