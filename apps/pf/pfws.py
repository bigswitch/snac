
import logging
import traceback
import simplejson 

from time import strftime
from nox.lib.core import *
from nox.lib.directory import *
from nox.webapps.webservice      import webservice
from nox.webapps.webservice.webservice import json_parse_message_body
from nox.webapps.webservice.webservice import NOT_DONE_YET,WSPathArbitraryString 
from nox.lib.netinet.netinet import *
#from nox.netapps.authenticator.pyauth import Host_event
from nox.ext.apps.directory.directorymanager import *
from nox.ext.apps.directory.directorymanagerws import *
from nox.coreapps.pyrt.pycomponent import CONTINUE 
from nox.ext.apps.directory.pydirmanager import Principal_name_event
from nox.lib.directory import Directory
from nox.ext.apps.configuration.simple_config import simple_config
from nox.netapps.bindings_storage.bindings_directory import *
from nox.ext.apps.pf.pypf import PyPF, pf_results

lg = logging.getLogger('pfws')

class pfws(Component):
    """Web service to expose os fingerprints recorded for a host"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
    
    def _get_all_fingerprints(self, request, arg):
          all_fps = self.pypf.get_all_fingerprints()
          request.write(simplejson.dumps(all_fps))
          request.finish()
          return NOT_DONE_YET
      
    def _get_fingerprints(self, request, arg):
        try :
          name = arg['<principal name>']
          dirname = arg['<dir name>']
          mangled_name = mangle_name(dirname,name)
          def interfaces_cb(res): 
            mac_ip_list = [] 
            for iface in res: 
              mac_ip_list.append((iface['dladdr'],iface['nwaddr'])) 
            return mac_ip_list
          def fp_lookup_cb(res):
            ret_map = {} 
            for mac_str,ip_str in res: 
              if ip_str in ret_map: 
                continue # host may be on multiple locations
              rs = pf_results()
              is_valid = self.pypf.get_fingerprints(\
                  create_eaddr(mac_str),create_ipaddr(ip_str),rs)
              if is_valid and rs.bpf.os != "": 
                  ret_map[ip_str] = rs.bpf.os
            request.write(simplejson.dumps({ "fingerprints" : ret_map}))
            request.finish()

          d = self.bindings_dir.get_interfaces_for_host(mangled_name) 
          d.addCallback(interfaces_cb)
          d.addCallback(fp_lookup_cb)
        except Exception , e : 
          traceback.print_exc()
          return webservice.internalError(request, str(e)) 

        return NOT_DONE_YET

    def install(self):
        dm = self.resolve(directorymanager)
        self.bindings_dir = self.resolve(BindingsDirectory) 
        self.pypf = self.resolve(PyPF) 
        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        #GET /ws.v1/host/<dir name>/<principal name>/os_fingerprint
        path = ( webservice.WSPathStaticString("host"), ) + \
                         (WSPathExistingDirName(dm, "<dir name>"),) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("os_fingerprint"),)

        reg(self._get_fingerprints, "GET", path,
            """Returns all OS fingerprints seen for this active host, grouped by IP address""")
        
        #GET /ws.v1/debug/os_fingerprint
        path = ( webservice.WSPathStaticString("debug"), ) + \
                         (webservice.WSPathStaticString("os_fingerprint"),)

        reg(self._get_all_fingerprints, "GET", path,
            """Returns all OS fingerprints currently known by the system""")
    
    
    def getInterface(self):
        return str(pfws)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return pfws(ctxt)
    return Factory()
