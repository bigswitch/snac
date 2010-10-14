
import logging
import traceback
import simplejson 

from time import strftime
from nox.lib.core import *
from nox.lib.directory import *
from nox.webapps.webservice  import webservice
from nox.webapps.webservice.webservice import json_parse_message_body
from nox.webapps.webservice.webservice import NOT_DONE_YET,WSPathArbitraryString 
from nox.lib.netinet.netinet import *
from nox.netapps.authenticator.pyauth import Host_join_event
from nox.ext.apps.directory.directorymanager import *
from nox.ext.apps.directory.directorymanagerws import *
from nox.coreapps.pyrt.pycomponent import CONTINUE 
from nox.ext.apps.directory.pydirmanager import Principal_name_event
from nox.lib.directory import Directory
from nox.ext.apps.configuration.simple_config import simple_config

PERIODIC_SAVE_INTERVAL = 60 # save every minute, if changes exist

lg = logging.getLogger('hosttrackerws')

# NOTE: this is a 'throw-away' component that is only 
# necessary because we do not have data ware-housing working right now.
# As a result, I am not writing it in a particularly robust/scalable fashion.
class hosttrackerws(Component):
    """Web service to expose when hosts were last seen on the network"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.data = {} 
        self.refcounts = {} 
        self.no_changes = True

    def _get_time_str(self): 
        return strftime("%I:%M %p on %m-%d-%Y") 

    def _get_last_seen_str(self, request, arg):
        try :
          name = arg['<principal name>']
          dirname = arg['<dir name>']
          mangled_name = mangle_name(dirname,name)
          if mangled_name in self.data:
            text = self.data[mangled_name]
          else: 
            text = ""
          return simplejson.dumps({ "lastSeen" : text }) 
        except Exception , e : 
          traceback.print_exc()
          return webservice.internalError(request, str(e)) 

    def host_event(self, event):
      dir,pname = demangle_name(event.name)

      if(event.action == Host_join_event.JOIN):
          
        self.data[event.name] = "Active since " + self._get_time_str()
        if event.name not in self.refcounts:
          self.refcounts[event.name] = 0
        self.refcounts[event.name] += 1

      else: # Host_join_event.LEAVE
        
        if event.name in self.refcounts:
          self.refcounts[event.name] -= 1
          if self.refcounts[event.name] == 0:
            # all instances of this host have left the network
            del self.refcounts[event.name]
            if dir == "discovered": 
              # don't keep persistent state if a host in 
              # 'discovered' directory leaves the network
              del self.data[event.name]
            else: 
              self.data[event.name] = "Left network at " + self._get_time_str()
            self.no_changes = False
            #print "New data: %s" % self.data

      return CONTINUE 

    def principal_name_event(self, event): 
      if event.type == Directory.HOST_PRINCIPAL and \
          event.oldname in self.data: 
            if event.newname != "":
              self.data[event.newname] = self.data[event.oldname]
            del self.data[event.oldname]
            #print "New data: %s" % self.data
            self.no_changes = False
      return CONTINUE 

    def install(self):
        dm = self.resolve(directorymanager)

        self.register_handler(Host_join_event.static_get_name(), self.host_event)
        self.register_handler(Principal_name_event.static_get_name(), 
                              self.principal_name_event)
        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        #GET /ws.v1/host/<dir name>/<principal name>/last_seen
        path = ( webservice.WSPathStaticString("host"), ) + \
                         (WSPathExistingDirName(dm, "<dir name>"),) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("last_seen"),)

        reg(self._get_last_seen_str, "GET", path,
            """Get string indicated the last time this host was seen on the network.""")
    
        # we persistently store data in simple_config, so we don't 
        # lose all data if nox is restarted
        self.simple_config = self.resolve(simple_config)
        d = self.simple_config.get_config("hosttrackerws") 
        d.addCallback(self.load_from_config) #initial load
        self.post_callback(PERIODIC_SAVE_INTERVAL,self.periodic_save)

    def load_from_config(self, props):
        if "values" not in props:
          return # nothing has been saved yet
        all_values = props["values"]
        all_keys = props["keys"]
        for i in xrange(0, len(all_values)): 
          self.data[all_keys[i]] = all_values[i]
        #print "Loaded data: %s" % self.data

    def periodic_save(self): 
        self.post_callback(PERIODIC_SAVE_INTERVAL,self.periodic_save)
        if self.no_changes:
          return 

        all_keys = [] 
        all_values = [] 
        for key,value in self.data.iteritems():

            dir,pname = demangle_name(key)
            if dir == "discovered": 
              continue # don't persist discovered names 

            # saved data is only used if nox is restarted, thus
            # no one is actually saved as 'active' 
            all_values.append(value.replace("Active since ", "Left network at "))
            all_keys.append(key)
        to_save = { "values" : all_values, "keys" : all_keys } 
        self.simple_config.set_config("hosttrackerws",to_save)
        self.no_changes = True 
        #print "saved data: %s" % to_save

    def getInterface(self):
        return str(hosttrackerws)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return hosttrackerws(ctxt)
    return Factory()
