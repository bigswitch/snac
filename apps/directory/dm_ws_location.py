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
#

import logging
import simplejson

from twisted.internet import defer
from twisted.python.failure import Failure
from nox.apps.coreui      import webservice
from nox.apps.coreui.webservice import *
from nox.apps.directory.query import query
from nox.apps.directory.directorymanagerws import *
from nox.apps.directory.directorymanager import mangle_name
from nox.lib.directory import Directory, DirectoryException

lg = logging.getLogger('dm_ws_location')

class dm_ws_location:
    """Exposes location state that does not correspond
    directly to a call in the standard directory interface"""

    def __init__(self, dm, bindings_dir):
        self.dm = dm
        self.bstore = bindings_dir.get_bstore()

    def register_webservices(self, reg): 
        ss = webservice.WSPathStaticString
        dirname       = WSPathExistingDirName(self.dm, "<dir name>");
        principalname = WSPathArbitraryString("<principal name>")

        # WSPathArbitraryString must use '<principal name>' in order to
        # play nicely with the URLs created by the directory manager
        switchpath = ( ss("location"), dirname, principalname )

        # GET /ws.v1/location/<dir name>/<location name>/config
        reg(self.get_config_ws, "GET", switchpath + (ss("config"),),
            """Return location configuration information""")

        # GET /ws.v1/location/<dir name>/<location name>/active
        #reg(lambda x,y: self.start(x,y,None),
        #    "GET", switchpath + (ss("active"),),
        #    """Boolean indicator of whether a location is currently active""")
    
    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)


    def get_config_ws(self,request,arg): 
        try : 
            location_name = arg["<principal name>"] 
            dir_name      = arg["<dir name>"] 
            mangled_name = mangle_name(dir_name,location_name) 

            def write_to_ws(res): 
              request.write(simplejson.dumps(res))
              request.finish()
            
            d = self.start(mangled_name)
            d.addCallback(write_to_ws)
            d.addErrback(self.err, request, "start", "Could not retrieve location information.") 
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "start", "Could not retrieve location information.")
        
    def start(self, mangled_name): 
        d = self.dm.get_principal(Directory.LOCATION_PRINCIPAL,mangled_name)
        d.addCallback(self.start2, mangled_name) 
        return d

    # this method continues the chain from start(), grabs the results
    # from the directory lookup, and then dispatches the specific
    # webservice handler
    def start2(self, location_info, mangled_name):
        if location_info is None:
            defer.fail("Location '%s' does not exist." % mangled_name)

        if location_info.dpid is None:
            d = defer.Deferred()
            d.addCallback(self.start3, [], location_info)
            return d

        # resolve switch name    
        query = {'dpid' : location_info.dpid}
        d = self.dm.search_principals(Directory.SWITCH_PRINCIPAL, query)
        d.addCallback(self.start3, location_info)
        return d

    # By this point, should have resolve switch name ... 
    def start3(self, switch_names, location_info):
        loc_dir = location_info.to_str_dict()
        if len(switch_names) < 1:
            loc_dir['switch_name'] = None
        else:
            loc_dir['switch_name'] = switch_names[0]
        return loc_dir
