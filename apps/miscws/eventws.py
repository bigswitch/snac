
import logging
import traceback

from nox.lib.core import *
from nox.lib.directory import *
from nox.webapps.webservice      import webservice
from nox.webapps.webservice.webservice import json_parse_message_body
from nox.webapps.webservice.webservice import NOT_DONE_YET,WSPathArbitraryString 
from nox.lib.netinet.netinet import *
from nox.netapps.authenticator.pyauth import Host_auth_event, PyAuth
from nox.netapps.bindings_storage.pybindings_storage import pybindings_storage
from nox.ext.apps.directory.directorymanager import *
from nox.ext.apps.directory.directorymanagerws import *

lg = logging.getLogger('eventws')

class eventws(Component):
    """Web service for generating events (intended for TESTING/DEBUG only)"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    # create an auth event.  request body should have a
    # subset of the following fields
    # 'type' - "authenticate" or "deauthenticate"
    # 'dpid' - string of datapath id
    # 'port' - int of port 
    # 'dladdr' - string of ethernet adddress
    # 'nwaddr' - string of IP address 
    # 'hostname' - string of host being bound
    # 'username' - string of user being bound
    def _do_auth_event(self, request, arg):
        content = json_parse_message_body(request)
       
        try : 
          type = Host_auth_event.AUTHENTICATE
          if "type" in content and content["type"] == "deauthenticate": 
            type = Host_auth_event.DEAUTHENTICATE
          ni = NetInfo.from_str_dict(content)
          hostname =str(content.get("hostname", self._auth.get_unknown_name()))  
          username =str(content.get("username", self._auth.get_unknown_name())) 

          ae = Host_auth_event(type, ni.dpid, ni.port, ni.dladdr,ni.nwaddr,False, 
                          hostname, username, 0, 0)
          self.post(ae) 
          return "[]" 
        except Exception , e : 
          traceback.print_exc()
          return webservice.badRequest(request, str(e)) 

    # exposes a simple webservice that takes an active username 
    # and deauthenticates that user
    def _do_user_deauth(self, request, arg):
        

        try:
          dirname = arg['<dir name>'] 
          name = arg['<principal name>']
          mangled_name = mangle_name(dirname,name)
        
          def cb(entity_list):
              if len(entity_list) == 0: 
                msg = "User '%s' is not currently authenticated. No entries removed." % \
                    (mangled_name)
                request.write(simplejson.dumps(msg))
                request.finish()
                return 

              for e in entity_list:
                dpid = datapathid.from_host(e[0])
                port = e[1]
                dladdr = ethernetaddr(e[2])
                nwaddr = e[3] 
                hostname = Authenticator.get_unknown_name()
                username = mangled_name 
                ae = Host_auth_event(Host_auth_event.DEAUTHENTICATE, dpid,
                        port, dladdr,nwaddr, False, hostname,
                        username, 0, 0)
                self.post(ae) 
                
              msg = "successfully removed %s user entries for '%s'" % \
                    (len(entity_list), mangled_name)
              request.write(simplejson.dumps(msg))
              request.finish()

          self.bs.get_entities_by_name(mangled_name,Name.USER,cb)
          return NOT_DONE_YET

        except Exception, e: 
          traceback.print_exc() 
          return webservice.badRequest(request,"Invalid URL parameters: %s" % e)
    

    def install(self):
        self._auth = self.resolve(PyAuth)
        dm = self.resolve(directorymanager)

        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        #PUT /ws.v1/debug/event/auth
        autheventpath    = ( webservice.WSPathStaticString("debug"), ) + \
                          ( webservice.WSPathStaticString("event"), ) +  \
                          ( webservice.WSPathStaticString("auth"), ); 
        reg(self._do_auth_event, "PUT", autheventpath,
            """Spawn an Auth event.""")
        
        # code below is for spawning a user-deauth from the UI 
        self.bs = self.resolve(pybindings_storage)
        path = ( webservice.WSPathStaticString("user"), ) + \
                         (WSPathExistingDirName(dm, "<dir name>") ,) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("deauth"),)
        desc = "Deauthenticate the named user"
        reg(self._do_user_deauth, "GET", path, desc)


    def getInterface(self):
        return str(eventws)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return eventws(ctxt)
    return Factory()
