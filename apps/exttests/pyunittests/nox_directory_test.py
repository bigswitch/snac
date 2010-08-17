#
# Copyright 2008 (C) Nicira, Inc.
#
import logging
from nox.lib.netinet.netinet import *
from nox.netapps.tests import unittest
from nox.netapps.storage import StorageTableUtil
from nox.ext.apps.directory_nox.nox_directory import *
from twisted.internet import defer, reactor

pyunit = __import__('unittest')

lg = logging.getLogger('nox_directory_test')

switch_rec = SwitchInfo()

class NoxDirectoryTestCase(unittest.NoxTestCase):

    def __init__(self, methodName, ctxt):
        unittest.NoxTestCase.__init__(self, methodName, ctxt)
        self.test_complete_deferred = None
        self._init_deferred = None

    def configure(self, configuration):
        pass

    def install(self):
        lg.debug("in install")
        def _install(res):
            lg.debug("nd ready")
            self.nd = res
        self._init_deferred = \
                self.resolve(str(NoxDirectory)).get_instance(None, None)
        self._init_deferred.addCallback(_install)

    def getInterface(self):
        return str(NoxDirectoryTestCase)

    def setUp(self):
        def _wait_before_running(d):
            d.callback(None)

        # dropping table here can cause other components to fail if they
        # try to access nox_directory at bootstrap (as authenticator does)
        # instead, we carefully order everything after a delay
        if self.test_complete_deferred is None:
            self.test_complete_deferred = defer.Deferred()
            d = defer.Deferred()
            reactor.callLater(0.1, _wait_before_running, d)
            self._init_deferred.addCallback(lambda res : d)
            self._init_deferred.addCallback(self._setup_later)
            return self._init_deferred
        self.test_complete_deferred.addCallback(self._setup_later)
        return self.test_complete_deferred

    def _setup_later(self, res):
        lg.debug("getting ready for test")
        d = StorageTableUtil.drop_tables(self.nd.storage, ALL_TABLE_NAMES)
        d.addCallback(self.nd.init_tables)
        return d

    def tearDown(self, res=None):
        lg.debug("in teardown")
        if self.test_complete_deferred != None:
            d = self.test_complete_deferred
            self.test_complete_deferred = None
            d.callback(None)
        return self.test_complete_deferred

    def _err(self, res):
        lg.error("error in test %s" %res)
        import traceback
        traceback.print_exc()
        return res

    def testCredentials(self):
        lg.debug("in testCredentials")
        expected = sorted((Directory.AUTH_SIMPLE,
                Directory.AUTHORIZED_CERT_FP))
        self.failUnless(sorted(self.nd.supported_auth_types()) == expected,
                        "Incorrect supported authentication types")
        self.failUnless(sorted(self.nd.get_enabled_auth_types()) == expected,
                        "Incorrect configured authentication types")
        user = UserInfo('user', 100000)
        pc1 = PasswordCredential('password')
        pc2 = PasswordCredential('password2', password_expire_epoch=123)
        def _cred_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_user(user)
                d.addCallback(_cred_test_state, 'useradded')
                d.addErrback(self._err)
            elif state == 'useradded':
                self.failUnless(res == user, "Incorrect data from add")
                d = self.nd.get_credentials(Directory.USER_PRINCIPAL,
                        'user', Directory.AUTH_SIMPLE)
                d.addCallback(_cred_test_state, 'got_empty_creds')
            elif state == 'got_empty_creds':
                self.failUnless(res == [],
                        "Unexpected return from getting empty credentials")
                d = self.nd.put_credentials(Directory.USER_PRINCIPAL,
                        'user', [pc1], Directory.AUTH_SIMPLE)
                d.addCallback(_cred_test_state, 'put_creds')
            elif state == 'put_creds':
                self.failUnless(len(res) == 1, "Incorrect credential "\
                        "count after put")
                self.failIf(res[0].type != Directory.AUTH_SIMPLE, 
                            "No password credentials after put")
                self.failUnless(res[0].password_expire_epoch == 0,
                        "Incorrect password expire after put")
                d = self.nd.pwcred_tbl.set_password('user',
                        Directory.USER_PRINCIPAL, 'newpw',
                        password_expire_epoch=123)
                d.addCallback(_cred_test_state, 'pw_set')
            elif state == 'pw_set':
                self.failUnless(res.password_expire_epoch == 123,
                        "Invalid data after set password")
                d = self.nd.put_credentials(Directory.USER_PRINCIPAL,
                        'user', [pc2], Directory.AUTH_SIMPLE)
                d.addCallback(_cred_test_state, 'update_creds')
            elif state == 'update_creds':
                self.failUnless(len(res) == 1, "Incorrect credential "\
                        "count after update")
                self.failIf(res[0].type != Directory.AUTH_SIMPLE, \
                    "Wrong type of credentials returned after update")
                self.failUnless(res[0].password_expire_epoch == 123,
                        "Incorrect password expire after update")
                d = self.nd.put_credentials(Directory.USER_PRINCIPAL,
                        'user', [], None)
                d.addCallback(_cred_test_state, 'del_creds')
            elif state == 'del_creds':
                self.failUnless(res == [], "Incorrect data "\
                        "returned from put")
                d = self.nd.get_credentials(Directory.USER_PRINCIPAL,
                        'user', Directory.AUTH_SIMPLE)
                d.addCallback(_cred_test_state, 'got_deleted_creds')
            elif state == 'got_deleted_creds':
                self.failUnless(res == [], 
                        "Unexpected return from getting deleted credentials")
                #TODO: test AUTHORIZED_CERT_FP
                return
            else:
                raise Exception("Invalid state '%s'" %state)
            return d
        return _cred_test_state()

    def testSimpleAuth(self):
        lg.debug("in testSimpeAuth")
        self.failUnless(Directory.AUTH_SIMPLE in 
                self.nd.supported_auth_types(),
                "Incorrect supported authentication types")
        self.failUnless(Directory.AUTH_SIMPLE in 
                self.nd.get_enabled_auth_types(),
                        "Incorrect configured authentication types")
        def _auth_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.simple_auth('admin', 'admin')
                d.addCallback(_auth_test_state, 'admin_auth_success')
                d.addErrback(self._err)
            elif state == 'admin_auth_success':
                self.failUnless(res.status == AuthResult.SUCCESS, 
                        "Failed authentication for default admin user")
                self.failUnless(res.groups == set(['network_admin_superusers']),
                        "Incorrect groups for default admin user")
                self.failUnless(res.nox_roles == set(['Superuser']),
                        "Incorrect NOX roles for default admin user")
                d = self.nd.simple_auth('admin', 'incorrect_pw')
                d.addCallback(_auth_test_state, 'admin_invalid_pw')
            elif state == 'admin_invalid_pw':
                self.failUnless(res.status == AuthResult.INVALID_CREDENTIALS, 
                        "Invalid authentication result with invalid password")
                d = self.nd.simple_auth('admin', 'incorrect_pw')
                d.addCallback(_auth_test_state, 'admin_empty_pw')
            elif state == 'admin_empty_pw':
                self.failUnless(res.status == AuthResult.INVALID_CREDENTIALS, 
                        "Invalid authentication result with empty password")
                #TODO: test expired pw
                return
            else:
                raise Exception("Invalid state")
            return d
        return _auth_test_state()
                
    def testSwitches(self):
        sw_a1 = SwitchInfo('testSwitcha', create_datapathid_from_host(1))
        sw_b1 = SwitchInfo('testSwitchb', create_datapathid_from_host(1))
        sw_a2 = SwitchInfo('testSwitcha', create_datapathid_from_host(2))
        self.failUnless(self.nd.switches_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Switches not fully supported")
        self.failUnless(
                self.nd.principal_enabled(Directory.SWITCH_PRINCIPAL) ==
                Directory.READ_WRITE_SUPPORT,
                "Switch support not fully enabled")
        def _switch_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_switch(sw_a1)
                d.addCallback(_switch_test_state, 'added')
                d.addErrback(self._err)
            elif state == 'added':
                self.failUnless(res == sw_a1, "Incorrect data from add")
                d = self.nd.add_switch(sw_a1)
                d.addCallback(_switch_test_state, 'dup_added')
                d.addErrback(_switch_test_state, 'dup1_failed')
            elif state == 'dup_added':
                self.fail("Adding duplicate did not fail")
            elif state == 'dup1_failed':
                d = self.nd.add_switch(sw_b1)
                d.addCallback(_switch_test_state, 'dup_added')
                d.addErrback(_switch_test_state, 'dup2_failed')
            elif state == 'dup2_failed':
                d = self.nd.add_switch(sw_a2)
                d.addCallback(_switch_test_state, 'dup_added')
                d.addErrback(_switch_test_state, 'dup3_failed')
            elif state == 'dup3_failed':
                d = self.nd.modify_switch(sw_a2)
                d.addCallback(_switch_test_state, 'modified')
            elif state == 'modified':
                self.failUnless(res == sw_a2, "Incorrect data from modify")
                d = self.nd.modify_switch(sw_b1)
                d.addCallback(_switch_test_state, 'nonexistent_modified')
                d.addErrback(_switch_test_state, 'nonexistent_failed')
            elif state == 'nonexistent_modified':
                self.fail("Modifying nonexistent switch did not fail")
            elif state == 'nonexistent_failed':
                d = self.nd.get_switch('testSwitcha')
                d.addCallback(_switch_test_state, 'got_existing')
            elif state == 'got_existing':
                self.failUnless(res == sw_a2, "Incorrect data from get")
                d = self.nd.get_switch('bogusname')
                d.addCallback(_switch_test_state, 'got_nonexistent')
            elif state == 'got_nonexistent':
                self.failUnless(res is None, "Got nonexistent switch")
                d = self.nd.search_switches({'dpid' : sw_a2.dpid})
                d.addCallback(_switch_test_state, 'search1_returned')
            elif state == 'search1_returned':
                self.failUnless(len(res) == 1, "Invalid search result")
                self.failUnless(res[0] == sw_a1.name,
                        "Invalid search result name")
                d = self.nd.search_switches({'dpid' : sw_a1.dpid, 
                                             'name' : sw_a1.name})
                d.addCallback(_switch_test_state, 'search2_returned')
            elif state == 'search2_returned':
                self.failUnless(len(res) == 0, "Invalid search2 result")
                d = self.nd.rename_principal(Directory.SWITCH_PRINCIPAL,
                        'testSwitcha', 'newtestSwitcha')
                d.addCallback(_switch_test_state, 'renamed')
            elif state == 'renamed':
                self.failUnless(res.name == 'newtestSwitcha', 
                        "Invalid record returned after rename")
                d = self.nd.search_switches({'name' : 'testSwitcha'})
                d.addCallback(_switch_test_state, 'search_oldname')
            elif state == 'search_oldname':
                self.failUnless(len(res) == 0, 
                        "Found renamed principal using old name")
                d = self.nd.search_switches({'name' : 'newtestSwitcha'})
                d.addCallback(_switch_test_state, 'search_newname')
            elif state == 'search_newname':
                self.failUnless(len(res) == 1, 
                        "Did not find renamed principal using new name")
                d = self.nd.del_switch('newtestSwitcha')
                d.addCallback(_switch_test_state, 'deleted')
            elif state == 'deleted':
                self.failUnless(res.name == 'newtestSwitcha',
                        "Failed to delete renamed switch")
                d = self.nd.del_switch(sw_a2.name)
                d.addCallback(_switch_test_state, 'delete_dup')
                d.addErrback(_switch_test_state, 'delete_failed')
            elif state == 'delete_dup':
                self.fail("Deleted switch that shouldn't exist")
            elif state == 'delete_failed':
                return
            else:
                raise Exception("Invalid state")
            return d
        return _switch_test_state()

    def testLocations(self):
        lg.debug("in testLocations")
        self.failUnless(self.nd.locations_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Locations not fully supported")
        self.failUnless(
                self.nd.principal_enabled(Directory.LOCATION_PRINCIPAL) ==
                Directory.READ_WRITE_SUPPORT,
                "Location support not fully enabled")
        loc_a11 = LocationInfo('testLoca', create_datapathid_from_host(1), 1)
        loc_b11 = LocationInfo('testLocb', create_datapathid_from_host(1), 1)
        loc_a12 = LocationInfo('testLoca', create_datapathid_from_host(1), 2)
        def _loc_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_location(loc_a11)
                d.addCallback(_loc_test_state, 'added')
            elif state == 'added':
                self.failUnless(res == loc_a11, "Incorrect data from add")
                d = self.nd.add_location(loc_a11)
                d.addCallback(_loc_test_state, 'dup_added')
                d.addErrback(_loc_test_state, 'dup1_failed')
            elif state == 'dup_added':
                self.fail("Adding duplicate did not fail")
            elif state == 'dup1_failed':
                d = self.nd.add_location(loc_b11)
                d.addCallback(_loc_test_state, 'dup_added')
                d.addErrback(_loc_test_state, 'dup2_failed')
            elif state == 'dup2_failed':
                d = self.nd.add_location(loc_a12)
                d.addCallback(_loc_test_state, 'dup_added')
                d.addErrback(_loc_test_state, 'dup3_failed')
            elif state == 'dup3_failed':
                d = self.nd.modify_location(loc_a12)
                d.addCallback(_loc_test_state, 'modified')
            elif state == 'modified':
                self.failUnless(res == loc_a12, "Incorrect data from modify")
                d = self.nd.modify_location(loc_b11)
                d.addCallback(_loc_test_state, 'nonexistent_modified')
                d.addErrback(_loc_test_state, 'nonexistent_failed')
            elif state == 'nonexistent_modified':
                self.fail("Modifying nonexistent location did not fail")
            elif state == 'nonexistent_failed':
                d = self.nd.get_location('testLoca')
                d.addCallback(_loc_test_state, 'got_existing')
            elif state == 'got_existing':
                self.failUnless(res == loc_a12, "Incorrect data from get")
                d = self.nd.get_location('bogusname')
                d.addCallback(_loc_test_state, 'got_nonexistent')
            elif state == 'got_nonexistent':
                self.failUnless(res is None, "Got nonexistent location")
                d = self.nd.search_locations({'dpid' : loc_a12.dpid})
                d.addCallback(_loc_test_state, 'search1_returned')
            elif state == 'search1_returned':
                self.failUnless(len(res) == 1, "Invalid search result")
                self.failUnless(res[0] == loc_a11.name,
                        "Invalid search result name")
                d = self.nd.search_locations({'port' : loc_a11.port, 
                                              'name' : loc_a11.name})
                d.addCallback(_loc_test_state, 'search2_returned')
            elif state == 'search2_returned':
                self.failUnless(len(res) == 0, "Invalid search2 result")
                d = self.nd.rename_principal(Directory.LOCATION_PRINCIPAL,
                        'testLoca', 'newtestLoca')
                d.addCallback(_loc_test_state, 'renamed')
            elif state == 'renamed':
                self.failUnless(res.name == 'newtestLoca', 
                        "Invalid record returned after rename")
                d = self.nd.search_locations({'name' : 'testLoca'})
                d.addCallback(_loc_test_state, 'search_oldname')
            elif state == 'search_oldname':
                self.failUnless(len(res) == 0, 
                        "Found renamed principal using old name")
                d = self.nd.search_locations({'name' : 'newtestLoca'})
                d.addCallback(_loc_test_state, 'search_newname')
            elif state == 'search_newname':
                self.failUnless(len(res) == 1, 
                        "Did not find renamed principal using new name")
                return
            else:
                raise Exception("Invalid state")
            return d
        d =  _loc_test_state()
        d.addErrback(self._err)
        return d
        
    def testHosts(self):
        lg.debug("in testHosts")
        self.failUnless(self.nd.hosts_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Hosts not fully supported")
        self.failUnless(self.nd.principal_enabled(Directory.HOST_PRINCIPAL) ==
                        Directory.READ_WRITE_SUPPORT,
                        "Host support not fully enabled")
        ni1 = NetInfo(create_datapathid_from_host(1), 1, None, None)
        ni2 = NetInfo(None, None, create_eaddr("ca:fe:de:ad:be:ef"), None)
        ni3 = NetInfo(None, None, None, 123)
        host1 = HostInfo('testHost','desc for test host',
                ['testHost_a1', 'testHost_a2'], [ni1, ni2, ni3])
        host2 = HostInfo('testHost','new desc for test host',
                ['testHost_a1'], [ni2, ni1, ni3])
        def _host_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_host(host1)
                d.addCallback(_host_test_state, 'added')
            elif state == 'added':
                self.failUnless(res == host1, "Incorrect data from add")
                dupNameHost = HostInfo('testHost')
                d = self.nd.add_host(dupNameHost)
                d.addCallback(_host_test_state, 'dup_added')
                d.addErrback(_host_test_state, 'dup1_failed')
            elif state == 'dup_added':
                self.fail("Adding duplicate did not fail")
                return Failure("Adding duplicate did not fail")
            elif state == 'dup1_failed':
                dupAliasHost = HostInfo('testHost_a1')
                d = self.nd.add_host(dupAliasHost)
                d.addCallback(_host_test_state, 'dup_added')
                d.addErrback(_host_test_state, 'dup2_failed')
            elif state == 'dup2_failed':
                d = self.nd.modify_host(host2)
                d.addCallback(_host_test_state, 'modified')
            elif state == 'modified':
                self.failUnless(res == host2, "Incorrect data from modify")
                d = self.nd.get_host('testHost')
                d.addCallback(_host_test_state, 'got_existing')
            elif state == 'got_existing':
                self.failUnless(res == host2, "Incorrect data from get")
                d = self.nd.get_host('bogusname')
                d.addCallback(_host_test_state, 'got_nonexistent')
            elif state == 'got_nonexistent':
                self.failUnless(res is None, "Got nonexistent location")
                d = self.nd.search_hosts({'alias' : host2.aliases[0]})
                d.addCallback(_host_test_state, 'search_alias')
            elif state == 'search_alias':
                self.failUnless(len(res) == 1, "Invalid search_alias result")
                self.failUnless(res[0] == host2.name, 
                        "Invalid search result name")
                d = self.nd.search_hosts({'nwaddr' : ni3.nwaddr})
                d.addCallback(_host_test_state, 'search_ni')
            elif state == 'search_ni':
                self.failUnless(len(res) == 1, "Invalid search_ni result")
                self.failUnless(res[0] == host2.name,
                        "Invalid search result name")
                d = self.nd.rename_principal(Directory.HOST_PRINCIPAL,
                        'testHost', 'newtestHost')
                d.addCallback(_host_test_state, 'renamed')
            elif state == 'renamed':
                self.failUnless(res.name == 'newtestHost', 
                        "Invalid record returned after rename")
                d = self.nd.search_hosts({'name' : 'testHost'})
                d.addCallback(_host_test_state, 'search_oldname')
            elif state == 'search_oldname':
                self.failUnless(len(res) == 0, 
                        "Found renamed principal using old name")
                d = self.nd.search_hosts({'name' : 'newtestHost',
                        'alias' : 'newtestHost'})
                d.addCallback(_host_test_state, 'search_newname')
            elif state == 'search_newname':
                self.failUnless(len(res) == 1, 
                        "Did not find renamed principal using new name")
                return
            else:
                raise Exception("Invalid state")
            return d
        d =  _host_test_state()
        d.addErrback(self._err)
        return d

    def testUsers(self):
        lg.debug("in testUsers")
        self.failUnless(self.nd.users_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Users not fully supported")
        self.failUnless(self.nd.principal_enabled(Directory.USER_PRINCIPAL) ==
                        Directory.READ_WRITE_SUPPORT,
                        "User support not fully enabled")
        user1 = UserInfo('user1', 100000, 'user1_real', 'user1_desc',
                'user1_loc', 'user1_phone', 'user1_email')
        user1a = UserInfo('user1', 100000, 'usera1_real', 'user1_desc',
                'user1_loc', 'user1_phone', 'user1_email')
        user2 = UserInfo('user2')
        def _user_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_user(user1)
                d.addCallback(_user_test_state, 'added')
                d.addErrback(self._err)
            elif state == 'added':
                self.failUnless(res == user1, "Incorrect data from add")
                d = self.nd.add_user(user1)
                d.addCallback(_user_test_state, 'dup_added')
                d.addErrback(_user_test_state, 'dup1_failed')
            elif state == 'dup_added':
                self.fail("Adding duplicate did not fail")
            elif state == 'dup1_failed':
                d = self.nd.add_user(user2)
                d.addCallback(_user_test_state, 'u2_added')
            elif state == 'u2_added':
                self.failUnless(res.user_id == 100001, 
                        "Autogenerated UID didn't match expected value")
                d = self.nd.modify_user(user1a)
                d.addCallback(_user_test_state, 'modified')
            elif state == 'modified':
                self.failUnless(res == user1a, "Incorrect data from modify")
                d = self.nd.modify_user(UserInfo('bogususer'))
                d.addCallback(_user_test_state, 'nonexistent_modified')
                d.addErrback(_user_test_state, 'nonexistent_failed')
            elif state == 'nonexistent_modified':
                self.fail("Modifying nonexistent user did not fail")
            elif state == 'nonexistent_failed':
                d = self.nd.get_user('user1')
                d.addCallback(_user_test_state, 'got_existing')
            elif state == 'got_existing':
                self.failUnless(res == user1a, "Incorrect data from get")
                d = self.nd.get_user('bogusname')
                d.addCallback(_user_test_state, 'got_nonexistent')
            elif state == 'got_nonexistent':
                self.failUnless(res is None, "Got nonexistent user")
                d = self.nd.search_users({'location' : 'user1_loc'})
                d.addCallback(_user_test_state, 'search1_returned')
            elif state == 'search1_returned':
                self.failUnless(len(res) == 1, "Invalid search result")
                self.failUnless(res[0] == user1.name,
                        "Invalid search result name")
                d = self.nd.search_users({'location' : 'user1_loc', 
                                          'name' : user2.name})
                d.addCallback(_user_test_state, 'search2_returned')
            elif state == 'search2_returned':
                self.failUnless(len(res) == 0, "Invalid search2 result")
                d = self.nd.del_user(user1.name)
                d.addCallback(_user_test_state, 'deleted')
            elif state == 'deleted':
                self.failUnless(res == user1a)
                d = self.nd.del_user(user1.name)
                d.addCallback(_user_test_state, 'delete_dup')
                d.addErrback(_user_test_state, 'delete_failed')
            elif state == 'delete_dup':
                self.fail("Deleted user that shouldn't exist")
            elif state == 'delete_failed':
                d = self.nd.rename_principal(Directory.USER_PRINCIPAL,
                        'user2', 'newuser2')
                d.addCallback(_user_test_state, 'renamed')
            elif state == 'renamed':
                self.failUnless(res.name == 'newuser2', 
                        "Invalid record returned after rename")
                d = self.nd.search_users({'name' : user2.name})
                d.addCallback(_user_test_state, 'search_oldname')
            elif state == 'search_oldname':
                self.failUnless(len(res) == 0, 
                        "Found renamed principal using old name")
                d = self.nd.search_users({'name' : 'newuser2'})
                d.addCallback(_user_test_state, 'search_newname')
            elif state == 'search_newname':
                self.failUnless(len(res) == 1, 
                        "Did not find renamed principal using new name")
                return
            else:
                raise Exception("Invalid state")
            return d
        return _user_test_state()

    @staticmethod
    def _compare_groups(dirname, g1, g2):
        if g1.name != g2.name:
            return False
        if g1.description != g2.description:
            return False
        def _ensure_mangled(name):
            if isinstance(name, basestring):
                if not is_mangled_name(name):
                    return mangle_name(dirname, name)
            return name
        g1_member_names = [_ensure_mangled(name) for name in g1.member_names]
        g2_member_names = [_ensure_mangled(name) for name in g2.member_names]
        g1_subgroup_names = [_ensure_mangled(name) for name in
                g1.subgroup_names]
        g2_subgroup_names = [_ensure_mangled(name) for name in
                g2.subgroup_names]
        if len(set(g1_member_names) ^ set(g2_member_names)):
            return False
        if len(set(g1_subgroup_names) ^ set(g2_subgroup_names)):
            return False
        return True

    def _testGroups(self, gt):
        self.failUnless(self.nd.group_supported(gt) ==
                        Directory.READ_WRITE_SUPPORT,
                        "Group type '%s' not fully enabled" %gt)
        self.failUnless(self.nd.group_enabled(gt) ==
                        Directory.READ_WRITE_SUPPORT,
                        "Group type '%d' support not fully enabled" %gt)
        gi1 = GroupInfo('group1', 'group1 description',
                ['member1', 'member2', 'ext;extmember1'],
                ['group2', 'ext;extgroup1'])
        gi2 = GroupInfo('group2', 'group2 description',
                ['member1', 'member3', 'member4'])
        gi3 = GroupInfo('group3', 'group3 description',
                ['member1',], ['group1', 'ext;extgroup2'])
        def _group_test_state(res, state='entry', ptype=None):
            if state == 'entry':
                self.failUnless(res == (), "Got nonexistent group")
                d = self.nd.add_group(gt, gi1)
                d.addCallback(_group_test_state, 'gi1_added')
            elif state == 'gi1_added':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME,
                        res,gi1), "Wrong group returned from add 1")
                d = self.nd.add_group(gt, gi2)
                d.addCallback(_group_test_state, 'gi2_added')
            elif state == 'gi2_added':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME,
                        res,gi2), "Wrong group returned from add 2")
                d = self.nd.get_group_membership(gt, 'member1')
                d.addCallback(_group_test_state, 'get_member1')
            elif state == 'get_member1':
                expected = ['group1', 'group2']
                self.failUnless(len(set(res) ^ set(expected)) == 0, 
                        "Wrong groups returned 1")
                d = self.nd.get_group_membership(gt, 'member3')
                d.addCallback(_group_test_state, 'get_member2')
            elif state == 'get_member2':
                expected = ['group1', 'group2']
                self.failUnless(len(set(res) ^ set(expected)) == 0, 
                        "Wrong groups returned 2")
                d = self.nd.add_group(gt, gi3)
                d.addCallback(_group_test_state, 'gi3_added')
            elif state == 'gi3_added':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME,
                        res,gi3), "Wrong group returned from add 3")
                d = self.nd.get_group_membership(gt, 'member3')
                d.addCallback(_group_test_state, 'get_member3')
            elif state == 'get_member3':
                expected = ['group1', 'group2',
                        'group3']
                self.failUnless(len(set(res) ^ set(expected)) == 0,
                        "Wrong groups returned 3")
                d = self.nd.get_group_membership(gt, 'extername',
                        ['ext;extgroup1'])
                d.addCallback(_group_test_state, 'get_ext1')
            elif state == 'get_ext1':
                expected = ['group1', 'group3',
                        'ext;extgroup1']
                self.failUnless(len(set(res) ^ set(expected)) == 0,
                        "Wrong groups returned ext1")
                d = self.nd.add_group_members(gt, 'group3', ['added_user1',
                        'added_user2'], ['added_sg1'])
                d.addCallback(_group_test_state, 'added_members')
            elif state == 'added_members':
                self.failUnless(len(set(res[0]) ^ 
                        set([NOX_DIRECTORY_NAME+';added_user1',
                        NOX_DIRECTORY_NAME+';added_user2'])) == 0,
                        "Wrong return from add_members")
                self.failUnless(res[1] == [NOX_DIRECTORY_NAME+';added_sg1'],
                        "Wrong subgroup return from add_members")
                d = self.nd.get_group(gt, 'group3')
                d.addCallback(_group_test_state, 'get_mod_group')
            elif state == 'get_mod_group':
                self.failUnless(len(set(res.member_names) ^ 
                        set([NOX_DIRECTORY_NAME+';added_user1',
                        NOX_DIRECTORY_NAME+';added_user2', 
                        NOX_DIRECTORY_NAME+';member1'])) == 0,
                        "Wrong member_names after add_members")
                self.failUnless(len(set(res.subgroup_names) ^
                        set([NOX_DIRECTORY_NAME+';added_sg1',
                        'ext;extgroup2', NOX_DIRECTORY_NAME+';group1'])) == 0,
                        "Wrong subgroup_names after add_members")
                d = self.nd.rename_group(gt, 'group2', 'new_group2')
                d.addCallback(_group_test_state, 'renamed_g2')
            elif state == 'renamed_g2':
                self.failIf(res is None, "Group not returned after "
                        "rename_group")
                d = self.nd.get_group(gt, "group2")
                d.addCallback(_group_test_state, 'got_oldname')
            elif state == 'got_oldname':
                self.failUnless(res is None, "Got renamed group using "\
                        "old name")
                d = self.nd.get_group(gt, "new_group2")
                d.addCallback(_group_test_state, 'got_newname')
            elif state == 'got_newname':
                self.failUnless(sorted(res.member_names) ==
                        sorted([mangle_name(NOX_DIRECTORY_NAME, mn) for mn
                                in gi2.member_names]),
                        "Wrong members in renamed group")
                self.failUnless(sorted(res.subgroup_names) ==
                        sorted(gi2.subgroup_names),
                        "Wrong subgroup_names in renamed group")
                self.failUnless(res.description == gi2.description,
                        "Wrong description in renamed group")
                d = self.nd.get_group_parents(gt, "new_group2")
                d.addCallback(_group_test_state, 'got_renamed_parents')
            elif state == 'got_renamed_parents':
                self.failUnless(res == ['group1'], "Incorrect parent "\
                        "groups after rename")
                d = self.nd.rename_group(gt, 'new_group2', 'group2')
                d.addCallback(_group_test_state, 'renamed_g2_back')
            elif state == 'renamed_g2_back':
                d = self.nd.del_group_members(gt, 'group3',
                        [NOX_DIRECTORY_NAME+';added_user1',
                        NOX_DIRECTORY_NAME+';added_user2'],
                        [NOX_DIRECTORY_NAME+';added_sg1'])
                d.addCallback(_group_test_state, 'deleted_members')
            elif state == 'deleted_members':
                self.failUnless(len(set(res[0]) ^ 
                        set([NOX_DIRECTORY_NAME+';added_user1',
                        NOX_DIRECTORY_NAME+';added_user2'])) == 0,
                        "Wrong return from del_members")
                self.failUnless(res[1] == [NOX_DIRECTORY_NAME+';added_sg1'],
                        "Wrong subgroup return from del_members")
                d = self.nd.search_groups(gt, {})
                d.addCallback(_group_test_state, 'got_all_groups')
            elif state == 'got_all_groups':
                expected = ['group1', 'group2', 'group3']
                others = set(res) ^ set(expected)
                role_groups = set([u'network_admin_superusers',
                        #u'NOX_Network_operators',
                        #u'NOX_Policy_administrators',
                        #u'NOX_No_access',
                        #u'NOX_Superusers',
                        #u'NOX_Security_operators'])
                        ])
                self.failUnless(len(others) == 0 or len(others ^
                        role_groups) == 0, "Wrong groups in get_all")
                d = self.nd.search_groups(gt, {'name' : 'group2'})
                d.addCallback(_group_test_state, 'got_specific_groups')
            elif state == 'got_specific_groups':
                self.failUnless(res == ['group2',], "Wrong groups returned "
                        "from search for group2")
                d = self.nd.search_groups(gt, {'name_glob' : 'g*p2'})
                d.addCallback(_group_test_state, 'got_glob1')
            elif state == 'got_glob1':
                self.failUnless(res == ['group2',], "Wrong groups returned "
                        "from glob search for 'g*p2'")
                d = self.nd.search_groups(gt, {'name_glob' : 'gr*'})
                d.addCallback(_group_test_state, 'got_glob2')
            elif state == 'got_glob2':
                expected = sorted(['group1', 'group2', 'group3'])
                self.failUnless(sorted(res) == expected, "Wrong groups "
                        "returned from glob search for 'gr*'")
                d = self.nd.del_group(gt, 'group3')
                d.addCallback(_group_test_state, 'deleted_group3')
            elif state == 'deleted_group3':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        gi3), "Wrong return from delete_group3")
                d = self.nd.get_group_membership(gt, 'member3')
                d.addCallback(_group_test_state, 'get_member4')
            elif state == 'get_member4':
                expected = ['group1', 'group2']
                self.failUnless(len(set(res) ^ set(expected)) == 0, 
                        "Wrong groups returned 4")
                d = self.nd.del_group(gt, 'group2')
                d.addCallback(_group_test_state, 'deleted_group2')
            elif state == 'deleted_group2':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        gi2), "Wrong return from delete_group2")
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_group_test_state, 'get_mod_group2')
            elif state == 'get_mod_group2':
                self.failIf('group2' in res.subgroup_names,
                        "Subgroup membership not removed")
                ptype = \
                        Directory.PRINCIPAL_GROUP_TO_PRINCIPAL.get(gt)
                if ptype is None:
                    return
                d = self.nd.global_principal_renamed(ptype,
                        'ext;extmember1', 'ext;newextmember1')
                d.addCallback(_group_test_state, 'global_p_ren', ptype=ptype)
            elif state == 'global_p_ren':
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_group_test_state, 'get_after_global_p_ren', 
                        ptype=ptype)
            elif state == 'get_after_global_p_ren':
                self.failUnless('ext;newextmember1' in res.member_names,
                        "Member missing after global principal rename")
                self.failIf('ext;extmember1' in res.member_names,
                        "Old member exists after global principal rename")
                d = self.nd.global_group_renamed(gt,
                        'ext;extgroup1', 'ext2;newextgroup1')
                d.addCallback(_group_test_state, 'global_g_ren', ptype=ptype)
            elif state == 'global_g_ren':
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_group_test_state, 'get_after_global_g_ren', 
                        ptype=ptype)
            elif state == 'get_after_global_g_ren':
                self.failUnless('ext2;newextgroup1' in res.subgroup_names,
                        "Subgroup missing after global principal rename")
                self.failIf('ext;extgroup1' in res.subgroup_names,
                        "Old subgroup exists after global principal rename")
                d = self.nd.global_principal_renamed(ptype,
                        'ext;newextmember1', '')
                d.addCallback(_group_test_state, 'global_p_del', 
                        ptype=ptype)
            elif state == 'global_p_del':
                d = self.nd.global_group_renamed(gt,
                        'ext2;newextgroup1', '')
                d.addCallback(_group_test_state, 'global_g_del', 
                        ptype=ptype)
            elif state == 'global_g_del':
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_group_test_state, 'get_after_global_pg_del', 
                        ptype=ptype)
            elif state == 'get_after_global_pg_del':
                self.failIf('ext;newextmember1' in res.member_names,
                        "Member exists after global principal delete")
                self.failIf('ext2;newextgroup1' in res.subgroup_names,
                        "Subgroup exists after global principal delete")
                return
            else:
                raise Exception("Invalid State: '%s'" %state)
            return d
        d = self.nd.get_group_membership(gt, 'group1_m1')
        d.addCallback(_group_test_state)
        d.addErrback(self._err)
        return d

    def testSwitchGroups(self):
        lg.debug("In testSwitchGroups")
        return self._testGroups(Directory.SWITCH_PRINCIPAL_GROUP)

    def testLocationGroups(self):
        lg.debug("In testLocationGroups")
        return self._testGroups(Directory.LOCATION_PRINCIPAL_GROUP)

    def testHostGroups(self):
        lg.debug("In testHostGroups")
        return self._testGroups(Directory.HOST_PRINCIPAL_GROUP)

    def testUserGroups(self):
        lg.debug("In testUserGroups")
        return self._testGroups(Directory.USER_PRINCIPAL_GROUP)

    def testTopologyProperties(self):
        lg.debug("in testTopologyProperties")
        self.failUnless(self.nd.topology_properties_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Topology not fully supported")
        e1 = create_eaddr("ca:fe:de:ad:be:ef")
        e2 = create_eaddr("d0:0d:d0:0d:d0:0d")
        ni1 = NetInfo(None, None, e1, None)
        ni2 = NetInfo(None, None, e2, None, True, True)
        host1 = HostInfo('testHost','test host for topology properties',
                [], [ni1, ni2])
        def _topology_test_state(res=None, state='entry'):
            if state == 'entry': 
                d = self.nd.add_host(host1)
                d.addCallback(_topology_test_state, 'added')
            elif state == 'added':
                self.failUnless(res == host1, "Incorrect data from add")
                d = self.nd.is_gateway(e1)
                d.addCallback(_topology_test_state, 'e1_is_gateway')
            elif state == 'e1_is_gateway':
                self.failUnless(res == False, "e1 shouldn't be a gateway")
                d = self.nd.is_router(e1)
                d.addCallback(_topology_test_state, 'e1_is_router')
            elif state == 'e1_is_router':
                self.failUnless(res == False, "e1 shouldn't be a router")
                d = self.nd.is_gateway(e2)
                d.addCallback(_topology_test_state, 'e2_is_gateway')
            elif state == 'e2_is_gateway':
                self.failUnless(res == True, "e2 should be a gateway")
                d = self.nd.is_router(e2)
                d.addCallback(_topology_test_state, 'e2_is_router')
            elif state == 'e2_is_router':
                self.failUnless(res == True, "e2 should be a router")
                return
            else:
                raise Exception("Invalid state")
            return d
        d =  _topology_test_state()
        d.addErrback(self._err)
        return d

    def testGlobSearch(self):
        lg.debug("in testGlobSearch")
        self.failUnless(self.nd.users_supported() ==
                        Directory.READ_WRITE_SUPPORT,
                        "Users not fully supported")
        user1 = UserInfo('user1a', 100001, 'user1_real', 'user1_desc',
                'user1_loc', 'user1_phone', 'user1_email')
        user2 = UserInfo('user2a', 100002, 'usera2_real', 'user2_desc',
                'user2_loc', 'user2_phone', 'user2_email')
        user3 = UserInfo('user3', 100003, 'usera3_real', 'user3_desc',
                'user3_loc', 'user3_phone', 'user3_email')
        def _glob_test_state(res=None, state='entry'):
            if state == 'entry':
                d = self.nd.add_user(user1)
                d.addCallback(_glob_test_state, 'added1')
                d.addErrback(self._err)
            elif state == 'added1':
                d = self.nd.add_user(user2)
                d.addCallback(_glob_test_state, 'added2')
            elif state == 'added2':
                d = self.nd.add_user(user3)
                d.addCallback(_glob_test_state, 'added3')
            elif state == 'added3':
                d = self.nd.search_users({'name_glob' : 'user*'})
                d.addCallback(_glob_test_state, 'search1_returned')
            elif state == 'search1_returned':
                self.failUnless(len(res) == 3, "Invalid search1 result")
                d = self.nd.search_users({'name_glob' : 'user*a'})
                d.addCallback(_glob_test_state, 'search2_returned')
            elif state == 'search2_returned':
                self.failUnless(len(res) == 2, "Invalid search2 result")
                d = self.nd.search_users({'name_glob' : 'user*a',
                        'user_email' : 'user3_email'})
                d.addCallback(_glob_test_state, 'search3_returned')
            elif state == 'search3_returned':
                self.failUnless(len(res) == 0, "Invalid search3 result")
                d = self.nd.search_users({'name_glob' : 'user*a',
                        'user_email' : 'user2_email'})
                d.addCallback(_glob_test_state, 'search4_returned')
            elif state == 'search4_returned':
                self.failUnless(len(res) == 1, "Invalid search4 result")
                return
            else:
                raise Exception("Invalid state")
            return d
        return _glob_test_state()

    def testDlAddrGroups(self):
        addrs1 = [create_eaddr(i) for i in xrange(0, 3)]
        addrs2 = [create_eaddr(i) for i in [pow(2, 48)- x for x in xrange(1,6)]]
        dgi1 = GroupInfo('group1', 'group1 description',
                addrs1, ['group2', 'ext;extgroup1'])
        dgi2 = GroupInfo('group2', 'group2 description',
                addrs2, ['ext;extgroup2'])
        lg.debug("In testDlAddrGroups")
        gt = Directory.DLADDR_GROUP
        self.failUnless(self.nd.group_supported(gt) ==
                        Directory.READ_WRITE_SUPPORT,
                        "dladdr groups not fully supported")
        def _dladdr_test_state(res, state='entry'):
            lg.debug("---state: %s res: %s" %(state, res))
            if state == 'entry':
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_dladdr_test_state, 'got_empty')
            elif state == 'got_empty':
                self.failUnless(res == (), "Got nonexistent group")
                d = self.nd.add_group(gt, dgi1)
                d.addCallback(_dladdr_test_state, 'added_1')
            elif state == 'added_1':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi1), "Wrong group returned from add 1")
                d = self.nd.add_group(gt,dgi2)
                d.addCallback(_dladdr_test_state, 'added_2')
            elif state == 'added_2':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi2), "Wrong group returned from add 2")
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_dladdr_test_state, 'got_1')
            elif state == 'got_1':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi1), "Wrong group returned from got_1")
                d = self.nd.get_group_parents(gt, dgi2.name)
                d.addCallback(_dladdr_test_state, 'got_parents')
            elif state == 'got_parents':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from got_parents")
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_dladdr_test_state, 'searched_with_2')
            elif state == 'searched_with_2':
                expected = (u'group2', u'group1')
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_with_2")
                d = self.nd.get_group_membership(gt, addrs1[1])
                d.addCallback(_dladdr_test_state, 'searched_for_addr_1')
            elif state == 'searched_for_addr_1':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_for_addr_1")
                d = self.nd.get_group_membership(gt, addrs2[4])
                d.addCallback(_dladdr_test_state, 'searched_for_addr_2')
            elif state == 'searched_for_addr_2':
                #groups include parent groups
                expected = (u'group2', u'group1')
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_for_addr_2")
                d = self.nd.del_group(gt, dgi2.name)
                d.addCallback(_dladdr_test_state, 'deleted_group2')
            elif state == 'deleted_group2':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi2), "Wrong group returned from deleted_group2")
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_dladdr_test_state, 'got_after_del')
            elif state == 'got_after_del':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned after_del")
                d = self.nd.add_group_members(gt, dgi1.name, addrs2, [])
                d.addCallback(_dladdr_test_state, 'added_addrs')
            elif state == 'added_addrs':
                self.failUnless(sorted(res[0]) == sorted(addrs2),
                        "Wrong names returned added_addrs")
                d = self.nd.get_group_membership(gt, addrs2[4])
                d.addCallback(_dladdr_test_state, 'researched_for_addr2')
            elif state == 'researched_for_addr2':
                #groups include parent groups
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from researched_for_addr2")
                d = self.nd.del_group_members(gt, dgi1.name, addrs1, [])
                d.addCallback(_dladdr_test_state, 'deleted_addrs')
            elif state == 'deleted_addrs':
                self.failUnless(sorted(res[0]) == sorted(addrs1),
                        "Wrong names returned deleted_addrs")
                d = self.nd.get_group_membership(gt, addrs1[1])
                d.addCallback(_dladdr_test_state, 'researched_for_addr_1')
            elif state == 'researched_for_addr_1':
                self.failUnless(len(res) == 0,
                        "Wrong groups returned from researched_for_addr_1")
                return
            else:
                raise Exception("Invalid state")
            return d
        d = _dladdr_test_state(None)
        d.addErrback(self._err)
        return d

    def testNwAddrGroups(self):
        addrs1 = [create_cidr_ipaddr(str(create_ipaddr(i)))
                for i in xrange(0, 3)]
        addrs2 = [create_cidr_ipaddr(str(create_ipaddr(i)))
                for i in [ pow(2,32) - x for x in xrange(1,6)]]
        dgi1 = GroupInfo('group1', 'group1 description',
                addrs1, ['group2', 'ext;extgroup1'])
        dgi2 = GroupInfo('group2', 'group2 description',
                addrs2, ['ext;extgroup2'])
        lg.debug("In testNwAddrGroups")
        gt = Directory.NWADDR_GROUP
        self.failUnless(self.nd.group_supported(gt) ==
                        Directory.READ_WRITE_SUPPORT,
                        "nwaddr groups not fully supported")
        def _nwaddr_test_state(res, state='entry'):
            lg.debug("---state: %s res: %s" %(state, res))
            if state == 'entry':
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_nwaddr_test_state, 'got_empty')
            elif state == 'got_empty':
                self.failUnless(res == (), "Got nonexistent group")
                d = self.nd.add_group(gt, dgi1)
                d.addCallback(_nwaddr_test_state, 'added_1')
            elif state == 'added_1':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi1), "Wrong group returned from add 1")
                d = self.nd.add_group(gt, dgi2)
                d.addCallback(_nwaddr_test_state, 'added_2')
            elif state == 'added_2':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi2), "Wrong group returned from add 2")
                d = self.nd.get_group(gt, 'group1')
                d.addCallback(_nwaddr_test_state, 'got_1')
            elif state == 'got_1':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi1), "Wrong group returned from got_1")
                d = self.nd.get_group_parents(gt, dgi2.name)
                d.addCallback(_nwaddr_test_state, 'got_parents')
            elif state == 'got_parents':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from got_parents")
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_nwaddr_test_state, 'searched_with_2')
            elif state == 'searched_with_2':
                expected = (u'group2', u'group1')
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_with_2")
                d = self.nd.get_group_membership(gt, addrs1[1])
                d.addCallback(_nwaddr_test_state, 'searched_for_addr_1')
            elif state == 'searched_for_addr_1':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_for_addr_1")
                d = self.nd.get_group_membership(gt, addrs2[4])
                d.addCallback(_nwaddr_test_state, 'searched_for_addr_2')
            elif state == 'searched_for_addr_2':
                #groups include parent groups
                expected = (u'group2', u'group1')
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from searched_for_addr_2")
                d = self.nd.del_group(gt, dgi2.name)
                d.addCallback(_nwaddr_test_state, 'deleted_group2')
            elif state == 'deleted_group2':
                self.failUnless(self._compare_groups(NOX_DIRECTORY_NAME, res,
                        dgi2), "Wrong group returned from deleted_group2")
                d = self.nd.get_group_membership(gt, None)
                d.addCallback(_nwaddr_test_state, 'got_after_del')
            elif state == 'got_after_del':
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned after_del")
                d = self.nd.add_group_members(gt, dgi1.name, addrs2, [])
                d.addCallback(_nwaddr_test_state, 'added_addrs')
            elif state == 'added_addrs':
                self.failUnless(len(set(res[0]) ^ set(addrs2)) == 0,
                        "Wrong names returned added_addrs")
                d = self.nd.get_group_membership(gt, addrs2[4])
                d.addCallback(_nwaddr_test_state, 'researched_for_addr2')
            elif state == 'researched_for_addr2':
                #groups include parent groups
                expected = (u'group1',)
                self.failUnless(sorted(res) == sorted(expected),
                        "Wrong groups returned from researched_for_addr2")
                d = self.nd.del_group_members(gt, dgi1.name, addrs1, [])
                d.addCallback(_nwaddr_test_state, 'deleted_addrs')
            elif state == 'deleted_addrs':
                self.failUnless(len(set(res[0]) ^ set(addrs1)) == 0,
                        "Wrong names returned deleted_addrs")
                d = self.nd.get_group_membership(gt, addrs1[1])
                d.addCallback(_nwaddr_test_state, 'researched_for_addr_1')
            elif state == 'researched_for_addr_1':
                self.failUnless(len(res) == 0,
                        "Wrong groups returned from researched_for_addr_1")
                return
            else:
                raise Exception("Invalid state")
            return d
        d = _nwaddr_test_state(None)
        d.addErrback(self._err)
        return d

def suite(ctxt):
    suite = pyunit.TestSuite()
    suite.addTest(NoxDirectoryTestCase("testCredentials", ctxt))
    suite.addTest(NoxDirectoryTestCase("testSimpleAuth", ctxt))
    suite.addTest(NoxDirectoryTestCase("testSwitches", ctxt))
    suite.addTest(NoxDirectoryTestCase("testLocations", ctxt))
    suite.addTest(NoxDirectoryTestCase("testHosts", ctxt))
    suite.addTest(NoxDirectoryTestCase("testUsers", ctxt))
    suite.addTest(NoxDirectoryTestCase("testSwitchGroups", ctxt))
    suite.addTest(NoxDirectoryTestCase("testLocationGroups", ctxt))
    suite.addTest(NoxDirectoryTestCase("testHostGroups", ctxt))
    suite.addTest(NoxDirectoryTestCase("testUserGroups", ctxt))
    suite.addTest(NoxDirectoryTestCase("testTopologyProperties", ctxt))
    suite.addTest(NoxDirectoryTestCase("testGlobSearch", ctxt))
    suite.addTest(NoxDirectoryTestCase("testDlAddrGroups", ctxt))
    suite.addTest(NoxDirectoryTestCase("testNwAddrGroups", ctxt))
    return suite
