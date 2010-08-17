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

from nox.lib.core import *
from nox.apps.storage import TransactionalStorage
from nox.apps.configuration.properties import Properties
import logging

lg = logging.getLogger('simple_config')


# this class is a simple wrapper around the Properties class
# so that people can read/write CDB properties values without
# having to deal with all of the transactional clunkiness of 
# the properties interface
class simple_config(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.storage = None

    # Sets a collection of property values within a single section. 
    # of the PROPERTIES table in CDB.  
    # (Note: if a property already exists within the section and is
    # not specified in 'dict', its values will remain unchanged.  Also,
    # you can add a new key/value pair to a section by including a key in dict
    # that does not correspond to an existing key in that section).
    #
    # section_id - the string name of the section within Properties
    # dict - a dictionary of key value pairs, with keys being strings
    # and values being lists of strings. 
    #
    # Returns a deferred.  Caller should register a callback/errback 
    # to make sure the operation completed successfully.
    # Result passed to callback is None
    def set_config(self,section_id, dict): 
        p = Properties(self.storage,section_id)
        d = p.begin()
        
        def set_values(res):
          for key,value in dict.iteritems():
              if value or value == 0:
                  p[key] = value
              else:
                  # Since the value was None, remove the key-value
                  # pair.
                  try:
                      del p[key]
                  except Exception, e:
                      # Already deleted
                      pass

        d.addCallback(lambda x : p.load())
        d.addCallback(set_values)
        d.addCallback(lambda x : p.commit())
        return d

    # returns (via a deferred) all key values pairs from the section of the 
    # PROPERTIES table identified by 'section_id'.  Return
    # value is a dictionary, with keys of type string and 
    # values that are lists of strings
    # A callback added to the deferred returned by this function will 
    # be called with the dictionary on success. 
    #
    # If update_cb is not None, any time the underlying properties object
    # is changed, update_cb will be called with a new dictionary
    #
    # If defaults are provided, they will be passed on to the underlying
    # properties object on the initial name lookup, and all subsequent
    # trigger updates.
    #
    def get_config(self,section_id,update_cb=None,defaults={}): 
        
        p = Properties(self.storage,section_id,defaults)
        def get_dict(res): 
          dict = p.get_simple_dict()
          if update_cb:
            cb = lambda: self._handle_trigger(section_id,update_cb,defaults)
            p.addCallback(cb)
          return dict

        d = p.begin()
        d.addCallback(lambda x : p.load())
        d.addCallback(lambda x : p.commit())
        d.addCallback(get_dict)
        return d

    # this method just piggy-backs on the main get_config method 
    # in order to retrieve the properties and reregister a trigger for
    # update_cb.  
    def _handle_trigger(self,section_id, update_cb,defaults):
      def err(res):
        lg.error("Error on Properties trigger for section '%s': %s" \
            % (section_id,str(res)))
      def call_update_cb(dict): 
        update_cb(dict)
      d = self.get_config(section_id,update_cb,defaults)
      d.addCallbacks(call_update_cb,err)

        
  # the methods below are for a "capped list", which builds on top of
  # simple config to offer the abstraction of a single list that is 
  # capped at a certain size.  This is useful if a components want to
  # persistenty to persistently remember things, but does not want that
  # list of things to grow infinitely (either because the component never
  # deletes items, or if its is possible that the list would grow very
  # large between before it was cleared) 
    def capped_list_get(self, section_id): 
      def get_list(res): 
        if section_id not in res:
          return [] 
        return res[section_id] 

      d = self.get_config(section_id)
      d.addCallback(get_list)
      return d

    def capped_list_add(self,section_id, new_elem,max_size): 

      def add_elem(list): 
        if len(list) >= max_size: 
          list.pop(0)
        list.append(new_elem)
        return self.set_config(section_id,{section_id : list } ) 

      d = self.capped_list_get(section_id)
      d.addCallback(add_elem) 
      return d

    def capped_list_remove(self,section_id,to_remove): 
      def remove_elem(list):
        try : 
          list.remove(to_remove) 
          return self.set_config(section_id,{section_id : list } ) 
        except : 
          pass # ignore

      d = self.capped_list_get(section_id)
      d.addCallback(add_elem) 
      return d
    
    def capped_list_clear(self,section_id): 
      return self.set_config(section_id, {})


    def install(self):
        self.storage = self.resolve(TransactionalStorage)

    def getInterface(self):
        return str(simple_config)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return simple_config(ctxt)

    return Factory()
