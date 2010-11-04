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
import sys

from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *
from nox.webapps.webserver import webserver

from authui import UISection, UIResource
from nox.webapps.webserver.webauth import Capabilities
from nox.webapps.webserver.webserver import redirect

from nox.lib.registries import InstanceRegistry
import coreui

class MonitorsSec(UISection):
    isLeaf = False
    required_capabilities = set([ "viewmonitors" ])

    def __init__(self, component):
        UISection.__init__(self, component, "Monitors", "monitorsButtonIcon")

class Monitor:
    """Base class for monitors."""

    def __init__(self, id, name, priority, component, required_capabilities, parent=None):
            """id: identifier for monitor. Should be short and will be the
                   same no matter the language of the user.
               name:  name for monitor.  For presentation to the user.
                   Will be translated.  If not specified, will not be
                   listed in the monitors section sidebar
               priority: priority for listing in sidebar
               component: component instantiating this monitor.
               required_capabilities: capabilities required to use
                   this monitor.
               parent: for hierarchical monitors, the parent monitors of this one."""
            self.id = id
            self.name = name
            self.priority = priority
            self.component = component
            self.required_capabilties = required_capabilities
            self.parent = parent

    def getUIResource(self):
        """Return a UIResource subclass tree for HTTP retrieval."""
        raise NotImplementedError("Monitor subclasses must implement getUIResource.")

class MonitorsRegistry(InstanceRegistry):
    def __init__(self):
        InstanceRegistry.__init__(self, Monitor)

    def register(self, m):
        InstanceRegistry.register(self, m.id, m)

    def list(self, reverse=False):
        return InstanceRegistry.list(self, sort_key=lambda i: i.priority, sort_reverse=reverse)

MonitorsRegistry = MonitorsRegistry()

class monitorsui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.webserver = None
        self.monitors = MonitorsRegistry

    def bootstrap_complete_callback(self, *args):
        for mname in self.monitors:
            m = self.monitors[mname]
            if m.parent == None:
                p = self.uisection
            else:
                p = m.parent.getUIResource()
            p.putChild(m.id, m.getUIResource())
        return CONTINUE

    def install(self):
        Capabilities.register("viewmonitors", "View realtime monitors.",
            #["Policy Administrator", "Network Operator", "Security Operator", "Viewer"])
            ["Admin","Demo","Readonly"])
        self.uisection = MonitorsSec(self)
        self.webserver = self.resolve(str(webserver.webserver))
        self.webserver.install_section(self.uisection)

        self.register_for_bootstrap_complete(self.bootstrap_complete_callback)
        r = self.monitors.register
        # TBD: - Define a "TemplateTree" monitor so don't have to register
        # TBD:   separate monitors for each subpage of a monitor like the
        # TBD:   switch info and switch port details page.

        # NOTE: all monitor page registration has been moved to 
        # ext/apps/snackui/snackmonitors.py

    def getInterface(self):
        return str(monitorsui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return monitorsui(ctxt)

    return Factory()




class MonitorResource(UIResource):
    template_search_path = [ monitorsui, coreui.coreui ]

    def render_tmpl(request, name, *arg, **data):
        return UIResource.render_tmpl(request, name,
                                      MonitorsRegistry=MonitorsRegistry,
                                      *arg, **data)

class SimpleTemplateMonitorRes(MonitorResource):
    isLeaf = False

    def __init__(self, component, capabilities, template, *arg, **data):
        UIResource.__init__(self, component)
        self.required_capabilities = capabilities
        self._template = template
        self.arg = arg
        self.data = data

    def render_GET(self, request):
        return self.render_tmpl(request, self._template, *self.arg, **self.data)

class SimpleResourceMonitor(Monitor):
    def __init__(self, id, name, priority, component, capabilities, monitorResource, parent=None):
        Monitor.__init__(self, id, name, priority, component, capabilities, parent )
        self._res = monitorResource

    def getUIResource(self):
        return self._res

class SimpleTemplateMonitor(SimpleResourceMonitor):
    def __init__(self, id, name, priority, component, capabilities, template, parent=None, *arg, **data):
        SimpleResourceMonitor.__init__(self, id, name, priority, component, capabilities, SimpleTemplateMonitorRes(component, capabilities, template, *arg, **data), parent)

