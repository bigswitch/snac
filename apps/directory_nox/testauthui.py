import os
import re
import code #XXX for debug

from socket import ntohs

from mako.template import Template
from mako.lookup import TemplateLookup
from twisted.python import log
from twisted.web import server
from twisted.web.resource import Resource
from twisted.web.util import redirectTo

from nox.lib.core import *
from nox.apps.pyrt.pycomponent import *
from nox.lib import config
from nox.lib.netinet.netinet import *

from nox.apps.coreui import coreui
from nox.apps.coreui.authui import User
from nox.apps.coreui.authui import UIResource
from nox.lib.directory import *
from nox.ext.apps.directory_nox import nox_directory
from nox.ext.apps.directory_ldap import pyldap_proxy

class testauthui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None
        self.noxdir = None
        self.ldapauth = None

    def bootstrap_complete_callback(self, *args):
        self.coreui.install_resource("/testauth", TestAuthRes(self))
        return CONTINUE

    def install(self):
        self.coreui = self.resolve(str(coreui.coreui))
        if self.coreui is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(coreui.coreui))
        self.noxdir = self.resolve(nox_directory.NoxDirectory)
        if self.noxdir is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(nox_directory.NoxDirectory))
        self.ldapauth = self.resolve(pyldap_proxy.Ldap_proxy)
        if self.ldapauth is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pyldap_proxy.Ldap_proxy))
        self.register_for_bootstrap_complete(self.bootstrap_complete_callback)

    def getInterface(self):
        return str(testauthui)


class TestAuthRes(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)

    def _pp_valid_user_name(self, pcstr, argd):
        if pcstr is None:
            return ''
        if len(pcstr) == 0 or pcstr.isalnum():
            return pcstr
        else:
            return None

    def _trim_postpath(self, postpath):
        if len(postpath) > 0 and postpath[0] == '':
            return postpath[1:]
        return postpath

    def render_GET(self, request):
        pp = self._trim_postpath(request.postpath)
        print "Request:" + str(pp)
        if len(pp) == 0:
            return self.render_tmpl(request, "test_auth.mako")
        elif pp[0] == 'cdb':
            if len(pp) == 1:
                rows = self.component.noxdir.user_tbl.get_all_recs_for_query({})
                rows.addCallback(self._get_all_users_cb, request)
                return server.NOT_DONE_YET
            elif pp[1] == 'auth':
                return self.render_tmpl(request, "cdb_auth.mako")
            elif pp[1] == 'user':
                if len(pp) != 3:
                    return self.render_tmpl(request, "cdb_user.mako", 
                    user = None)
                username = pp[2]
                rows = self.component.noxdir.user_tbl.get_all_recs_for_query(
                    {'USERNAME' : username})
                rows.addCallback(self._get_user_cb, username, request)
                return server.NOT_DONE_YET
        elif pp[0] == 'ldap':
            pass #fall through

        return self.render_tmpl(request, "invalid_request.mako")

    def _get_all_users_cb(self, res, request):
        request.write(self.render_tmpl(request, "cdb_accounts.mako",
                users = res))
        request.finish()
        
    def _get_user_cb(self, res, username, request):
        request.write(self.render_tmpl(request, "cdb_user.mako",
                username = username, user = res))
        request.finish()

    def render_POST(self, request):
        pp = self._trim_postpath(request.postpath)
        if len(pp) == 0:
            if ( (not request.args.has_key("method")) or
                 (not request.args.has_key("username")) or
                 (not request.args.has_key("password")) ):
                return self.render_tmpl(request, "test_auth.mako", 
                    invalid_param=True)
            method = request.args["method"][0]
            username = request.args["username"][0]
            password = request.args["password"][0]
            if method == 'all':
                return self.render_tmpl(request, "invalid_request.mako")
            elif method == 'cdb':
                d = self.component.noxdir.simple_auth(username, password)
                d.addCallback(self._auth_test_cb, request)
                return server.NOT_DONE_YET
            elif method == 'ldap':
                d = self.component.ldapauth.simple_auth(username, password)
                d.addCallback(self._auth_test_cb, request)
                d.addErrback(self._auth_test_eb, request)
                return server.NOT_DONE_YET
            else:
                return self.render_tmpl(request, "invalid_request.mako")
            #no valid posts to /
            return self.render_tmpl(request, "invalid_request.mako")
        elif pp[0] == 'cdb':
            if len(pp) == 1:
                return self.render_tmpl(request, "invalid_request.mako")
            elif pp[1] == 'auth':
                if ( (not request.args.has_key("username")) or
                     (not request.args.has_key("password")) ):
                    return self.render_tmpl(request, "cdb_auth.mako", 
                        invalid_param=True)
                username = request.args["username"][0]
                password = request.args["password"][0]
                d = self.component.noxdir.simple_auth(username, password)
                d.addCallback(self._cdb_auth_test_cb, request)
                return server.NOT_DONE_YET
            elif pp[1] == 'user':
                req_args = set(('USERNAME', 'USER_REAL_NAME', 'PHONE',
                               'LOCATION', 'PASSWORD_EXPIRE_EPOCH', 'NOX_ROLE',
                               'USER_EMAIL', 'DESCRIPTION', 'PASSWORD'))
                if len(req_args - set(request.args.keys())) > 0:
                    return self.render_tmpl(request, "invalid_request.mako")
                for arg in req_args:
                    if len(request.args[arg][0]) == 0:
                        request.args[arg][0] = None

                args = request.args
                d = self.component.noxdir.create_user(
                        user_id=self.component.noxdir.get_next_uid(),
                        username = args['USERNAME'][0],
                        password = args['PASSWORD'][0],
                        password_expire_epoch = long(args['PASSWORD_EXPIRE_EPOCH'][0]),
                        user_real_name = args['USER_REAL_NAME'][0],
                        description = args['DESCRIPTION'][0],
                        location = args['LOCATION'][0],
                        phone = args['PHONE'][0],
                        user_email = args['USER_EMAIL'][0],
                        nox_role = args['NOX_ROLE'][0])
                d.addCallback(self._create_user_callback, request, 
                        args['USERNAME'][0])
                return server.NOT_DONE_YET
        elif pp[0] == 'ldap':
            pass

        return self.render_tmpl(request, "invalid_request.mako")

    def _create_user_callback(self, res, request, username):
        request.write(self.render_tmpl(request, "cdb_user.mako",
                username = username, user = res))
        request.finish()

    def _auth_test_cb(self, res, request):
        request.write(self.render_tmpl(request, "test_auth.mako",
                is_auth=True, authresult=res.status))
        request.finish()

    def _auth_test_eb(self, failure, request):
        request.write(self.render_tmpl(request, "test_auth.mako",
                failure=failure.value[0]))
        request.finish()

    def _cdb_auth_test_cb(self, res, request):
        request.write(self.render_tmpl(request, "cdb_auth.mako",
                is_auth=True, authresult=res))
        request.finish()



def getFactory():
    class Factory:
        def instance(self, ctxt):
            return testauthui(ctxt)
    
    return Factory()
