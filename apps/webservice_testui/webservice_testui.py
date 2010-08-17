"""Test client for webservice implementations."""

from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.webapps.coreui.authui import UISection, UIResource, Capabilities
from nox.webapps.coreui import coreui

class WebServiceTestSec(UISection):
    isLeaf = True

    def __init__(self, component):
        UISection.__init__(self, component, "WebServiceTest")

    def render_GET(self, request):
        return self.render_tmpl(request, "wstest.mako")

class webservice_testui(Component):

    hidden = False

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None

    def configure(self, configuration):
        for param in configuration['arguments']:
            if param == 'hidden':
                self.hidden = True

    def install(self):
        self.coreui = self.resolve(str(coreui.coreui))
        self.coreui.install_section(WebServiceTestSec(self), self.hidden)

    def getInterface(self):
        return str(webservice_testui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return webservice_testui(ctxt)

    return Factory()
