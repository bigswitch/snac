#
# Copyright 2008 (C) Nicira, Inc.
#
from twisted.internet import defer
from twisted.python.failure import Failure
import logging
import code

from nox.lib.core import Component
from nox.lib.directory import *
from nox.lib.directory_factory import Directory_Factory

from nox.netapps.directory.directorymanager import directorymanager
from nox.ext.apps.directory_ldap.pyldap_proxy import pyldap_proxy

lg = logging.getLogger('ldap_dir_factory')

class ldap_dir_factory(Component, Directory_Factory):
    """
    Factory component to produce ldap directory instances
    """
    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.directorymanager = None
        self.instances = {}

    def getInterface(self):
        return str(ldap_dir_factory)

    def install(self):
        self.directorymanager = self.resolve(directorymanager)
        d = self.directorymanager.register_directory_component(self)
        return d

    def get_type(self):
        return "LDAP"

    def get_default_config(self):
        return pyldap_proxy.get_default_config()

    def get_instance(self, name, config_id):
        def _dir_ready(res):
            self.instances[config_id] = dinst
            return dinst
        if config_id in self.instances:
            return defer.succeed(self.instances[config_id])
        dinst = pyldap_proxy(name.encode('utf-8'), config_id)
        d = dinst.initialize(self.ctxt)
        if d is None:
            defer.fail("Failed to get new pyldap_proxy instance");
        d.addCallback(_dir_ready)
        return d

    def supports_multiple_instances(self):
        return True

    def supported_auth_types(self):
        return (Directory_Factory.AUTH_SIMPLE,)

    def principal_supported(self, principal_type):
        if principal_type == Directory.USER_PRINCIPAL:
          return Directory.READ_ONLY_SUPPORT
        return Directory.NO_SUPPORT

    def group_supported(self, group_type):
        if group_type == Directory.USER_PRINCIPAL_GROUP:
          return Directory.READ_ONLY_SUPPORT
        return Directory.NO_SUPPORT


def getFactory():
        class Factory():
            def instance(self, context):
                return ldap_dir_factory(context)

        return Factory()
