from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *
from nox.webapps.webserver import webserver

from nox.ext.apps.coreui.authui import UISection
from nox.webapps.webserver.webauth import Capabilities

class DBExplorerSec(UISection):
    isLeaf = False
    required_capabilities = set([ "viewdb" ])

    def __init__(self, component, persistent):
        if persistent:
            self.dbname = "cdb"
        else:
            self.dbname = "ndb"
        UISection.__init__(self, component, self.dbname.upper()+"Explorer")

    def render_GET(self, request):
        return self.render_tmpl(request, "dbexplorer.mako", dbname=self.dbname)

class dbexplorerui(Component):

    hidden = False

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.webserver = None

    def configure(self, configuration):
        for param in configuration['arguments']:
            if param == 'hidden':
                self.hidden = True

    def install(self):
        Capabilities.register("viewdb", "Browse raw DB tables.", [])
        Capabilities.register("updatedb", "Update raw DB tables.", [])
        self.webserver = self.resolve(str(webserver.webserver))
        self.webserver.install_section(DBExplorerSec(self, persistent=True), self.hidden)
        self.webserver.install_section(DBExplorerSec(self, persistent=False), self.hidden)

    def getInterface(self):
        return str(dbexplorerui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return dbexplorerui(ctxt)

    return Factory()
