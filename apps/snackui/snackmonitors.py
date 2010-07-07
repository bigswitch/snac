import sys

from nox.apps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.apps.coreui.authui import UISection, UIResource, Capabilities
from nox.apps.user_event_log.UI_user_event_log import UI_user_event_log
from nox.apps.coreui import coreui

from nox.apps.coreui.monitorsui import monitorsui, SimpleTemplateMonitor
from nox.ext.apps.snackui.principal_list_pages import *
from nox.ext.apps.snackui.search import SearchRes
from nox.ext.apps.snackui.flow_table_page import FlowTableRes,HostFlowSummaryRes

class snackmonitors(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.monitorsui = self.resolve(str(monitorsui))

    def bootstrap_complete_callback(self, *args):
        self.monitorsui.uisection.set_default_subpath("NetworkOverview")
        return CONTINUE

    def install(self):
        self.register_for_bootstrap_complete(self.bootstrap_complete_callback)
        monitors = self.monitorsui.monitors
        r = monitors.register
        r(SimpleTemplateMonitor("NetworkOverview", "Network Overview",
                                100, self,
                                set(["viewmonitors"]),
                                "NetworkOverview.mako"));
        r(SimpleTemplateMonitor("Hosts", "Hosts", 300,
                                self, set(["viewmonitors"]),
                                "principallist_wrapper.mako", 
                                ptype="Hosts"))        
        r(SimpleResourceMonitor("HostslistOnly", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                HostListRes(self,set(["viewmonitors"]))))
        r(SimpleTemplateMonitor("Switches", "Switches", 200, 
                                self, set(["viewmonitors"]),
                                "principallist_wrapper.mako", 
                                ptype="Switches"))        
        r(SimpleResourceMonitor("SwitcheslistOnly", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                SwitchListRes(self,set(["viewmonitors"]))))
        r(SimpleTemplateMonitor("SwitchInfo", None, sys.maxint,
                                self, set(["viewmonitors"]),
                                "SwitchInfoMon.mako",
                                monitors.get("Switches")))
        r(SimpleTemplateMonitor("SwitchPortInfo", None, sys.maxint,
                                self, set(["viewmonitors"]),
                                "SwitchPortInfoMon.mako",
                                monitors.get("Switches")))        
        r(SimpleTemplateMonitor("HostInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "HostInfo.mako",
                                monitors.get("Hosts")));
        r(SimpleTemplateMonitor("Users", "Users", 400, 
                                self, set(["viewmonitors"]),
                                "principallist_wrapper.mako", 
                                ptype="Users"))        
        r(SimpleResourceMonitor("UserslistOnly", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                PrincipalListRes("user", self, 
                                    set(["viewmonitors"]))));
        r(SimpleTemplateMonitor("UserInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "UserInfo.mako",
                                monitors.get("Users")));
        r(SimpleTemplateMonitor("Locations", "Locations", 500, 
                                self, set(["viewmonitors"]),
                                "principallist_wrapper.mako", 
                                ptype="Locations"))        
        r(SimpleResourceMonitor("LocationslistOnly", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                LocationListRes(self,set(["viewmonitors"]))))
        r(SimpleTemplateMonitor("Groups", "Groups",
                                600, self,
                                set(["viewmonitors"]),
                                "Groups.mako"));
        r(SimpleTemplateMonitor("HostGroups", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "HostGroups.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("HostGroupInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "HostGroupInfo.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("UserGroups", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "UserGroups.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("UserGroupInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "UserGroupInfo.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("SwitchGroups", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "SwitchGroups.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("SwitchGroupInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "SwitchGroupInfo.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("LocationGroups", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "LocationGroups.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("LocationGroupInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "LocationGroupInfo.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("NWAddrGroups", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "NWAddrGroups.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("NWAddrGroupInfo", None,
                                sys.maxint, self,
                                set(["viewmonitors"]),
                                "NWAddrGroupInfo.mako",
                                monitors.get("Groups")));
        r(SimpleTemplateMonitor("NetworkEventsLog", "Network Events Log",
                                700, self,
                                set(["viewmonitors"]),
                                "NetEventsMon.mako"));
        r(SimpleResourceMonitor("Search", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                SearchRes(self,set(["viewmonitors"]))))
        r(SimpleResourceMonitor("FlowHistory", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                FlowTableRes(self,set(["viewmonitors"]))))
        r(SimpleResourceMonitor("HostFlowSummary", None, sys.maxint, 
                                self, set(["viewmonitors"]),
                                HostFlowSummaryRes(self,set(["viewmonitors"]))))


    def getInterface(self):
        return str(snackmonitors)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return snackmonitors(ctxt)

    return Factory()
