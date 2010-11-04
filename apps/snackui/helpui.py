from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.webapps.webserver import webserver
from nox.ext.apps.coreui.authui import UISection
from nox.ext.apps.user_event_log.UI_user_event_log import UI_user_event_log

class HelpSec(UISection):
    isLeaf = False
    required_capabilities = set([])

    def __init__(self, component):
        UISection.__init__(self, component, "Help", "helpButtonIcon")

    def render_GET(self, request):
        return webserver.redirect(request, "/static/nox/ext/apps/snackui/helpui/");

class helpui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.webserver = None

    def install(self):
        self.webserver = self.resolve(str(webserver.webserver))
        self.webserver.install_section(HelpSec(self))

    def getInterface(self):
        return str(helpui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return helpui(ctxt)

    return Factory()
