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
from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *
from nox.lib.directory import AuthResult
from nox.lib import config

from twisted.internet import defer
from twisted.web.resource import Resource
from twisted.web import server
from twisted.web.util import redirectTo
from twisted.python import log
from twisted.python.failure import Failure
from mako.template import Template
from mako.lookup import TemplateLookup

from nox.ext.apps.directory.directorymanager import directorymanager

import os
import types
import urllib
import coreui
    
# Twisted hardcodes the string TWISTED_SESSION as the cookie name.  
# This hack let's us append a Nicira string to that cookie name.  
# In the future, we may want to override Request.getSession() 
# as implemented in twisted/web/server.py to completely remove
# TWISTED_SESSION from the cookie name.  
# NOTE: spaces in the cookie name are incompatible with Opera
def get_current_session(request): 
        old_sitepath = request.sitepath
        request.sitepath = [ "Nicira_Management_Interface" ]
        session = request.getSession()
        request.sitepath = old_sitepath
        return session 


all_immutable_roles = ["Superuser",
                       "Policy Administrator",
                       "Network Operator",
                       "Security Operator",
                       "Viewer",
                       "No Access" ]


class UnknownCapabilityError(Exception):
    pass

class InvalidRoleError(Exception):
    pass

class authui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None
        self.directorymanager = self.resolve(directorymanager)

    def setup_immutable_roles(self):
      # Create and register the immutable roles
      for name in all_immutable_roles:
        if name == "Superuser":
            r = SuperuserRole(name)
        elif name == "No Access":
            r = NoAccessRole(name)
        else:
            r = Role(name, immutable=True)
        Roles.register(r)
    
      self.coreui.authui_initialized = True

    def bootstrap_complete_callback(self, *args):
        # if these resources are installed within install(), 
        # they are not able to resolve authui
        self.coreui.install_resource("/login", LoginRes(self))
        self.coreui.install_resource("/logout", LogoutRes(self))
        self.coreui.install_resource("/denied", DeniedRes(self))
        self.coreui.install_resource("/server_error", ServerErrRes(self))

        self.setup_immutable_roles()
        return CONTINUE
    
    def install(self):
        self.coreui = self.resolve(str(coreui.coreui))
        self.register_for_bootstrap_complete(self.bootstrap_complete_callback)

    def requestIsAuthenticated(self, request):
        session = get_current_session(request)

        if hasattr(session, "roles"):
            return True

        if not self.directorymanager.supports_authentication():
            session.requestIsAllowed = requestIsAllowed
            user = User("assumed-admin", set(("Superuser",)))
            session.user = user
            roles = [ Roles.get(r) for r in user.role_names ]
            session.roles = roles
            session.language = "en"
            return True

        return False

    def getInterface(self):
        return str(authui)

class Capabilities:
    """Stores and provides info on entire set of defined capabilities"""

    def __init__(self):
        self._dict = {}

    def register(self, name, description, immutable_roles=None):
        """Register a capability.

        Capabilities used to control visibity and actions in the UI should
        be registered using this method in the component's install() method.

        Arguments are:
            name: The name of the capability.  This is the string that will
                 be used to refer to the capability subsequently in tests,
                 etc.
            description: A user-readable description of the capability.
                 This will be displayed in the role definition UI to
                 assist the user in determining the appropriate capabilities
                 to give to the role.
            immutable_roles: A list of the names of immutable roles that
                 should have this capability.  Immutable roles are a default
                 set of roles provided by Nicira which the user can not
                 edit.  The capabilities for each of those roles are built
                 from these lists.  This is needed because the capability
                 set may change over time and the editable roles will always
                 assume a role does not have a capability if the user did
                 not specifically set it.  Note it is not neccesary to
                 include the 'Superuser' role in this list as the
                 implementation gurantees that role will have all
                 capabilities."""

        if immutable_roles == None:
            immutable_roles = []
        else:
            for r in immutable_roles:
                if r not in all_immutable_roles:
                    raise InvalidRoleError, "Only roles in authui.all_immutable_roles are appropiate."

        self._dict[name] = (description, immutable_roles)

    def has_registered(self, name):
        return self._dict.has_key(name)

    def list(self):
        return self._dict.keys()

    def describe(self, name):
        try:
            return self._dict[name][0]
        except KeyError, e:
            raise UnknownCapabilityError, str(name)

    def immutable_roles(self, name):
        try:
            return self._dict[name][1]
        except KeyError, e:
            raise UnknownCapabilityError, str(name)

# Following ensures there is only ever one capabilities manager...
Capabilities = Capabilities()

class Role:
    """Named set of capabilities"""
    def __init__(self, name, immutable=False):
        self.name = name
        self._capabilities = set()
        if immutable:
            self._immutable = False # is overridden below...
            if not  self.name in all_immutable_roles:
                raise InvalidRoleError, "Only roles in authui.all_immutable_roles can be set immutable."
            for c in Capabilities.list():
                if name in Capabilities.immutable_roles(c):
                    self.add_capability(c)
        self._immutable = immutable

    def capabilities(self):
        return self._capabilities

    def has_capability(self, name):
        return name in self._capabilities

    def has_all_capabilities(self, capability_set):
        return len(capability_set.difference(self._capabilities)) == 0

    def has_anyof_capabilities(self, capability_set):
        return len(capability_set.intersection(self._capabilities)) != 0

    def is_immutable(self):
         return self._immutable

    def add_capability(self, name):
        if not self._immutable:
            if Capabilities.has_registered(name):
                self._capabilities.add(name)
            else:
                raise UnknownCapabilityError, "Name=%s" % name

    def remove_capability(self, name):
        if not self._immutable:
            try:
                self._capabilities.remove(name)
            except KeyError, e:
                pass

class SuperuserRole(Role):
    """Role guaranteed to always have all capabilities"""

    def __init__(self, name):
        Role.__init__(self, name, True)

    def capabilities(self):
        return Capabilities.list()

    def has_capability(self, name):
        return True

    def has_all_capabilities(self, capability_set):
        return True

    def has_anyof_capabilities(self, capability_set):
        return True

class NoAccessRole(Role):
    """Role guaranteed to never have any capabilities"""
    def __init__(self, name):
        Role.__init__(self, name, True)

    def capabilities(self):
        return []

    def has_capability(self, name):
        return False

    def has_all_capabilities(self, capability_set):
        return False

    def has_anyof_capabilities(self, capability_set):
        return False

class Roles:
    """Manages defined roles."""

    def __init__(self):
        self._roles = {}

    def register(self, role):
        self._roles[role.name] = role

    def has_registered(self, role_name):
        return self._roles.has_key(role_name)

    def get(self, role_name):
        try:
            return self._roles[role_name]
        except KeyError, e:
            raise InvalidRoleError(role_name)

    def names(self):
        return [ r.name for r in self._roles.values() ]

    def instances(self):
        return self._roles.values()

# Following ensures there is only ever one roles manager...
Roles = Roles()


class User:
    """User information class"""
    def __init__(self, username=None, role_names=set(), language=None):
        self.username = username
        self.language = language
        self.role_names = role_names

class InvaidAuthSystemError(Exception):
    pass


def redirect(request, uri):
    # TBD: make handle child links automatically, normalize URI, etc.
    return redirectTo(uri, request)



def requestIsAllowed(request, cap):
    session = get_current_session(request)
    try:
        roles = session.roles
    except AttributeError:
        e = "Forbidding access due to unknown role in requestIsAllowed()"
        log.err(e, system="authui")
        return False
    if cap is None:
        return True
    for role in roles:
        if role.has_all_capabilities(cap):
            return True
    return False


class MissingTemplateError(Exception):
    pass


class UIResource(Resource):
    """UI resource class handling template search and authentication.

    This is a subclass of twisted.web.resource.Resource that ensures that
    the current session is associated with a user with the required
    capabilities set to interact with the resource.  It is intended to be
    subclassed in the same way as its twisted parent class.  Similar to
    the way the Twisted Resource class uses the isLeaf class variable,
    subclasses of this class can use two class variables to control
    authentication:

        noUser: (default=False) if True, no authentication will be
                done for this resource.
        required_capabilities: (default=set()) a set object of capabilities
                the user must hold to interact with this resource.
                Capabilites in the list are supplied as strings naming the
                capability and must also be registered with the capabilities
                manager (authui.Capabilities).  Alternatively, can be a
                dictionary keyed by request method containing a set of
                capabilities for each request method implemented by the
                resource.  If a method is implemented but has not entry
                in the dictionary, it is assummed that no capabilities
                are required.

    Note that the capability checking is primarily a convenience to
    handle the most common cases for simple resources.  For more
    complex situations such as a resources that parses request.postpath
    and thus supports many different URIs, it may be appropriate for the
    method specific render methods to check capabilities directly.

    This class also sets up component specific template search paths,
    and provides a conveience function to render templates with global
    site configuration information passed into the template using the
    contents of the coreui component siteConfig dictionary."""

    noUser = False
    required_capabilities = set()
    template_search_path = [ coreui.coreui ]

    def _tmpl_paths(self, component, path_type):
        # TBD: come up with the right solution for supporting finding
        # TBD:    templates after install.  Install dir templates should
        # TBD:    be lower priority than build dir templates so we use
        # TBD:    buildir templates in preference.
        interface = component.getInterface().split(".")
        pkgpath = interface[0]
        for p in interface[1:-2]:
            pkgpath = os.path.join(pkgpath, p)
        return [ os.path.join(pkgpath, path_type, interface[-1]) ]

    def __init__(self, component):
        Resource.__init__(self)
        self.component = component
        self.coreui = component.resolve(str(coreui.coreui))
        self.authui = component.resolve(str(authui))

        # TBD: select base_module_dir based on whether started in build
        # TBD:    directory or not.
        started_in_build_dir = True
        if started_in_build_dir:
            i = 0
        else:
            i = 1
        base_module_dir = self._tmpl_paths(self.component, "mako_modules")[i]
        base_template_dirs = []
        base_template_dirs.extend(self._tmpl_paths(self.component, "templates"))
        for o in self.template_search_path:
            if str(o) == self.component.getInterface():
                continue
            c = self.component.resolve(str(o))
            base_template_dirs.extend(self._tmpl_paths(c, "templates"))

        self.tlookups = {}
        for l in coreui.supported_languages:
            template_dirs = []
            module_dir = os.path.join(base_module_dir, l)
            for d in base_template_dirs:
                template_dirs.append(os.path.join(d, l))
                if l != "en":
                    template_dirs.append(os.path.join(d, "en"))
                template_dirs.append(d)
            self.tlookups[l] = TemplateLookup(directories=template_dirs,
                                              module_directory=module_dir,
                                              output_encoding='utf-8',
                                              encoding_errors='replace')

    def _lang_from_request(self, request):
        languages = []
        if request.getHeader("Accept-Language") is None:
            return "en"
        for l in request.getHeader("Accept-Language").split(","):
            t = l.split(";q=")
            name = t[0].strip()
            if len(t) > 1:
                qvalue = float(t[1])
            else:
                qvalue = 1.0
            languages.append((name, qvalue))
        languages.sort(key=lambda x: x[1], reverse=True)
        lang = "en"
        base_lang = lang
        if len(languages) > 0:
            t = languages[0][0].split("-")
            if len(t) > 1:
                lang = t[0].lower() + "_" + t[1].upper()
            else:
                lang = t[0].lower()
            base_lang = t[0].lower()

        if base_lang not in coreui.supported_languages:
            lang = "en"   # This had better always be supported.

        return lang

    def _lookup_template(self, lang, name):
        if self.tlookups.has_key(lang):
            return self.tlookups[lang].get_template(name)
        else:
            t = lang.split("_")
            if len(t) > 1:
                return self._lookup_template(t[0], name)
        raise MissingTemplateError, "lang=%s, name=%s" % (lang, name)

    def pp_empty(self, pcstr, argd):
        """Verify a null string at a location in the postpath.

        No argd is required.  Typically this would be used at
        the end of a rule to verify a path ends with a trailing
        slash."""
        if pcstr == "":
            return True
        return None

    def pp_opt_empty(self, pcstr, argd):
        """Verify an optional null string at a location in the postpath.

        This is exactly the same as pp_empty() except that it still
        succeeds if pcstr is None, indicating the path component
        does not exist.  It returns False in this case.  This can be
        used to allow a single rule to cover both trailing slash and
        non-trailing slash cases."""
        if pcstr == None:
            return False
        if pcstr == "":
            return True
        return None

    def pp_static_str(self, pcstr, argd):
        """Verify a static string at a location in the postpath.

        The argd dictionary must contain the following argument:

           str: The string to match against

        The argd dictionary may contain the following argument:

           foldcase: If true, both str in argd and the pcstr are
                converted to lowercase before comparison.

        The value of the string as it existed in the path component
        is returned on success."""
        if pcstr == None:
            return None
        try:
            foldcase = argd["foldcase"]
        except KeyError:
            foldcase = False
        if foldcase:
            if pcstr.lower() == argd["str"].lower():
                return pcstr
        else:
            if pcstr == argd["str"]:
                return pcstr
        return None

    def parse_postpath(self, request, rules):
        """Parse the postpath according to a set of rules.

        NOTE: This is only intended for use by subclasses!

        The rules are lists of lists of the form:

           [ <rulename>, [[<path component name>, <check method>, <argd>]...]]

        The <check method> should should have the signature:

            method(self, path_component_str, argd)

        The method should return the validated value for this component of
        the path or None, indicating the test failed.  The argd
        parameter is an additional dictionary of arguments for the method.
        The method can use this as required.  It's docstring should indicate
        the valid values a caller can set in it.  If it doesn't require any
        additional arguments, the rule can specify it as None.

        This method will test each rule in the order they are specified
        and return a 2-tuple consisting of the name of the first rule
        that matched (or None if no rule matched) and a dictionary
        containing the validated values from each path component keyed
        by the path component name (or a failure message to be passed to
        badRequest() if no rule matched).

        If there are more path component checks than actual path components,
        the remaining checks will be called with a path_component_str
        of None.  The check method should be prepared for this.  if
        all path component checks pass but there are still path component
        value remaining the test will be considered to have failed."""
        failure_msg = ["The received request was:\n\n    ",
                       request.method, " ", request.path,
                       "\n\nIt was matched against the following possibilities",
                       " and each failed for the reason given.\n"]
        for r in rules:
            rulename, checks = r
            i = 0
            resultd = {}
            failed_component = None
            failure_msg.append("\n    - /")
            failure_msg.append("/".join(request.prepath))
            for c in checks:
                pcname, check_method, argd = c
                if check_method == self.pp_empty:
                    failure_msg.append("/")
                elif check_method == self.pp_opt_empty:
                    pass
                else:
                    failure_msg.append("/")
                    failure_msg.append(pcname)
                if failed_component != None:
                    continue
                try:
                    pcstr = request.postpath[i]
                except IndexError:
                    pcstr = None
                pcvalue = check_method(pcstr, argd)
                if pcvalue == None:
                    if check_method == self.pp_opt_empty:
                        failed_component = "end of expected request."
                    elif check_method == self.pp_empty:
                        failed_component = "at required trailing slash of request."
                    else:
                        failed_component = pcname
                    continue
                else:
                    resultd[pcname] = pcvalue
                i += 1
            if failed_component != None:
                failure_msg.append("\n      Failed at ")
                failure_msg.append(failed_component)
                failure_msg.append("\n")
            elif i >= len(request.postpath):
                return (rulename, resultd)
            else:
                failure_msg.append("\n      Failed due to contents beyond the end of the expected request.")
        return (None, "".join(failure_msg))

    def render_tmpl(self, request, name, *arg, **data):
        session = get_current_session(request)
        lang = getattr(session, "language", None)
        if lang == None:
            lang = self._lang_from_request(request)
            # This may be overridden after login based on user preferences
            session.language = lang
        tmpl = self._lookup_template(lang, name)
        return tmpl.render(siteConfig=self.coreui.siteConfig,
                           request=request, session=session, *arg, **data)

    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)

    def _authredirect(self, request):

        if self.noUser:       # If resource doesn't require user at all...
            get_current_session(request).requestIsAllowed = requestIsAllowed
            return None

        if not self.authui.requestIsAuthenticated(request):
            get_current_session(request).requestIsAllowed = requestIsAllowed
            return "/login?last_page=" + urllib.quote(request.uri)

        if type(self.required_capabilities) == types.DictionaryType:
            try:
                cs = self.required_capabilities[request.method]
            except KeyError, e:
                cs = None
        else:
            cs = self.required_capabilities

        if cs != None and not isinstance(cs, set):
            e = "Invalid required_capabilities on object: %s" % repr(self)
            log.err(e, system="authui")
            return (False, "/server_error")

        if not requestIsAllowed(request, cs):
            return "/denied"

        return None

    def render(self, request):
      
        session = get_current_session(request)
        redirect_uri = self._authredirect(request)
        if redirect_uri != None:
            session.return_uri = request.uri
            return redirect(request, redirect_uri)
        else:
            return Resource.render(self, request)

class UISection(UIResource):
    """Class representing a top-level section of the site.

    A top-level section of the site is one that is available on the toolbar
    under the main site banner.  Typically this class will be subclassed
    for each top-level section and an instance of that subclass will be
    registered to show up in the UI with the coreui component
    install_section() method."""

    def __init__(self, component, name, icon="fixmeButtonIcon"):
        """Initialize a top-level section.

        Arguments are:
            name: the name of the section.  This should be a single word
                  and will be used as the text on the toolbar (if shown)
                  and the base URI path for the section.
            icon: uri path to an icon to be shown in the toolbar.  This is
                  not currently used but is very likely to be used in the
                  near future.  If no icon is specified a default one will
                  be used.

        A subclass is free to register additional resources as children
        of itself before and after registering the section with the coreui
        code using the coreui component install_section() method."""
        UIResource.__init__(self, component)
        self.section_name = name
        self.section_icon = icon
        self.redirect_subpath = None

    def set_default_subpath(self, subpath):
        """Specify the default URI subpath under this section

        By default, if the user performs a GET request on the section
        top-level URI, this is the page where the user will be redirected."""
        self.redirect_subpath = subpath

    def redirect_URI(self, request):
        # Subclasses can override this if they want to specify an
        # alternative method of determining the URI to reditect to.
        if self.redirect_subpath != None:
            return request.childLink(self.redirect_subpath)
        else:
            return "/server_error"

    def render_GET(self, request):
        # Subclasses can override this if they have an alternative
        # method of providing data for a GET request on the top-level
        # section URI.
        return redirect(request, self.redirect_URI(request))

class ServerErrRes(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)

    def render_GET(self, request):
        return self.render_tmpl(request, "server_error.mako")

class DeniedRes(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)

    def render_GET(self, request):
        return self.render_tmpl(request, "denied.mako", last_page="")


class LoginRes(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)
        self.coreui           = self.component.resolve(str(coreui.coreui))
        self.directorymanager = self.component.resolve(str(directorymanager))
        if self.directorymanager is None:
            raise Exception("Unable to resolve required component '%s'"
                            %str(directorymanager))

    def render_GET(self, request):
        if not self.directorymanager.supports_authentication():
          uri =  self._return_uri(request,get_current_session(request))
          request.write(redirect(request,uri))
          return

        get_current_session(request).expire()
        return self.render_tmpl(request, "login.mako", login_failed=False, last_page="")

    def _return_uri(self, request, session):
        try:
            return_uri = session.return_uri
            del(session.return_uri)
        except AttributeError, e:
            last_page = urllib.unquote(request.args.get("last_page", [""])[0])
            if last_page not in ("", "/login", "/logout", "/denied", "/server_error"):
                return_uri = last_page
            else:
                return_uri = self.coreui.default_uri
        return return_uri

    def render_POST(self, request):
        if not self.directorymanager.supports_authentication():
          uri =  self._return_uri(request,get_current_session(request))
          request.write(redirect(request,uri))
          return 

        username = request.args["username"][0]
        password = request.args["password"][0]
        d = self.directorymanager.simple_auth(username, password)
        d.addCallback(self._auth_callback, request)
        d.addErrback(self._auth_errback, request)
        return server.NOT_DONE_YET

    def _auth_errback(self, failure, request):
        log.err("Failure during authentication: %s" %failure)
        get_current_session(request).expire()
        request.write(self.render_tmpl(request, "login.mako", login_failed=True, last_page=request.args.get("last_page", [""])[0]))
        request.finish()

    def _auth_callback(self, res, request):
        if res.status == AuthResult.SUCCESS:
            session = get_current_session(request)
            session.user = User(res.username, set(res.nox_roles))
            try:
                session.roles = [Roles.get(r) for r in session.user.role_names]
            except InvalidRoleError, e:
                log.err("Failed to resolve user role: %s" %e)
                request.write(self.render_tmpl(request, "server_error.mako"))
                request.finish()
                return
            if session.user.language != None:
                session.language = session.user.language
            else:
                session.language = self._lang_from_request(request)
            request.write(redirect(request, self._return_uri(request,session)))
        else:
            request.write(self.render_tmpl(request, "login.mako", login_failed=True, last_page=request.args.get("last_page", [""])[0]))
        request.finish()

class LogoutRes(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)

    def render_GET(self, request):
        get_current_session(request).expire()
        return self.render_tmpl(request, "logout.mako", last_page="")


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return authui(ctxt)

    return Factory()
