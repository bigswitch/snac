from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.ext.apps.coreui.authui import UISection
from nox.webapps.webserver.webauth import Capabilities
from nox.webapps.webserver.webserver import redirect

from nox.ext.apps.restracker.pyrestracker import pyrestracker

class ResTrackerDebugSec(UISection): 
    isLeaf = True

    def __init__(self, component):
        UISection.__init__(self, component, "ResTrackerDebug")
        self.rt = component.resolve(str(pyrestracker))

    def render_GET(self, request):
      return self.render_tmpl(request, "restrackerdebug.mako",rt=self.rt)

class restrackerui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.webserver = None

    def install(self):
        # Capabilities.register("viewpolicy", "View policy configuration.",
        #                       ["Policy Administrator",
        #                        "Network Operator",
        #                        "Security Operator",
        #                        "Viewer"])
        self.webserver = self.resolve(str(webserver.webserver))
        
        self.webserver.install_section(ResTrackerDebugSec(self), True) # always hidden

    def getInterface(self):
        return str(restrackerui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return restrackerui(ctxt)

    return Factory()
