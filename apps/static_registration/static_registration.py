from nox.lib.core import *
from nox.netapps.tests.pyunittests.storage_test_base import StorageTestBase

from twisted.python import log
from twisted.internet import reactor

class StaticRegistration(Component):
    """
    Interface to the CDB to register 
    MAC->IP->NAME bindings
    AP->NAME bindings
    SWITCH-NAME bindings
    """

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.mac_ip_tname   = "mac_ip_reg"
        self.mac_name_tname = "mac_name_reg"
        self.ip_name_tname  = "ip_name_reg"
        self.ap_name_tname  = "ap_name_reg"
        self.sw_name_tname  = "sw_name_reg"
        
    def configure(self, config):
        pass

    # attempt to create the table if it hasn't already been done so
    def create_tables(self):
        def create_ok(res):
            pass

        def create_err(res):
            log.err('error creating table %s' + str(res),
            system='mac_registration') 

        d = self.storage.create_table(self.mac_ip_tname,
                                   {"MAC" : int, "IP" : int},
                                   (('index_1', ("MAC",)),))
        d.addCallback(create_ok)
        d.addErrback(create_err)
        d = self.storage.create_table(self.mac_name_tname,
                                   {"MAC" : int, "NAME" : str},
                                   (('index_1', ("MAC",)),))
        d.addCallback(create_ok)
        d.addErrback(create_err)
        d = self.storage.create_table(self.ip_name_tname,
                                   {"IP" : int, "NAME" : str},
                                   (('index_1', ("IP",)),))
        d.addCallback(create_ok)
        d.addErrback(create_err)
        d = self.storage.create_table(self.ap_name_tname,
                                   {"AP" : int, "NAME" : str},
                                   (('index_1', ("AP",)),))
        d.addCallback(create_ok)
        d.addErrback(create_err)
        d = self.storage.create_table(self.sw_name_tname,
                                   {"SWITCH" : int, "NAME" : str},
                                   (('index_1', ("SWITCH",)),))
        d.addCallback(create_ok)
        d.addErrback(create_err)


    def install(self):
        # FIXME: There doesn't seem to be a persistent_storage file anymore
        # so I'm not sure what this is supposed to use instead. Probably
        # transactional_storage? Is this code even supported anymore?
        from nox.netapps.storage.persistent_storage import PersistentStorage
        self.storage = self.ctxt.resolve(str(PersistentStorage))
        self.create_tables()

        
    def getInterface(self):
        return str(StaticRegistration)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return StaticRegistration(ctxt)

    return Factory()
