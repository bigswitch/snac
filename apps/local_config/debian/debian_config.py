# Manage and expose debian specific configuration options for:
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
from nox.netapps.storage import Storage

from nox.ext.apps.local_config.debian.deb_net_config import deb_net_config

lg = logging.getLogger('debian_config')

class debian_config:

    def __init__(self, parent):
        self.lg      = lg
        self.storage = parent.storage

        self.net     = deb_net_config(self)

    def init(self):
        return self.net.init()

    def get_interfaces(self):
        return self.net.interfaces

    def get_hostname(self):
        return self.net.hostname

    def set_interface(self, interface):
        return self.net.set_interface(interface)
