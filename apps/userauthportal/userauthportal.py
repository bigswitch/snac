# Copyright 2008 (C) Nicira, Inc.
#
"""User authentication captive portal component

==== Overview ====

This component implements a means for establishing and maintaining a user to
network location binding in NOX via a web browser.  Users are redirected
to the portal by the http_redirector component, whose operation is governed
by the sepl policy.

A web page (preferablly a popup) keeps the session alive, and provides the
user with a means to remove the binding (logout).


==== Assumptions ====

When a user has multiple browser tabs/windows redirected to the portal,
authentication on one page should be sufficient for all of them.  To
facilitate this, we assume that ANY user binding for a location
indicates all requests at that location are authenticated.  This
assumption does not hold on a multi-user hosts where users have different
access policies.

Proper operation of this component depends on the proper configuration
of the policy (sepl) and http_redirector components:

  Policy:
    Hosts with or without user bindings must be granted access to the host
    and port where the authentication portal is running.  Basic network
    services such as ARP, DNS, DHCP, and potentially others must also be
    (at least partially) allowed in most cases.

    HTTP flows (currently only TCP port 80 is supported) from hosts without
    user bindings should be configured to take the 'http_redirect'
    function action to activate the http_redirector component.

    HTTP flows with active user bindings MUST be configured to *NOT*
    take the 'http_redirect' function action, as this will result in a
    browser redirect loop.

  Http_redirector :
    The http_redirector must be configured with the correct URL of the
    authentication portal.


==== Web Browser Compatibility ====

The captive portal component is meant to be compatible with all modern
web browsers (and some ancient ones too.)  While CSS, DOM,  Javascript and
popup window support are strongly suggested, the core operation of the
portal should function in their absence.


==== Component Operation ====

The userauthportal authentication process requires the cooperation of
other components, as described in the Assumptions section above.

Bootstrap operation (outside of userauthportal):

1.  User opens web browser on host that currently does not have a user
    binding.  The web browser makes a web request to an URL that is
    restricted to hosts with user bindings.

2.  Flow associated to the web request is passed from the openflow switch
    to the policy engine.

3.  Policy engine routes the flow to the http_redirector component.

4.  Http_redirector caches the flow information and HTTP request payload sent
    by the host.  It then redirects the client browser to the URL of the
    userauthportal, including an argument with a key to the cached flow
    information.

5.  Following the redirect, the client browser issues a request to the
    userauthportal, including http_redirector cached flow key argument.

Userauthportal operation:

6.  A client session key is automagically created by the twisted web
    server and passed along with each request.  The session key uniquely
    identifies a web client application, but not a specific tab/window.

7.  A query comes to the 'auth' URL.
    - The flow information associated with the request is queried from the
      http_redirector, and is parsed into a new _Flowinfo instance, which is
      associated (cached) with the session.

    - render auth_login.mako template:
      - A page consisting of a banner, disclaimer, and username/password form
        is displayed.  The form also contains hidden input fields specifying
        the flow information and original URL requested by this browser
        tab/window.

    - If the browser supports DOM, Javascript and the XMLHttpRequest
      method, a timer is launched which polls the 'check_for_auth'
      URL for user authentication.
      - If the user has been authenticated, the page is replaced with the
        authentication success page (14.)

8.  When the user clicks submit on the login form:
    - If javascript is enabled:
      - A javascript method attempts to open a popup window to the
        'opening_pu' url. (We open here to avoid being blocked by popup
        blockers if possible.)

      - If the popup window was successful:
        - The form inputs are annotated to indicate a popup was successful
        - The form target is redirected to the popup window
        - The parent window is redirected to the 'wait_for_pu' URL
        - The form is submitted to the 'do_login' URL

      - Else (no popup window):
        - The form is submitted as normal to the 'do_login' URL

    - Else (no javascript):
      - The form is submitted as normal to the 'do_login' URL

9a. A query may come to the 'opening_pu' url.  The popup may be about to
    submit a form, or may never in some edge cases.
    - If popup was first opened too long ago:
      - Render auth_error.mako
    - Else:
      - render auth_in_progress.mako template with opening_pu argument
        - will refresh to 'opening_pu' url in 1 sec

9b. A form submit comes to the 'do_login' URL.
    - The flow information associated with the page is parsed from the form
      fields.
    - A simple_auth request is made to the directory manager
    - render in_progress.mako template with 'do_login' argument
      - will refresh to 'do_login' in 1 sec

9c. A query may come to the 'wait_for_pu' URL.
    - If we started waiting for popup too long ago
      - Render auth_error.mako
    - check auth status XXX how?
    - XXX additional checks/timers for form submit?
    - render in_progress.mako template with 'wait_for_pu' argument

10. A form submit comes to the 'auth_status' URL.
    - render auth_logout.mako template:
      - A page consisting of a banner, message, and logout button is displayed.
      - If not is_popup:
        - Message indicating that popup failed and current page must
          remain open
        - Add link to retry popup
        - If we could parse the URL from the original query, add link to
          open the original destination URL in new window
      - Page refreshes and keeps session alive
        XXX - fill in the rest of this

11. A form submit comes to the 'do_logout' URL.
    - The form parameters are validated
    - A DEAUTHENTICATE event is sent to the authenticator component
    - render auth_logout.mako template:
      - A 'logged out' message is displayed
      - If have javascript: a button to close the window is provided

12. A form submit comes to the 'success' URL.
    - render auth_success.mako template:
      - A page consisting of a banner and success message is displayed.
      - If we could parse the URL from the original query for this window:
        - Page includes very short refresh to original URL
        - Page includes links to the original URL in case redirect fails
      - Else (no URL to redirect to):
        - Page includes message for user to reissue their query


Notes:
A.  If an unsupported URL is provided by the browser, a generic error
    page is displayed.

B.  If network flow information associated with a request cannot be retrieved
    or fails to validate, a generic error page is displayed.

"""
import array
import code #XXX debug
import logging
import md5
import re
import time

from random import SystemRandom
from socket import ntohs

from twisted.internet import defer
from twisted.web import server
from twisted.web.util import redirectTo

from nox.lib.core import *
from nox.lib.directory import *
from nox.lib.netinet.netinet import *

from nox.apps.authenticator.pyauth import Auth_event, Authenticator
from nox.apps.authenticator.pyauth import PyAuth
from nox.apps.bindings_storage import pybindings_storage
from nox.apps.bindings_storage.pybindings_storage import Name
from nox.apps.coreui import coreui
from nox.apps.coreui.authui import UIResource
from nox.apps.directory import directorymanager
from nox.apps.pyrt.pycomponent import *
from nox.apps.user_event_log.pyuser_event_log import pyuser_event_log, LogEntry
from nox.ext.apps.http_redirector.pyhttp_redirector import *

lg = logging.getLogger('userauthportal')

DEV_VERBOSE   = True # XXX this should never be True in production
DEV_FAKE_FLOW = True # XXX dev - remove for production

COMPONENT_ID  = "userauthportal"
UNKNOWN_HNAME = Authenticator.get_unknown_name()
IMAGE_BUG_GIF = array.array('B', [0x47,0x49, 0x46,0x38, 0x39,0x61, 0x01,0x00,
                                  0x01,0x00, 0x80,0x00, 0x00,0xFF, 0xFF,0xFF,
                                  0x00,0x00, 0x00,0x21, 0xf9,0x04, 0x01,0x00,
                                  0x00,0x00, 0x00,0x2c, 0x00,0x00, 0x00,0x00,
                                  0x01,0x00, 0x01,0x00, 0x00,0x02, 0x02,0x44,
                                  0x01,0x00, 0x3b]).tostring()
RANDOM = SystemRandom()
HASH_COOKIE_BITS = 128
HASH_COOKIE_LIFETIME_SEC = 60*60*24
OPENING_PU_MAX_TM = 10
WAIT_FOR_PU_MAX_TM = 15

#
# TODO:
# - Have logout page refresh form cookie every n seconds
#   - should meta refresh if XMLHttpRequest isn't available
#
# - See if we can get login pu to display in progress message
#
# - Add nonce to prevent replay attacks
#
# - encode redirect urls and verify they are safe before rendering
#
# - time out in-progress requests

class uapConfig:

    def __init__(self):
        #TODO: get this from CDB
        imagebase = "/static/nox/ext/apps/userauthportal/"
        #self.logo_lg = None # Dim 600 X 115+/-
        self.logo_lg = imagebase + "nicira_banner_sm.jpg"
        #self.logo_sm = None # Dim 294 X 58
        self.logo_sm = imagebase + "nicira_banner_tiny.jpg"
        self.org_name = "Nicira Networks"
        self.message = \
                "<table width='95%'><tr><td>"\
                "A really long disclaimer message, or anything that the "\
                "company wants (configurable in CDB) can go here.  This "\
                "message is just to show what it will look like where "\
                "there is a block of text."\
                "</td></tr><tr><td>\n"\
                "The user acknowledges that the current pages are a work "\
                "in progress, and although feedback is appreciated, it may "\
                "not get immediately implemented.  Thanks for reading "\
                "my big block of text."\
                "</td></tr></table>"
        self.message = ""
        self.css = ""
        self.log_invalid_username = False
        self.auth_check_interval_ms = 4000


class userauthportal(Component):
    _web_resource_root = "/auth"

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.auth   = None
        self.bs     = None
        self.coreui = None
        self.dm     = None
        self.hr     = None
        self.uel    = None
        self.config = uapConfig()
        self.old_hashcookie = RANDOM.getrandbits(HASH_COOKIE_BITS)
        self.cur_hashcookie = RANDOM.getrandbits(HASH_COOKIE_BITS)

    def bootstrap_complete_callback(self, *args):
        self.coreui.install_resource(self._web_resource_root,
                AuthRes(self, self._web_resource_root))
        return CONTINUE

    def install(self):
        self.auth = self.resolve(str(PyAuth))
        if self.auth is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(PyAuth))
        self.bs = self.resolve(str(pybindings_storage.pybindings_storage))
        if self.bs is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pybindings_storage.py_bindings_storage))
        self.coreui = self.resolve(coreui.coreui)
        if self.coreui is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(coreui.coreui))
        self.dm = self.resolve(directorymanager.directorymanager)
        if self.coreui is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(coreui.coreui))
        self.hr = self.resolve(pyhttp_redirector)
        if self.hr is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pyhttp_redirector))
        self.uel = self.resolve(pyuser_event_log)
        if self.uel is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pyuser_event_log))
        self.register_for_bootstrap_complete(self.bootstrap_complete_callback)
        self._rotate_hashcookie()

    def _rotate_hashcookie(self):
        #lg.debug("rotating hashes")
        self.old_hashcookie = self.cur_hashcookie
        self.cur_hashcookie = RANDOM.getrandbits(HASH_COOKIE_BITS)
        self.post_callback(HASH_COOKIE_LIFETIME_SEC, self._rotate_hashcookie)

    def getInterface(self):
        return str(userauthportal)


class AuthRes(UIResource):
    isLeaf = True
    noUser = True

    class web_resources:
        def __init__(self, res_root):
            self.auth           = res_root
            self.check_for_auth = res_root + "/check"
            self.opening_pu     = res_root + "/pu"
            self.wait_for_pu    = res_root + "/wfpu"
            self.auth_status    = res_root + "/ses"
            self.do_login       = res_root + "/do_li"
            self.do_logout      = res_root + "/do_lo"
            self.success        = res_root + "/success"
            self.error        = res_root + "/error"

    def __init__(self, component, res_root):
        UIResource.__init__(self, component)
        self.component = component
        self.res_paths = self.web_resources(res_root)
        self.resource_handlers = {
            self.res_paths.auth           : self.handle_auth,
            self.res_paths.check_for_auth : self.handle_check_for_auth,
            self.res_paths.opening_pu     : self.handle_opening_pu,
            self.res_paths.wait_for_pu    : self.handle_wait_for_pu,
            self.res_paths.auth_status    : self.handle_auth_status,
            self.res_paths.do_login       : self.handle_do_login,
            self.res_paths.do_logout      : self.handle_do_logout,
            self.res_paths.success        : self.handle_success,
            self.res_paths.error          : self.handle_error
        }

    def render_tmpl(self, request, name, *arg, **data):
        """Render mako template with componet config and resource paths"""
        return UIResource.render_tmpl(self, request, name,
                c=self.component.config, r=self.res_paths, *arg, **data)

    def render_GET(self, request):
        return self.render_POST(request)

    def render_POST(self, request):
        try:
            if request.path[-1] == '/':
                request.path = request.path[:-1]
            handler = self.resource_handlers.get(request.path)
            if handler is not None:
                return handler(request)
            else:
                lg.err("Invalid %s URL: '%s'"%(request.method,
                        str(request.path)))
                return self._render_error(request,
                        msg="Invalid %s URL"%request.method)
        except Exception, e:
            lg.error("Exception while processing %s request for '%s': %s"\
                    %(request.method, str(request.path), e.message))
            return self._render_error(request,
                    msg="Exception has occurred: %s"%e)

    def _render_error(self, request, close_if_pu=True, msg=None):
        rendered_msg = None
        if DEV_VERBOSE:
            rendered_msg = msg
        return self.render_tmpl(request, "auth_error.mako",
                                msg=rendered_msg, close_if_pu=close_if_pu)

    def handle_auth(self, request):
        """Cache flow information and display a login page"""
        #TODO: we could check for authentication here
        # _get_associated_flow also caches the flow with session
        fi = self._get_associated_flow(request)
        li_failed = request.args.get('e', (0,))[0] == '1'
        if fi is None:
            if DEV_FAKE_FLOW and not li_failed:
                lg.warning("No associated flow, simulating for development")
                fi = self._get_fake_flow(request)
            else:
                return self._render_error(request,
                        msg="No associated flow information")
        return self.render_tmpl(request, "auth_login.mako",
                                dev_fake=DEV_FAKE_FLOW,
                                login_failed=li_failed,
                                flowparams=fi.req_param_dict())

    def _get_associated_flow(self, request):
        #TODO: cache all flow information internally, don't do anything in
        #      the session

        # All windows of a web client correspond to a single session, so
        # orig_url needs to be stored with each window
        fi = None
        if request.args.has_key('f'):
            # prefer flow info directly from redirect if available
            lfid = long(request.args['f'][0], 16)
            rf = self.component.hr.get_redirected_flow(lfid)
            if rf.is_initialized:
                fi = _FlowInfo.from_flow(rf, self.component)
            else:
                lg.info("Invalid or expired flow key passed as GET " \
                        "parameter")
        else:
            # use flow info from form submission if available
            fi = _FlowInfo.from_request(request, self.component)

        if fi is not None:
            request.getSession().assoc_flow = fi
        else:
            # fall back on flow stored in session - orig_url may or may not
            # correspond to the correct URL for the window/tab making
            # the request
            fi = getattr(request.getSession(), 'assoc_flow', None)
            if fi is not None:
                fi.orig_url = None
        if fi is None:
            lg.warning("No valid flow information in request")
        return fi

    def _get_fake_flow(self, request):
        """Simulate flow information to ease development and debugging"""
        # generate from redirected_flow for more code coverage
        redir_flow = Redirected_flow()
        redir_flow.dpid = datapathid.from_host(0x0019d16c1233)
        redir_flow.flow.in_port = htons(123)
        redir_flow.flow.dl_src = create_eaddr("00:11:22:33:44:55")
        redir_flow.flow.nw_src = ipaddr(request.getClientIP()).addr
        redir_flow.payload_head = "Get / HTTP/1.1\r\n"\
                                  "Host: www.nicira.com\r\n\r\n"
        fi = _FlowInfo.from_flow(redir_flow, self.component)
        return fi

    def handle_check_for_auth(self, request):
        """Determine if location in request has user binding"""
        fi = self._get_associated_flow(request)
        if fi is None:
            lg.error("Invalid fi in check")
            return "0";
        d = self._check_user_bound_to_loc(request)
        d.addCallback(self._check_for_auth_cb, request)
        d.addErrback(self._check_for_auth_eb, request)
        return server.NOT_DONE_YET

    def _check_for_auth_cb(self, res, request):
        for binding in res:
            if binding[1] == Name.USER:
                request.write("1")
                request.finish()
                return
        request.write("0");
        request.finish()

    def _check_for_auth_eb(self, err, request):
        lg.error("Error in _check_user_bound_to_loc: '%s'"%err)
        request.write("-1")
        request.finish()

    def _check_user_bound_to_loc(self, request):
        lg.debug("Checking if session is authenticated")
        f = self._get_associated_flow(request)
        d = defer.Deferred()
        if f is None:
            d.callback(False)
        else:
            cb = lambda res : d.callback(res)
            self.component.bs.get_names(f.dpid, f.in_port, f.dl_src,
                                        f.nw_src, cb)
        return d

    def handle_opening_pu(self, request):
        """Display page in popup before login form is submitted"""
        # This is referenced in between opening the popup, and the
        # (immediate) form submission that follows, so it is unlikely
        # that the browser will ever request or render this.
        # Once the form is submitted, it should overwrite the page,
        # causing the refresh loop to end.
        session = request.getSession()
        pu_open_ts = getattr(session, 'pu_open_ts', None)
        if pu_open_ts is None:
            session.pu_open_ts = time.time()
        else:
            if time.time() - pu_open_ts > OPENING_PU_MAX_TM:
                #TODO: we could try to recover here
                session.pu_open_ts = None
                return self._render_error(request,
                        msg="Popup failed to submit form")
        return self.render_tmpl(request, "auth_in_progress.mako",
                refresh_ms=OPENING_PU_MAX_TM*1000,
                refresh_url=self.res_paths.opening_pu)

    def handle_wait_for_pu(self, request):
        # The popup success page will redirect this window when it has
        # received a result
        # TODO(?): handle the redirect failing
        session = request.getSession()
        wait_for_pu_ts = getattr(session, 'wait_for_pu_ts', None)
        if wait_for_pu_ts is None:
            session.wait_for_pu_ts = time.time()
        else:
            if time.time() - wait_for_pu_ts > WAIT_FOR_PU_MAX_TM:
                #TODO: we could try to recover here
                session.wait_for_pu_ts = None
                return self._render_error(request,
                        msg="Timed out waiting for popup to submit form")
        return self.render_tmpl(request, "auth_in_progress.mako",
                refresh_ms=1000, 
                refresh_url=self.res_paths.wait_for_pu)

    def handle_auth_status(self, request):
        #TODO:
        #      - popout has meta refresh of 1x1 image every N seconds
        #        where N < controller timeout.  Refresh image may (or
        #        may not) contain cookie param to prevent spoofing
        #        to keep other sessions alive
        #      - server hosting image calls hostActive() method on
        #        authenticator upon recipt of image request
        #

        fi = self._get_associated_flow(request)
        request.setHeader("Content-Type", "image/gif")
        self.component.auth.reset_inactivity_timeout(fi.dpid, fi.in_port,
                                                     fi.dl_src, fi.nw_src)
        return IMAGE_BUG_GIF #TODO: is this necessary

    def handle_do_login(self, request):
        fi = self._get_associated_flow(request)
        provided_uname = request.args.get('username', [None,])[0]
        provided_pw = request.args.get('password', [None,])[0]
        if (provided_uname is None) or (provided_pw is None) :
            lg.error("Missing required username or pw in post")
            return self._render_error(request, msg="Invalid POST parameters")
        d = self.component.dm.simple_auth(provided_uname, provided_pw)
        d.addCallback(self._do_login_cb, request, provided_uname, fi)
        d.addErrback(self._do_login_eb, request, provided_uname, fi)
        #TODO: return in progress form immediately
        return server.NOT_DONE_YET

    def _do_login_cb(self, res, request, provided_uname, fi):
        #XXX slowing things down for dev
        lg.debug("Sleeping for dev")
        self.component.post_callback(0,
                lambda : self._do_login_cb2(res, request,
                                            provided_uname, fi))

    def _do_login_cb2(self, res, request, provided_uname, fi):
        lg.debug("Done sleeping for dev")
        is_popup = (request.args.get("pu") == ['1'])
        if res.status == AuthResult.SUCCESS:
            fi.username = res.username
            lg.error("Authenticated "+str(fi.username))

            self.component.uel.log("userauthportal", LogEntry.INFO,
                    "{du} authenticated via captive portal "\
                    "({sl}; MAC %s; IP %s)"
                    %(fi.dl_src, ipaddr(fi.nw_src)),
                    du=fi.username.encode('utf-8'), set_src_loc=(fi.dpid,
                    fi.in_port))

            ae = Auth_event(Auth_event.AUTHENTICATE, fi.dpid,
                            fi.in_port, fi.dl_src,
                            fi.nw_src, False, UNKNOWN_HNAME,
                            fi.username.encode('utf-8'), 0, 0)
            self.component.post(ae)

            #For now, store username and url in session so the
            #/auth/success page can be rendered
            request.getSession().username = fi.username
            redir_url = fi.orig_url
            request.getSession().redir_url = redir_url

            # we no longer need the orig_url and don't want to hash on it
            fi.orig_url = None
            request.write(self.render_tmpl(request, "auth_logout.mako",
                                is_popup=is_popup,
                                is_logged_out=False,
                                flowparams=fi.req_param_dict(),
                                username = fi.username,
                                redir_url = redir_url))
        else:
            if self.component.config.log_invalid_username:
                lg.info("Authentication failed for '%s': %d (%s) at %s"
                        %(provided_uname, res.status, res.status_str(),
                        fi.location_string()))
                self.component.uel.log("userauthportal", LogEntry.INFO,
                        "{du} failed to authenticate at captive portal: "\
                        "%d (%s) ({sl}; MAC %s; IP %s)" %(res.status,
                        res.status_str(), fi.dl_src, ipaddr(fi.nw_src)), 
                        du = provided_uname.encode('utf-8'),
                        set_src_loc=(fi.dpid, fi.in_port))
            else:
                lg.info("Authentication failed : %d (%s) at %s"
                        %(res.status, res.status_str(),
                        fi.location_string()))
                self.component.uel.log("userauthportal", LogEntry.INFO,
                        "Authentication failure at captive portal: "\
                        "%d (%s) ({sl}; MAC %s; IP %s)"
                        %(res.status, res.status_str(), fi.dl_src,
                        ipaddr(fi.nw_src)),
                        set_src_loc=(fi.dpid, fi.in_port))
            request.write(self.render_tmpl(request, "auth_login.mako",
                    flowparams=fi.req_param_dict(), login_failed=True,
                    is_popup=is_popup))
        request.finish()

    def _do_login_eb(self, failure, request, provided_uname, fi):
        lg.error("Authentication error (%s) during authentication of '%s'" \
                %(repr(failure), provided_uname))
        request.write(self._render_error(request, msg="Exception during auth"))
        request.finish()

    def handle_do_logout(self, request):
        fi = self._get_associated_flow(request)
        if fi is None:
            return self._render_error(request, close_if_pu=False,
                    msg="Invalid flow information in logout post")
        ae = Auth_event(Auth_event.DEAUTHENTICATE, fi.dpid,
                        fi.in_port, fi.dl_src,
                        fi.nw_src, False, UNKNOWN_HNAME,
                        fi.username.encode('utf-8'), 0, 0)
        self.component.uel.log("userauthportal", LogEntry.INFO,
                "{du} deauthenticated via captive portal "\
                "({sl}; MAC %s; IP %s)"
                %(fi.dl_src, ipaddr(fi.nw_src)),
                du=fi.username.encode('utf-8'), set_src_loc=(fi.dpid,
                fi.in_port))
        self.component.post(ae)
        is_popup = request.args.get("pu") == ['1']
        return self.render_tmpl(request, "auth_logout.mako",
                                flowparams=fi.req_param_dict(),
                                logout=True, is_popup=is_popup)

    def handle_success(self, request):
        #this state is only valid on redirect from popup
        #TODO: figure out when to expire the session
        username = getattr(request.getSession(), 'username', None)
        redir_url = getattr(request.getSession(), 'redir_url', None)
        return(self.render_tmpl(request, "auth_success.mako",
                            is_popup=False,
                            username=username,
                            redir_url=redir_url))

    def _generic_req_eb(self, request):
        request.write(self.render_tmpl(request, "auth_error.mako"))
        request.finish()

    def handle_error(self, request):
        msg = request.args.get('msg', [None,])[0]
        return self._render_error(request, msg=msg)



class _FlowInfo(object):
    """Information needed to bind a request with a network flow
    """
    _http_req_get_re = re.compile(r"^GET (\S+) HTTP/(\S+)\r\n", re.I)
    _http_req_host_re = re.compile(r"Host: (\S+?)(:(\d+))?\r\n", re.I)
    _http_req_header_end_re = re.compile(r"\r\n\r\n")
    _http_req_abs_uri_re = re.compile(r"^(\S+?)://([^/]+?)(:(\d+))?/(\S+)$")

    def __init__(self, component):
        #Numeric values are stored in host byte order
        self.component = component
        self.dpid = None
        self.in_port = None
        self.dl_src = None
        self.nw_src = None
        self.orig_url = None
        self.username = None

    @classmethod
    def from_request(cls, req, component):
        if ( (not req.args.has_key("dpid")) or
             (not req.args.has_key("in_port")) or
             (not req.args.has_key("dl_src")) or
             (not req.args.has_key("nw_src")) or
             (not req.args.has_key("h"))):
            lg.warning("Unable to reconstruct flow information, missing "\
                    "required field(s)")
            return None
        #TODO: prevent replay attacks
        #TODO: encode url
        instance = _FlowInfo(component)
        #Mandatory fields
        instance.dpid     = datapathid.from_host(long(req.args["dpid"][0], 16))
        instance.in_port  = int(req.args["in_port"][0])
        instance.dl_src   = create_eaddr(req.args["dl_src"][0])
        instance.nw_src   = long(req.args["nw_src"][0])
        #Optional fields
        if req.args.has_key("b_user"):
            instance.username = req.args["b_user"][0]
        else:
            instance.username = None
        if req.args.has_key("rurl"):
            instance.orig_url = req.args["rurl"][0]
        else:
            instance.orig_url = None

        if instance.get_hash(component.cur_hashcookie) == req.args["h"][0]:
            return instance
        if instance.get_hash(component.old_hashcookie) == req.args["h"][0]:
            return instance
        lg.error("Hash cookies did not validate")
        return instance #XXX don't validate hash for now
        #return None

    def req_param_dict(self):
        ret = { "dpid"    : self.dpid,
                "in_port" : self.in_port,
                "dl_src"  : self.dl_src,
                "nw_src"  : self.nw_src,
                "h"       : self.get_current_hash()
        }
        if self.orig_url is not None:
            ret["rurl"] = self.orig_url
        return ret

    def get_current_hash(self):
        return self.get_hash(self.component.cur_hashcookie)

    def get_hash(self, hashCookie):
        m = md5.new()
        if self.dpid is not None:
            m.update(self.dpid.string())
        if self.in_port is not None:
            m.update(str(self.in_port))
        if self.dl_src is not None:
            m.update(str(self.dl_src))
        if self.nw_src is not None:
            m.update(str(self.nw_src))
        if self.orig_url is not None:
            m.update(self.orig_url)
        if self.username is not None:
            m.update(self.username)
        m.update(str(self.component.cur_hashcookie))
        return m.hexdigest()

    @classmethod
    def from_flow(cls, redir_flow, component):
        instance = _FlowInfo(component)
        # TODO: redir_flow.dpid is getting garbage collected, so we
        #       copy it for now
        #instance.dpid = redir_flow.dpid
        instance.dpid = datapathid(redir_flow.dpid)
        instance.in_port = ntohs(redir_flow.flow.in_port)
        # TODO: redir_flow.dl_src is getting garbage collected, so we
        #       copy it for now
        #instance.dl_src = redir_flow.flow.dl_src
        instance.dl_src = create_eaddr(redir_flow.flow.dl_src)
        instance.nw_src = c_ntohl(redir_flow.flow.nw_src)
        instance.orig_url = \
                instance._get_url_from_request(redir_flow.payload_head)
        instance.username = None
        return instance

    def _get_url_from_request(self, request_buf):
        ret = None
        #TODO: support URI encoded requests
        # parse the 'GET' request
        m = self._http_req_get_re.search(request_buf)
        if m is None:
            lg.debug("No URL from redirect: Didn't match 'GET': '%s'"\
                    %request_buf)
            return None
        uri = m.group(1)
        version = m.group(2)

        # parse the URI to see if it is absolute or relative
        m = self._http_req_abs_uri_re.search(uri)
        if m is not None:
            #absolute URI
            if m.group(1) != 'http':
                lg.debug("No URL from redirect: not an http request: '%s'"\
                        %request_buf)
                return None #we can't proxy requests other than http
            ret = uri
        else:
            #relative URI
            if uri[0] != '/':
                lg.debug("No URL from redirect: Not absolute URI, and URI "\
                        "doens't start with '/': '%s'" %request_buf)
                return None

            # find the header end so we don't mistake content for a host header
            m = self._http_req_header_end_re.search(request_buf)
            header_end_offset = len(request_buf)-1
            if m is not None:
                header_end_offset = m.start()

            # parse the host header if there is one
            m = self._http_req_host_re.search(request_buf)
            if m is not None and m.start() < header_end_offset:
                host = m.group(1)
                port = m.group(3)
                #build the url
                ret = "http://"+host
                if port is not None:
                    ret = ret + ":" + port
                ret = ret + uri

        if ret is  None:
            lg.debug("No URL from redirect: No host header captured: '%s'"\
                    %request_buf)
        #TODO: verify ret is valid
        return ret

    def location_string(self):
        if self.nw_src is not None:
            nwsrcstr = ipaddr(self.nw_src)
        return "AP:%s:%d MAC:%s IP:%s"%(self.dpid, self.in_port,
                self.dl_src, nwsrcstr)

    def __str__(self):
        return "%s Username:%s Original_URL:%s"%(self.location_string(),
                self.username, self.orig_url)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return userauthportal(ctxt)

    return Factory()
