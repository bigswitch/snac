# Manage and expose redhat specific configuration options for:
#
# - network settings 
#    - local IP address
# - DHCP settings (ISC DHCPD)
#    - ??
# - NOX start scripts
#   - Local port
#

import logging

from nox.lib.core import *
from nox.apps.storage import Storage

from nox.ext.apps.local_config.redhat.redhat_net_config import redhat_net_config

lg = logging.getLogger('redhat_config')

class redhat_config:

    def __init__(self, parent):
        self.lg      = lg
        self.storage = parent.storage

        self.net     = redhat_net_config(self)

    def init(self):
        return self.net.init()

    def get_interfaces(self):
        return self.net.interfaces

    def get_hostname(self):
        return self.net.hostname

    def set_interface(self, interface):
        return self.net.set_interface(interface)
