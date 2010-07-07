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
# Trivial example using reactor timer method to countdown from three
from nox.apps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.apps.coreui.authui import UISection, UIResource, Capabilities
from nox.apps.coreui import coreui

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
        self.coreui = None

    def configure(self, configuration):
        for param in configuration['arguments']:
            if param == 'hidden':
                self.hidden = True

    def install(self):
        Capabilities.register("viewdb", "Browse raw DB tables.", [])
        Capabilities.register("updatedb", "Update raw DB tables.", [])
        self.coreui = self.resolve(str(coreui.coreui))
        self.coreui.install_section(DBExplorerSec(self, persistent=True), self.hidden)
        self.coreui.install_section(DBExplorerSec(self, persistent=False), self.hidden)

    def getInterface(self):
        return str(dbexplorerui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return dbexplorerui(ctxt)

    return Factory()
