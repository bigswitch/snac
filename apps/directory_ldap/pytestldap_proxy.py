import code
import os
import re
import time

from nox.ext.apps.directory_ldap import ldap_dir_factory
from nox.ext.apps.directory_ldap import pyldap_proxy
from nox.lib.core import *
from nox.lib.directory import Directory
from nox.coreapps.pyrt.pycomponent import *
from nox.lib import config

class pytestldap_proxy(Component):
    #to work, _configured_dir_id must correspond to the directory
    #config_id of a correctly configured ldap directory
    _configured_dir_id = 2

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.ldap_factory = None
        self.ldapdir = None

    def install(self):
        def _dir_ready(res):
            self.ldapdir = res
            self.register_for_bootstrap_complete(self.bootstrap_complete_cb)
        self.ldap_factory = self.resolve(ldap_dir_factory.ldap_dir_factory)
        if self.ldap_factory is None:
            raise Exception("Unable to resolve component '%s'"
                    %str(ldap_dir_factory.ldap_dir_factory))
        d = self.ldap_factory.get_instance('test',
        self._configured_dir_id)
        d.addCallback(_dir_ready)
        return d

    def getInterface(self):
        return str(pytestldap_proxy)

    def _default_eb(self, failure, callname="unknown"):
        print "'%s' call failed: %s" %(callname, str(failure))

    def bootstrap_complete_cb(self, *args):
        self.try_auth("peter", "goodpw")
        self.try_auth("peter", "badpw")
        self.try_search({'name_glob' : '*pe*'})
        self.try_get("peter")
        self.try_get("abc123")
        self.try_get_group_membership("peter")
        return CONTINUE

    def try_get_group_membership(self, user, count=0):
        d = self.ldapdir.get_group_membership(Directory.USER_PRINCIPAL_GROUP,
                user)
        d.addCallback(self.get_group_membership_cb, user, count)
        d.addErrback(self._default_eb, 'try_get_group_membership')
        return d

    def get_group_membership_cb(self, res, user, count):
        count += 1
        if count % 100 == 1:
            print "Get_group_membership '%s' attempt %d; result: %s" \
                    %(user, count, res)
        self.post_callback(0,
                lambda: self.try_get_group_membership(user, count));

    def try_get(self, user, count=0):
        d = self.ldapdir.get_principal(Directory.USER_PRINCIPAL, user)
        d.addCallback(self.get_cb, user, count)
        d.addErrback(self._default_eb, 'try_get')
        return d

    def get_cb(self, res, user, count):
        count += 1
        if count % 100 == 1:
            if res is not None:
                res = res.to_str_dict()
            print "Get '%s' attempt %d; result: %s" %(user, count, res)
        self.post_callback(0, lambda: self.try_get(user, count));

    def try_search(self, query, count=0):
        d = self.ldapdir.search_principals(Directory.USER_PRINCIPAL, query)
        d.addCallback(self.search_cb, query, count)
        d.addErrback(self._default_eb, 'try_search(%s)' %query)
        return d

    def search_cb(self, res, query, count):
        count += 1
        if count % 100 == 1:
            print "Search '%s' attempt %d; result: %s" %(query, count, res)
        self.post_callback(0, lambda: self.try_search(query, count));

    def try_auth(self, un, pw, count=0):
        #print "calling simple_auth"
        d = self.ldapdir.simple_auth(un, pw)
        d.addCallback(self.simple_auth_cb, un, pw, count)
        d.addErrback(self._default_eb, 'try_auth(%s:%s)' %(un, pw))
        return d

    def simple_auth_cb(self, res, un, pw, count):
        count += 1
        if count % 100 == 1:
            print "Authentication attempt %d; result for '%s': %s" \
                    %(count, res.username, res.status_str())
        #time.sleep(1);
        self.post_callback(0, lambda: self.try_auth(un, pw, count));


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return pytestldap_proxy(ctxt)
    
    return Factory()
