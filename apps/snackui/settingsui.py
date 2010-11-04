from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.ext.apps.coreui.authui import UISection, UIResource
from nox.webapps.webserver.webauth import Capabilities
from nox.webapps.webserver import webserver
from nox.ext.apps.user_event_log.UI_user_event_log import UI_user_event_log

class ControllerRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "controller.mako")

class DirectoriesRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "directories.mako")

class DirectoryInfoRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "DirectoryInfo.mako")

class CaptivePortalRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "captiveportal.mako")

class DhcpRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "dhcp.mako")

class LogRes(UIResource):
    required_capabilities = set([ "viewsettings" ] )

    def render_GET(self, request):
        return self.render_tmpl(request, "log.mako")

class SettingsSec(UISection):
    isLeaf = False
    required_capabilities = set([ "viewsettings" ])

    def __init__(self, component):
        UISection.__init__(self, component, "Settings", "settingsButtonIcon")
        self.putChild("Controller", ControllerRes(self.component))
        dirRes = DirectoriesRes(self.component)
        self.putChild("Directories", dirRes)
        dirRes.putChild("DirectoryInfo", DirectoryInfoRes(self.component))
        self.putChild("CaptivePortal", CaptivePortalRes(self.component))
        self.putChild("DHCP", DhcpRes(self.component))
        self.putChild("Logs", LogRes(self.component))

    def render_GET(self, request):
        return webserver.redirect(request, request.childLink('Controller'))

class settingsui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.webserver = None

    def install(self):
        Capabilities.register("viewsettings", "View configuration settings.",
                              ["Admin","Demo","Readonly"])
                              #["Policy Administrator", "Network Operator", "Security Operator", "Viewer"])
        self.webserver = self.resolve(str(webserver.webserver))
        self.webserver.install_section(SettingsSec(self))

    def getInterface(self):
        return str(settingsui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return settingsui(ctxt)

    return Factory()
