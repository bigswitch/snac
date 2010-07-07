from nox.apps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.apps.coreui.authui import UISection, UIResource, Capabilities, redirect
from nox.apps.user_event_log.UI_user_event_log import UI_user_event_log
from nox.apps.coreui import coreui

class HelpSec(UISection):
    isLeaf = False
    required_capabilities = set([])

    def __init__(self, component):
        UISection.__init__(self, component, "Help", "helpButtonIcon")

    def render_GET(self, request):
        return redirect(request, "/static/nox/ext/apps/snackui/helpui/");

class helpui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None

    def install(self):
        self.coreui = self.resolve(str(coreui.coreui))
        self.coreui.install_section(HelpSec(self))

    def getInterface(self):
        return str(helpui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return helpui(ctxt)

    return Factory()
