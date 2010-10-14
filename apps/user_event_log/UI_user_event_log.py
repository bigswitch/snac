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

from nox.lib.core     import Component
from nox.apps.storage import Storage
import time
import sys
from twisted.python import log

class UI_user_event_log(Component):
    """Simple UI component for User_Event_Log functionality"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.log = [] 

    def configure(self,configuration):
      pass

    def install(self):
      self.store = self.resolve(Storage)
      self.attempt_trigger_insert() 

    def attempt_trigger_insert(self):
      d = self.store.put_table_trigger("user_event_log", True, self.trigger_callback)
      d.addCallback(self.set_trigger_callback)  
      d.addErrback(self.set_trigger_error) 

    def getInterface(self):
        return str(UI_user_event_log)

    def get_log_slice(self, start_index, end_index):
      return self.log[start_index:end_index] 
  
    def trigger_callback(self, trigger_id, row, reason):
     
      time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(row['ts'])))
      row_tuple = (time_str, row['logid'], row['app'],row['level'],row['msg'])  

      print str(row_tuple) 
      self.log.append(row_tuple) 
    
    def set_trigger_callback(self, res): 
      result , self.trigger_id = res 

      if (result[0] != 0): 
        log.err("put trigger failed: " + str(result[1])) 

    def set_trigger_error(self, err): 
        log.msg("UI_user_event_log failed to connect to table 'user_event_log'")  
        
        # try again in five seconds
        self.post_callback(5, self.attempt_trigger_insert)
        return "" # swallow the error 

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return UI_user_event_log(ctxt)

    return Factory()


