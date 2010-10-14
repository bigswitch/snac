
from nox.lib.core import *
from nox.ext.apps.coreui.authui import UISection, UIResource, Capabilities
from nox.ext.apps.coreui.authui import redirect, get_current_session
from nox.ext.apps.coreui.monitorsui import *

class SearchRes(MonitorResource): 
    
    def __init__(self, component,capabilities):
        UIResource.__init__(self, component)
        # maps from 'subset' param value to the 
        # page and parameter string we need to use for
        # redirection
        self.subset_map = { "Host Names" : ("Hosts","name_glob"), 
                           "Host IPs" : ("Hosts","nwaddr_glob"), 
                           "Host MACs" : ("Hosts","dladdr_glob"), 
                           "Host Locations" : ("Hosts","location_name_glob"), 
                           "User Names" : ("Users","name_glob"), 
                           "Switch Names" : ("Switches","name_glob"), 
                           "Location Names" : ("Locations","name_glob")
                           }

    def invalid_search(self,msg):
      return "<h3> Invalid Search Parameters: </h3>"

    def render_GET(self, request):
        if "subset" not in request.args: 
            return self.invalid_search("no 'subset' parameter")
        if "search" not in request.args: 
            return self.invalid_search("no 'search' parameter")
        subset = request.args["subset"][-1]
        if subset not in self.subset_map: 
            return self.invalid_search("'%s' is not a value subset parameter" \
                % subset)
        page, param = self.subset_map[subset]

        # save selected search type in session 
        session = get_current_session(request) 
        session.selected_search_type = subset

        search = request.args["search"][-1]
        if len(search) == 0: 
          search = '*'
        elif search[0] != '*' and search[-1] != '*':
            search = "*" + search + "*"
        return redirect(request, '/Monitors/%s?%s=%s' % (page,param,search))
