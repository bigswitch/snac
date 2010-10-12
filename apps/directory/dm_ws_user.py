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
from time import time

from twisted.internet import defer
from twisted.python.failure import Failure
from nox.apps.coreui      import webservice
from nox.apps.coreui.webservice import *
from nox.apps.directory.query import query
from nox.apps.directory.directorymanagerws import *
from nox.apps.directory.directorymanager import mangle_name
from nox.lib.directory import Directory, DirectoryException

lg = logging.getLogger('dm_ws_user')

class dm_ws_user:
    """Exposes user state that does not correspond
    directly to a call in the standard directory interface"""

    def __init__(self, dm, bindings_dir, reg):
        self.dm = dm
        self.bstore = bindings_dir.get_bstore()

        ss = webservice.WSPathStaticString
        dirname       = WSPathExistingDirName(dm, "<dir name>");
        principalname = WSPathArbitraryString("<principal name>")

        # WSPathArbitraryString must use '<principal name>' in order to
        # play nicely with the URLs created by the directory manager
        userpath = ( ss("user"), dirname, principalname )

        # GET /ws.v1/<Principal type>/<dir name>/<principal name>/cred
        reg(self.do_get_creds, "GET", userpath + (ss("cred"),),
                "Set credentials on a principal.")

        # PUT /ws.v1/<Principal type>/<dir name>/<principal name>/cred
        reg(self.do_set_creds, "PUT", userpath + (ss("cred"),),
                "Set credentials on a principal.")

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def do_get_creds(self, request, arg):
        try:
            def _ok(res):
                ret = {}
                for cred in res:
                    ret[cred.type] = cred.to_str_dict()
                request.write(simplejson.dumps(ret))
                request.finish()

            user_name = arg["<principal name>"]
            dir_name  = arg["<dir name>"]
           
            d = self.dm.get_credentials(Directory.USER_PRINCIPAL, user_name,
                                        dir_name=dir_name)
            d.addCallback(_ok)
            d.addErrback(self.err, request, "do_get_creds",
                         "Could not retrieve credential information.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "do_get_creds",
                            "Could not retrieve credential information.")

    def do_set_creds(self, request, arg):
        try:
            def _ok(res):
                ret = {Directory.AUTH_SIMPLE : []}
                if len(res):
                    ret[Directory.AUTH_SIMPLE].append(res[0].to_str_dict())
                request.write(simplejson.dumps(ret))
                request.finish()

            user_name = arg["<principal name>"]
            dir_name  = arg["<dir name>"]
           
            content = json_parse_message_body(request)
            if content == None: 
                return webservice.badRequest(request, "Unable to parse message body.")

            pwcreds = []
            enabled_auth_types = self.dm.get_directory_instance(dir_name)._instance.get_enabled_auth_types()
            for credtype, credlist in content.items():
                if not isinstance(credlist, list):
                    return webservice.badRequest(request,
                                                 "Credentials must be a list")
                if credtype not in enabled_auth_types or credtype != Directory.AUTH_SIMPLE:
                    return webservice.badRequest(request,
                                                 "Unsupported credential type '%s'" %credtype)

                if len(credlist) > 1:
                    return webservice.badRequest(request,
                                                 "Only one "+Directory.AUTH_SIMPLE
                                                 + " credential may be supplied")
                for pwdict in credlist:
                    pwcred = PasswordCredential.from_str_dict(pwdict)
                    if pwcred.password is None:
                        return webservice.badRequest(request,
                                                     "Invalid "+Directory.AUTH_SIMPLE
                                                     + " credential supplied")
                    pwcreds.append(pwcred)
            d = self.dm.put_credentials(Directory.USER_PRINCIPAL, user_name,
                                        pwcreds, dir_name=dir_name)
            d.addCallback(_ok)
            d.addErrback(self.err, request, "do_set_creds",
                         "Could not set credential information.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "do_set_creds",
                            "Could not set credential information.")
