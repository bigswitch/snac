
from nox.lib.core     import Component
from nox.ext.apps.ndb     import API, GetOp, PutOp 
from nox.ext.apps.ndb.ndb_utils import *
from twisted.python import log
import time

class NDBComponent(Component):
    """Abstract class for components that log network data to NDB"""

    def __init__(self, ctxt, name):
        Component.__init__(self, ctxt, name)
        self.ndb = self.resolve(API)
        self.cache = {}  # cache of recently seen entries
        # entries not seen for this period of time will be removed from cache & NDB
        self.timeout_sec = 5 * 60 # default 
        # precision of how frequently we check for time-outs
        self.timer_interval_sec = self.timeout_sec / 10 # default 
        self.debug = False
        self.init_table_info()

    def configure(self,configuration):
      pass

    def install(self):
      if(self.debug):
        log.msg("Creating Table %s " % self.table_name, system=self.app_name)
      ndb_setup(self.ndb, self.table_name, self.table_dict, self.app_name, self.db_init_finished) 

    def getInterface(self):
        return str(NDBComponent) 
  
    def db_init_finished(self, x):
      self.register_for_packet_in(self.packet_in_callback)
      self.post_callback(self.timer_interval_sec, self.timer_callback)

    def update_entry(self, dict): 
      key = self.dict_to_key(dict)
      cur_time = time.time() 
      if not key in self.cache:
        if(self.debug):
          log.msg("new entry: %s (t = %f )" % (key,cur_time), system=self.app_name)
        ndb_add(self.ndb, self.table_name, dict, None, self.app_name) 
      self.cache[key] = cur_time

    def timer_callback(self):
      cur_time = time.time()
      for key, ts in self.cache.items():
        if(ts + self.timeout_sec < cur_time): 
          del self.cache[key] 
          ndb_remove(self.ndb, self.table_name, self.key_to_dict(key),None, self.app_name)  
          if(self.debug):
            log.dbg("entry timed-out: %s (cur-time = %f)" % (key,cur_time), system=self.app_name)
      self.post_callback(self.timer_interval_sec, self.timer_callback)

    def dump_cache(self): 
      for key, ts in self.cache.items():
          log.msg("key = %s  t = %f" % (key, ts), system=self.app_name)

    def packet_in_callback(self, dpid, inport, reason, len, bufid, packet) : 
        raise Exception, "NDBComponent class must implement packet_in_callback" 

    def init_table_info(self):
        raise Exception, "NDBComponent class must implement init_table_info" 

    def dict_to_key(self, dict):
        raise Exception, "NDBComponent class must implement dict_to_key" 

    def key_to_dict(self, key):
        raise Exception, "NDBComponent class must implement key_to_dict" 

