# Interface with local configuration state

import logging

import os
import os.path

from twisted.internet import defer

from nox.lib.core import *

from nox.apps.pyrt.pycomponent import pyevent

from nox.apps.storage.storage import Storage
from nox.lib.netinet.netinet import create_ipaddr 

from nox.ext.apps.local_config.interface_change_event import interface_change_event 

lg = logging.getLogger('local_config')

class cfg_interface:

    def __init__(self):
        self.name       = ""
        self.dhcp       = False
        self.encap      = ""
        self.hwaddr     = ""
        self.ip4gw      = ""
        self.ip4dns     = ""
        self.ip4addr    = "0.0.0.0"
        self.ip4mask    = "0.0.0.0"
        self.ip4bcast   = "0.0.0.0"

    def get_dict(self):
        return {
            'name' : self.name,
            'dhcp' : self.dhcp,
            'encap' : self.encap,
            'hwaddr' : self.hwaddr,
            'ip4gw' : self.ip4gw,
            'ip4dns' : self.ip4dns,
            'ip4addr' : self.ip4addr,
            'ip4mask' : self.ip4mask,
            'ip4bcast' : self.ip4bcast,
            }

class local_config(Component):

    # <Public interface>

    def get_hostname(self):
        if not self.cfg:
            lg.error('local_config not enabled')
            return ''
        return self.cfg.get_hostname()

    # Set local interface information.  Performs two actions:
    # - immediately updates the interface information (e.g. using
    #   ifconfig)
    # - updates the local set scripts so configuration is retained
    #   across reboots
    #
    # interface : cfg_interface  
    #
    def set_interface(self, interface):    
        # Do some basic sanity checking of the fields
        ipa = create_ipaddr(interface.ip4addr)
        if not ipa:
            lg.error('invalid IP address '+interface.ip4addr)
            return
        ipa = create_ipaddr(interface.ip4mask)
        if not ipa:
            lg.error('invalid IP mask '+interface.ip4mask)
            return
        ipa = create_ipaddr(interface.ip4bcast)
        if not ipa:
            lg.error('invalid IP mask '+interface.ip4bcast)
            return
        if interface.ip4gw != "":
            ipa = create_ipaddr(interface.ip4gw)
            if not ipa:
                lg.error('invalid IP gw '+interface.ip4gw)
                return
            
        if not self.cfg:
            lg.error('local_config not enabled')
            return False
        try:    
            self.cfg.set_interface(interface) 
            self.post(pyevent(interface_change_event.static_get_name(),
            interface_change_event(interface)))
        except Exception, e:
            lg.error('unable to set interface '+interface.name)

            

    def get_interfaces(self):
        if not self.cfg:
            lg.error('local_config not enabled')
            return None 
        return self.cfg.get_interfaces()    


    # </Public interface>

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.lg = lg
        self.type = 'unknown'

    def determine_local_type(self):
        if os.path.isfile('/etc/debian_version'):
            self.type = 'debian'
        elif os.path.isfile('/etc/redhat-release'):
            self.type = 'redhat'
            
    def configure(self, something):    
        self.register_python_event(interface_change_event.static_get_name())
        self.determine_local_type()

    def install(self):
        self.storage = self.resolve(Storage)
        
        if self.type == 'debian':
            from nox.ext.apps.local_config.debian.debian_config import debian_config
            self.cfg = debian_config(self) 
            return self.cfg.init()
        elif self.type == 'redhat':
            from nox.ext.apps.local_config.redhat.redhat_config import redhat_config
            self.cfg = redhat_config(self) 
            return self.cfg.init()
        else:
            self.cfg = None
            lg.error('unable to determine local system type, disabling local configuration')

    def getInterface(self):
        return str(local_config)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return local_config(ctxt)

    return Factory()
