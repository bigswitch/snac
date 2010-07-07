# Copyright 2008 (C) Nicira, Inc.
#
"""User authentication captive portal component

==== Overview ====

This component implements a means for establishing and maintaining a user to
network location binding in NOX via a web browser.  Users are redirected
to the portal by the http_redirector component, whose operation is governed
by the sepl policy.


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

    NOTE: The HTTP redirect will likely fail if the host web browser is
    statically configured to use a proxy on a different port.

    HTTP flows with active user bindings MUST be configured to *NOT*
    take the 'http_redirect' function action, as this will result in a
    browser redirect loop.

  Http_redirector :
    The http_redirector must be configured with the correct URL of the
    authentication portal.


==== Web Browser Compatibility ====

The captive portal component is meant to be compatible with all modern
web browsers (and some ancient ones too.)  While CSS, DOM and Javascript
support are strongly suggested, the core operation of the portal should
function in their absence.


==== Component Operation ====

The captiveportal authentication process requires the cooperation of
other components, as described in the Assumptions section above.

Bootstrap operation (outside of captiveportal):

1.  User opens web browser on host that currently does not have a user
    binding.  The web browser makes a web request (TCP port 80) to a URL 
    that is restricted to hosts with user bindings.

2.  Flow associated to the web request is passed from the openflow switch
    to the policy engine.

3.  Policy engine routes the flow to the http_redirector component.

4.  Http_redirector caches the flow information and HTTP request payload sent
    by the host.  It then redirects the client browser to the URL of the
    captiveportal, including an argument with a key to the cached flow
    information.

5.  Following the redirect, the client browser issues a request to the
    captiveportal, including http_redirector cached flow key argument.

Captiveportal operation:

6.  A client session key is automagically created by the twisted web
    server and passed along with each request.  The session key uniquely
    identifies a web client application, but not a specific tab/window.

7.  A query comes to the 'auth' URL.
    - The flow information associated with the request is queried from the
      http_redirector, and is parsed into a new _Flowinfo instance, which is
      saved with the session.

    - render cp_login.mako template:
      - A page consisting of a banner, disclaimer, and username/password form
        is displayed.  The form also contains hidden input field specifying
        the original URL requested by this browser tab/window.

    - If the browser supports DOM, Javascript and the XMLHttpRequest
      method, a timer is launched which polls the 'check_for_auth'
      URL for user authentication.
      - If the user has been authenticated, the page is replaced with the
        authentication success page (9.)

8. A form submit with username/password comes to the 'auth' URL.
    - If the browser supports DOM and Javascript, the submit button will
      be disabled, and a 'please wait' message will be displayed.
    - A simple_auth request is made to the directory manager
    - server waits for associated auth to return
      - If successful:
        - Render authentication success page (9.)
      - Else;
        - Render cp_login.mako with error message

9. A request is made from an authenticated user:
    - render cp_success.mako template:
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
import base64
import logging
import re
import socket
import time
import urllib

from twisted.internet import defer
from twisted.web import server, error

from nox.lib.core import *
from nox.lib.token_bucket import TokenBucket
from nox.lib.directory import *
from nox.lib.netinet.netinet import *
from twisted.web.util import redirectTo

from nox.apps.authenticator.pyauth import Auth_event, Authenticator, PyAuth
from nox.apps.bindings_storage.pybindings_storage import Name
from nox.apps.bindings_storage.pybindings_storage import pybindings_storage
from nox.apps.configuration.properties import *
from nox.apps.coreui import coreui
from nox.apps.coreui.authui import UIResource
from nox.apps.directory import directorymanager
from nox.apps.storage import TransactionalStorage
from nox.apps.user_event_log.pyuser_event_log import pyuser_event_log, LogEntry
from nox.ext.apps.http_redirector.pyhttp_redirector import *
from nox.ext.apps.redirproxy import redirproxy

lg = logging.getLogger("captiveportal")

DEV_VERBOSE   = False # XXX this should never be True in production
DEV_FAKE_FLOW = False # XXX this should never be True in production

PROPERTIES_SECTION = "captive_portal_settings"
UNKNOWN_HNAME = Authenticator.get_unknown_name()

def _file_to_base64(path):
    f = open(path, 'rb')
    ret = base64.b64encode(f.read())
    f.close()
    return ret


class captiveportal(Component):
    _static_url_root = '/static/nox/ext/apps/captiveportal/'
    _web_root  = '/cp/'
    _prop_root = _web_root + 'props/'
    _banner_image_name  = 'cp_banner'
    _custom_css_name    = 'local.css'
    web_resources = {
        'root'         : _web_root,
        'banner_image' : _prop_root + _banner_image_name,
        'custom_css'   : _prop_root + _custom_css_name,
        'default_css'  : _static_url_root + 'default.css' ,
        'js_lib'       : _static_url_root + 'cp.js' 
    }

    _static_file_base = coreui.coreui.STATIC_FILE_BASEPATH + \
            'nox/ext/apps/captiveportal/'
    _default_banner_file = _static_file_base + 'default_banner.jpg'
    _default_banner_content_type = u'image/jpeg'
    _default_properties = {
        'banner_image'              : _file_to_base64(_default_banner_file),
        'banner_image_content_type' : _default_banner_content_type,
        'org_name'                  : u"",
        'banner'                    : u"",
        'custom_css'                : u"div#banner {\n padding: 8px;\n "\
                                       "width: 300px;\n}",
        'soft_timeout_minutes'      : 60*3,
        'hard_timeout_minutes'      : 60*7,
        'log_invalid_username'      : 0,
        'auth_check_interval_sec'   : 4,
    }

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.auth    = None
        self.bs      = None
        self.coreui  = None
        self.dm      = None
        self.hr      = None
        self.storage = None
        self.uel     = None
        self.props   = None

    def getInterface(self):
        return str(captiveportal)

    def install(self):
        # this resolve may fail, which is ok 
        # this application does not need to depend on redirproxy
        # but should be able to use it if it is loaded
        self.redirproxy = self.resolve(redirproxy.redirproxy)
        
        self.auth = self.resolve(str(PyAuth))
        if self.auth is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(PyAuth))
        self.bs = self.resolve(str(pybindings_storage))
        if self.bs is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pybindings_storage))
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
        self.storage = self.resolve(TransactionalStorage)
        if self.storage is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(TransactionalStorage))
        self.uel = self.resolve(pyuser_event_log)
        if self.uel is None:
            raise Exception("Unable to resolve required component: '%s'"
                            %str(pyuser_event_log))

        #Register our URL paths after boostrap
        self.register_for_bootstrap_complete(self._register_resource_handlers)

        #Load our properties
        self.props = Properties(self.storage, PROPERTIES_SECTION)
        #properties requres an exclusive transaction for a load
        d = self.props.begin()
        d.addCallback(lambda x : self.props.load())
        d.addCallback(lambda x : self.props.commit())
        d.addCallback(self._initialize_default_properties)
        d.addCallback(lambda x: self.props.addCallback(self._config_update_cb))
        return d
    
    def _register_resource_handlers(self, *args):
        self.authres = AuthRes(self)
        self.coreui.install_resource(self._web_root, self.authres)

        propres = PropertyRes(self, PROPERTIES_SECTION)
        propres.register_property_resource(self._banner_image_name,
                'banner_image', None, 'banner_image_content_type', True)
        propres.register_property_resource(self._custom_css_name,
                'custom_css', 'text/css', None, False)
        self.coreui.install_resource(self._prop_root, propres)
        lg.debug("Ready for requests")
        return CONTINUE

    def _initialize_default_properties(self, res):
        def _set_defaults(res):
            for k, v in self._default_properties.items():
                if not k in self.props:
                    self.props[k] = v
            d = self.props.commit()
            return d
        d = self.props.begin()
        d.addCallback(_set_defaults)
        return d

    def _config_update_cb(self):
        # We don't need to do anything special when config changes, just
        # load the new values so they are used for future requests.
        lg.debug("Configuration updated")
        #properties requres an exclusive transaction for a load
        d = self.props.begin()
        d.addCallback(lambda x : self.props.load())
        d.addCallback(lambda x : self.props.commit())
        d.addCallback(lambda x: self.props.addCallback(self._config_update_cb))
        return d

    def get_property(self, prop_name):
        return self.props.get_simple_dict().get(prop_name, (None,))[0]


class PropertyRes(UIResource):
    """A web resource handler for serving resources out of configuration
    properties (from Transactional Storage)
    """
    isLeaf = True
    noUser = True

    def __init__(self, component, props_section_id):
        UIResource.__init__(self, component)
        self._props = Properties(component.storage, props_section_id)
        self._props_dirty = True
        self._registered_resources = {}

    def _update_properties(self):
        def _cache_resource_content(res):
            for path in self._registered_resources.keys():
                self._update_cached_property(path)
            self._props_dirty = False
            return self._props.addCallback(self._props_updated_cb)
        #properties requres an exclusive transaction for a load
        d = self._props.begin()
        d.addCallback(lambda x : self._props.load())
        d.addCallback(lambda x : self._props.commit())
        d.addCallback(_cache_resource_content)
        return d

    def _props_updated_cb(self):
        self._props_dirty = True

    def _update_cached_property(self, path):
        meta = self._registered_resources[path][0]
        (cp, ct, ctp, encoded) = meta
        if cp in self._props and (ct is not None or ctp in self._props):
            if encoded:
                content = base64.b64decode(self._props[cp][0])
            else:
                content = self._props[cp][0]
            if ct is not None:
                content_type = ct
            else:
                content_type = self._props[ctp][0]
            cached_resource = (content, content_type)
        else:
            cached_resource = (None, None)
        self._registered_resources[path] = (meta, cached_resource)
        
    def register_property_resource(self, path, content_prop, 
            content_type, content_type_prop, base64encoded):
        """Register path to return content in content_prop

        If content_type is None, the content type will be queried using
        the key content_type_prop; else content_type_prop is ignored.
        """
        meta = (content_prop, content_type, content_type_prop, base64encoded)
        self._registered_resources[path] = (meta, None)
        if not self._props_dirty:
            self._update_cached_property(path)
        #else the property will be set when we reload properties on render

    def unregister_property_resource(self, name):
        if name in self._registered_resources:
            del self._registered_resources[name]
        
    def render(self, request):
        def _do_render(res):
            path = '/'.join(request.postpath)
            if path in self._registered_resources:
                content, content_type = self._registered_resources[path][1]
                if content is None or content_type is None:
                    e = error.NoResource("Resource not configured.")
                    request.write(e.render(request))
                else:
                    request.setHeader('content-type', str(content_type))
                    request.setHeader('content-length', str(len(content)))
                    if type(content) == unicode:
                        content = content.encode('utf-8')
                    request.write(content)
            else:
                e = error.NoResource("Resource not found.").render(request)
                request.write(e)
            request.finish()
            
        if self._props_dirty:
            d = self._update_properties()
        else:
            d = defer.succeed(None)
        d.addCallback(_do_render)
        return server.NOT_DONE_YET
        

class AuthRes(UIResource):
    isLeaf = False
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)
        self.component = component
        self.res_paths = component.web_resources.copy()
        self.res_paths.update({
            'auth_check' : self.res_paths['root'] + '?check=1'
        })

    def _get_url_for_display(self, full_url):
        if len(full_url) < 50:
            return full_url
        return full_url[:46]+" ..."

    def _render_tmpl(self, request, name, *args, **kwargs):
        """Render mako template with base arguments
        """
        rurl = (request.args.get("rurl") or ('',))[0] or ''
        proxy_cookie = (request.args.get("proxy_cookie") or ('',))[0] or ''
	if proxy_cookie == "": 
	        proxy_param = ""
	else:
	        proxy_param = "&proxy_cookie=" + proxy_cookie

        return UIResource.render_tmpl(self, request, name, 
                p=self.component.get_property, r=self.res_paths, rurl=rurl,
                proxy_cookie=proxy_cookie, proxy_param=proxy_param,  
                rurl_disp=self._get_url_for_display(rurl), *args, **kwargs)

    def _render_error(self, request, msg=None):
        rendered_msg = None
        if DEV_VERBOSE:
            rendered_msg = msg
        return self._render_tmpl(request, "cp_error.mako", msg=rendered_msg)

    def render(self, request):
        lg.debug("Captive Portal Request: %s:%s %s"
                %(request.method, request.path, request.args.keys()))
        if request.postpath != []:
            #should never get called with this case since isLeaf==False
            msg = "Invalid %s URL: '%s'"%(request.method, str(request.path))
            lg.error(msg)
            return self._render_error(request, msg)

        #Special case for auth page preview
        if request.args.has_key('preview'):
            return self._render_tmpl(request, 'cp_login.mako', preview=True)
   
        if request.args.has_key('done'): 
            request.write(self._render_tmpl(request, "cp_success.mako"))
            request.finish()
            return server.NOT_DONE_YET

        def after_flow_retrieval(flowinfo): 
            #Special case for JS background auth check
            if request.method.upper() == 'POST' \
                and request.args.get('check', (None,))[0]:
              #Invalid flowinfo is handled by _handle_bg_auth_check
              return self._handle_bg_auth_check(request, flowinfo)

            #Normal web client request
            if flowinfo is None:
              #TODO: use non-generic error page?
              msg = "No associated flow information"
              return self._render_error(request, msg)

            #Check current user authentication status before handling the request
            d2 = self._check_user_bound_to_loc(flowinfo)
            d2.addCallback(self._handle_user_auth_request, request, flowinfo)

	         
        d = self._get_flowinfo_for_ip(request)
        if d is not None: 
          d.addCallback(after_flow_retrieval)
	else: 
          request.finish()

        return server.NOT_DONE_YET

    # queries binding storage to get the network identifiers 
    # (dpid,port,mac,ip) associated with this client IP
    # and builds a flowinfo out of it
    #NOTE: this won't work if the client is behind a NAT! 
    def _get_flowinfo_for_ip(self, request):
        rurl = self._get_orig_url(request)
        proxy_cookie = request.args.get("proxy_cookie",[""])[0]
        if proxy_cookie != "": 
          if self.component.redirproxy == None: 
            request.write(self._render_tmpl(request, "cp_login.mako",
                            login_failed=True))
            lg.error("'proxy_cookie' set but redirproxy is not running")
            return None
          ip_str = self.component.redirproxy.getIPFromCookie(proxy_cookie)
          if ip_str is None: 
            # send them to their orignal url. they will get redirected 
            # back to hear again, but this time with a fresh cookie
            redirectTo(rurl, request)
            return None
        else: 
          ip_str = request.getClientIP()

        if ip_str == "127.0.0.1": 
               # handle case when an unauthenticated client accesses this
               # page directly via HTTPS.  The request will not have a 
               # proxy_cookie.  So, we need to redirect them to an HTTP
               # page that will allow the redirproxy to insert a proxy_cookie
               # and again redirect to the captive portal.
               # We redirect to the captive portal page with done=1, so the
               # redirect after the login will make sense
               url = self.component.redirproxy.redir_url.replace('https:',
                                                          'http:', 1)
               lg.error("direct HTTPS access to CP page from proxied client") 
               redirectTo(url + "?done=1", request)
               return None

        ip = c_ntohl(create_ipaddr(ip_str).addr)

        def create_flowinfo(netinfos):
            for ni in netinfos:
                flowinfo  = _FlowInfo.from_netinfo_tuple(ni,rurl)
                return flowinfo
            #FIXME: in the future, we should throw an Auth_event for each
            # netinfo this IP is bound to.   
            defer.fail("No netinfos found matching %s" % request.getClientIP())

        d = self.component.bs.get_netinfos_by_ip(ip)
        d.addCallback(create_flowinfo)
        d.addErrback(self._get_netinfos_eb,request) 
        return d

    def _get_netinfos_eb(self, failure, request):
        lg.error("Could not find binding data for request: %s"  % failure.value)
        request.write(self._render_error(request, \
              msg="No data found for network address: %s" % \
              request.getClientIP()))
        request.finish()

    def _handle_user_auth_request(self, is_authenticated, request, flowinfo):
        session = request.getSession()
        if is_authenticated:
            #Sanity check for redirect loops
            session = request.getSession()
            if not hasattr(session, 'redir_tb'):
                session.redir_tb = TokenBucket(8, .5)
            if not session.redir_tb.consume(1):
                #Error page has no redirect, so the loop should stop
                request.write(self._render_error(request, "Redirect loop"))
            else:
                request.write(self._render_tmpl(request, 'cp_success.mako'))
        else:
            #check if auth_request
            username = request.args.get('username')
            password = request.args.get('password')
            if request.method.upper() == 'POST':
                if username and password:
                    if not username[0]:
                        request.write(self._render_tmpl(request,
                                "cp_login.mako", login_failed=True))
                    else:
                        d = self.component.dm.simple_auth(username[0],
                                password[0])
                        d.addCallback(self._do_login_cb, request, username[0],
                                flowinfo)
                        d.addErrback(self._do_login_eb, request, username[0],
                                flowinfo)
                        return server.NOT_DONE_YET
                else:
                    lg.error("Missing required username or password in POST")
                    request.write(self._render_tmpl(request, "cp_login.mako",
                            login_failed=True))
            else:
                #No auth yet, render the login page
                request.write(self._render_tmpl(request, 'cp_login.mako'))
        request.finish()
        return server.NOT_DONE_YET

    # FIXME: this is a silly wrapper implementation that actually 'forgets'
    # all of the data we have cached for the flow, except for the URL.  
    # In the future, we will stop caching everything except the URL because
    # we can fetch that data from binding storage
    def _get_orig_url(self,request):
        if 'rurl' in request.args:
            return request.args['rurl'][0]
        fi = self._get_associated_flow(request)
        if fi:
            return fi.orig_url
        else:
            None

    def _get_associated_flow(self, request):
        # All windows of a web client correspond to a single session, so
        # orig_url for each window needs to be passed as parameters
        # rather than in the session
        fi = None
        if request.args.has_key('f'):
            # prefer flow info directly from redirect if available
            lfid = long(request.args['f'][0], 16)
            rf = self.component.hr.get_redirected_flow(lfid)
            if rf.is_initialized:
                fi = _FlowInfo.from_flow(rf)
                request.getSession().assoc_flow = fi
                #bootstrap the redirect url parameter from the redirect info
                request.args["rurl"] = [fi.orig_url]
            else:
                lg.info("Invalid or expired flow key passed as GET " \
                        "parameter")
                fi = None
        else:
            # use flow info stored in session
            fi = getattr(request.getSession(), 'assoc_flow', None)

        if fi is None:
            lg.warning("No valid flow information in request")
            if DEV_FAKE_FLOW:
                lg.warning("Simulating flow information for development")
                fi = _FlowInfo.get_faked_flow(request)
                request.getSession().assoc_flow = fi
                request.args["rurl"] = [fi.orig_url]
                request.getSession().server_message = "No flow information "\
                        "provided, simulating for development."
        return fi

    def _check_user_bound_to_loc(self, flowinfo, squash_errback=True):
        """Return deferred return true iff a user is bound to the location
        of the flowinfo source.
        """
        def _is_bound_user_cb(res):
            for binding in res:
                if binding[1] == Name.USER:
                    lg.debug("User is authenticated")
                    return True
            lg.debug("User is not authenticated")
            return False

        def _is_bound_user_eb(res):
            lg.warn("Error checking bindings storage for names (flow '%s'): %s"
                    %(str(flowinfo), res.value))
            if squash_errback:
                return False
            else:
                return res

        if flowinfo is None:
            return defer.succeed(False)
        d = defer.Deferred()
        cb = lambda res : d.callback(res)
        self.component.bs.get_names(flowinfo.dpid, flowinfo.in_port,
                                    flowinfo.dl_src, flowinfo.nw_src, cb)
        d.addCallbacks(_is_bound_user_cb, _is_bound_user_eb)
        return d

    def _handle_bg_auth_check(self, request, flowinfo):
        """Handle XMLHttpRequest auth check from Javascript
        """
        def _check_for_auth_cb(is_authenticated):
            if is_authenticated:
                request.write("1")
            else:
                request.write("0")
            request.finish()

        def _check_for_auth_eb(err, request):
            #returning -1 causes client to stop asking
            request.write("-1")
            request.finish()

        if flowinfo is None:
            lg.error("Invalid flow in background auth check")
            return "-1";
        d = self._check_user_bound_to_loc(flowinfo, squash_errback=False)
        d.addCallbacks(_check_for_auth_cb, _check_for_auth_eb)
        return server.NOT_DONE_YET

    def _do_login_cb(self, res, request, provided_uname, fi):
        if res.status == AuthResult.SUCCESS:
            user = res.username.encode('utf-8')
            lg.info("Authentication successful for '%s'" %user)

            self.component.uel.log("captiveportal", LogEntry.INFO,
                    "{du} authenticated via captive portal "\
                    "({sl}; {sh}; MAC %s; IP %s)"
                    %(fi.dl_src, ipaddr(fi.nw_src)),
                    du=user,src_ip=fi.nw_src)

            sto = self.component.get_property('soft_timeout_minutes') or 0
            hto = self.component.get_property('hard_timeout_minutes') or 0
            ae = Auth_event(Auth_event.AUTHENTICATE, fi.dpid, fi.in_port,
                            fi.dl_src, fi.nw_src, False, UNKNOWN_HNAME, user,
                            int(sto)*60, int(hto)*60)
            self.component.post(ae)

            content = self._render_tmpl(request, 'cp_success.mako',
                    user=user)
        else:
            if self.component.get_property('log_invalid_username'):
                lg.info("Authentication failed for '%s': %d (%s) at %s"
                        %(provided_uname, res.status, res.status_str(),
                        fi.location_string()))
                self.component.uel.log("captiveportal", LogEntry.INFO,
                        "{du} failed to authenticate at captive portal: "\
                        "%d (%s) ({sl}; {sh}; MAC %s; IP %s)" %(res.status,
                        res.status_str(), fi.dl_src, ipaddr(fi.nw_src)), 
                        du = provided_uname.encode('utf-8'),
                        set_src_loc=(fi.dpid, fi.in_port))
            else:
                lg.info("Authentication failed : %d (%s) at %s"
                        %(res.status, res.status_str(),
                        fi.location_string()))
                self.component.uel.log("captiveportal", LogEntry.INFO,
                        "Authentication failure at captive portal: "\
                        "%d (%s) ({sl}; {sh}; MAC %s; IP %s)"
                        %(res.status, res.status_str(), fi.dl_src,
                        ipaddr(fi.nw_src)),
                        set_src_loc=(fi.dpid, fi.in_port))
            content = self._render_tmpl(request, "cp_login.mako",
                    login_failed=True)
        request.write(content)
        request.finish()
        return server.NOT_DONE_YET

    def _do_login_eb(self, failure, request, provided_uname, fi):
        lg.error("Authentication error (%s) during authentication of '%s'" \
                %(failure.value, provided_uname))
        request.write(self._render_error(request, msg="Exception during auth"))
        request.finish()
        return server.NOT_DONE_YET
        

    def _generic_req_eb(self, request):
        request.write(self._render_tmpl(request, "cp_error.mako"))
        request.finish()


class _FlowInfo(object):
    """Information needed to bind a request with a network flow
    """
    _http_req_get_re = re.compile(r"^GET (\S+) HTTP/(\S+)\r\n", re.I)
    _http_req_host_re = re.compile(r"Host: (\S+?)(:(\d+))?\r\n", re.I)
    _http_req_header_end_re = re.compile(r"\r\n\r\n")
    _http_req_abs_uri_re = re.compile(r"^(\S+?)://([^/]+?)(:(\d+))?/(\S+)$")
    #Note: do not add tabs, newlines, etc to the allowed list below
    #      becausse they are stripped by the browser and could be used
    #      to obfuscate the 'javascript:' tag.  Space (0x20) is okay.
    _js_filter_re = re.compile(r"[^\w \t.\-_/,;:@&=?+$#\^|)(]|javascript:",
            re.IGNORECASE)

    def __init__(self):
        #Numeric values are stored in host byte order
        self.dpid = None
        self.in_port = None
        self.dl_src = None
        self.nw_src = None
        self.orig_url = None
        self.username = None

    @classmethod
    def from_flow(cls, redir_flow):
        instance = _FlowInfo()
        # TODO: redir_flow.dpid is getting garbage collected, so we
        #       copy it for now
        #instance.dpid = redir_flow.dpid
        instance.dpid = datapathid(redir_flow.dpid)
        instance.in_port = socket.ntohs(redir_flow.flow.in_port)
        # TODO: redir_flow.dl_src is getting garbage collected, so we
        #       copy it for now
        #instance.dl_src = redir_flow.flow.dl_src
        instance.dl_src = create_eaddr(redir_flow.flow.dl_src)
        instance.nw_src = c_ntohl(redir_flow.flow.nw_src)
        instance.orig_url = \
                instance._get_url_from_request(redir_flow.payload_head)
        instance.username = None
        return instance
    
    @classmethod
    def from_netinfo_tuple(cls, net_info,url): 
        instance = _FlowInfo()
        instance.dpid = create_datapathid_from_host(net_info[0])
        instance.in_port = net_info[1]
        instance.dl_src = create_eaddr(net_info[2])
        instance.nw_src = net_info[3]
        instance.orig_url = url 
        instance.username = None
        return instance



    @staticmethod
    def get_faked_flow(request):
        """Simulate flow information to ease development and debugging"""
        # generate from redirected_flow for more code coverage
        redir_flow = Redirected_flow()
        redir_flow.dpid = datapathid.from_host(0x0019d16c1233)
        redir_flow.flow.in_port = htons(123)
        redir_flow.flow.dl_src = create_eaddr("00:11:22:33:44:55")
        redir_flow.flow.nw_src = ipaddr(request.getClientIP()).addr
        redir_flow.payload_head = "Get /ig?hl=en&source=iglk HTTP/1.1\r\n"\
                                  "Host: www.google.com\r\n\r\n"
        fi = _FlowInfo.from_flow(redir_flow)
        return fi

    def _get_url_from_request(self, request_buf):
        ret = None
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
                        "doesn't start with '/': '%s'" %request_buf)
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
                #build the URL
                ret = "http://"+host
                if port is not None:
                    ret = ret + ":" + port
                ret = ret + uri

        if ret is  None:
            lg.debug("No URL from redirect: No host header captured: '%s'"\
                    %request_buf)
            return None
        #we render the URL in the page, so escape any potential nasties
        escaped_url = urllib.unquote(ret)
        if self._js_filter_re.search(escaped_url):
            lg.warn("Not returning potentially malicious URL '%s'" %ret)
            return None
        return ret

    def location_string(self):
        if self.nw_src is not None:
            nwsrcstr = ipaddr(self.nw_src)
        else:
            nwsrcstr = ""
        return "Location:%s:%d MAC:%s IP:%s"%(self.dpid, self.in_port,
                self.dl_src, nwsrcstr)

    def __str__(self):
        return "%s Username:%s Original_URL:%s"%(self.location_string(),
                self.username, self.orig_url)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return captiveportal(ctxt)

    return Factory()

