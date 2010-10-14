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

from nox.netapps.authenticator import pyauth
from nox.ext.apps.directory.directorymanager import demangle_name
from nox.ext.apps.directory.simple_directory import simple_directory 
from nox.lib.directory import Directory, GroupInfo

# principal is unauthenticated
#UNAUTHENTICATED = pyauth.Authenticator.get_unauthenticated_name()
# principal is authenticated but more specific name is unknown
#AUTHENTICATED   = pyauth.Authenticator.get_authenticated_name()
# don't know principal's name (for throwing auth events)
#UNKNOWN         = pyauth.Authenticator.get_unknown_name()

#UNMODIFIABLE = [ demangle_name(UNAUTHENTICATED)[1],
#                 demangle_name(AUTHENTICATED)[1],
#                 demangle_name(UNKNOWN)[1] ]

DISCOVERED_DIR_NAME = "discovered"

class discovered_directory(simple_directory):
    GATEWAYS_GROUP_NAME = "gateways"
    SWITCH_MGMT_GROUP_NAME = "switch_management_ports"

    def __init__(self):
        simple_directory.__init__(self)        
        
        #for name in UNMODIFIABLE:
        #    self.restricted_names.add(name)
        self.restricted_names.add(None)
        self.name = DISCOVERED_DIR_NAME
        def fail(result, group_name):
            log.err("Could not create '%s' group." %group_name)
        #the underlying calls are synchronous, so we don't wait on deferred
        d = self.add_group(Directory.HOST_PRINCIPAL_GROUP,
                GroupInfo(self.SWITCH_MGMT_GROUP_NAME,
                "Discovered traffic-sending Openflow switches.", [], []))
        d.addErrback(fail, self.SWITCH_MGMT_GROUP_NAME)
        d = self.add_group(Directory.HOST_PRINCIPAL_GROUP,
                GroupInfo(self.GATEWAYS_GROUP_NAME,
                "Discovered gateways to non-Openflow hosts.", [], []))
        d.addErrback(fail, self.GATEWAYS_GROUP_NAME)
   
    # eventually we want 'discovered' directory 
    # to appear Read-Only to the UI.  But declaring
    # it so means directorymanager won't allow 
    # adds or modifies, so we don't 
#    def switches_supported(self):
#        return Directory.READ_ONLY_SUPPORT
#    def hosts_supported(self):
#        return Directory.READ_ONLY_SUPPORT
#    def users_supported(self):
#        return Directory.READ_ONLY_SUPPORT
#    def locations_supported(self):
#        return Directory.READ_ONLY_SUPPORT
