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

import logging
from nox.lib.core import *

import nox.lib.openflow as openflow
from nox.lib.packet.packet_utils  import mac_to_str

from nox.lib.netinet.netinet import datapathid, c_ntohl, c_htonl
from nox.netapps.directory.directorymanager import directorymanager
from nox.lib.directory import Directory
from nox.netapps.configuration.simple_config import simple_config
from twisted.python import log
from nox.netapps.switchstats.switchstats    import switchstats
from nox.netapps.directory.pydirmanager import Principal_name_event

lg = logging.getLogger('switchconfig')

U32_ALL = 0xffffffff

class switchconfig(Component):
    """Handle configuration of switches via the UI"""
  

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.simple_config = None
        self.nat_config = None
        self.dpid_to_name = {} 

    # on switch rename, rewrite all nat_config keys from 
    # oldname to newname 
    #
    # on switch delete, remove all nat_config keys for that
    # switch, so that a new switch with the same name does not
    # get stale config
    #
    # NOTE: we do not make changes to self.nat_config directly.
    # we write changes to CDB, then get notified by the listener
    # which in turn updates self.nat_config
    def handle_principal_name_event(self,event):

      if event.type != Directory.LOCATION_PRINCIPAL: 
        return CONTINUE
       
      if event.oldname in self.nat_config: 
        to_change = { event.oldname : [] } 
        if event.newname != "": 
          to_change[event.newname] = self.nat_config[event.oldname] 
        self.simple_config.set_config("switch_nat_config",to_change)
      return CONTINUE

    # generic helper function for querying directories
    # returns a deferred, which is called with a list
    # of locations. If port is not None, this list 
    # will be of size 1, containing the location corresponding
    # to dpid,port.  Otherwise, it returns all locations associated
    # with that dpid. 
    def do_location_lookup(self, dpid, port): 
      def err(res): 
        lg.error("error on directory query: %s" % str(res))
      
      def ok(loc_names):
        if(len(loc_names) == 0): 
          lg.error("couldn't find loc name for dp = %s port = %s" \
              % (dpid,port))
        return loc_names

      query_dict = {"dpid" : datapathid.from_host(dpid) }
      if port != None: 
        query_dict["port"] = port
      d = self.dm.search_principals(Directory.LOCATION_PRINCIPAL, query_dict)
      d.addErrback(err)
      return d

    # helper fn to handle when one or more locs join
    # 'loc_names' is a list of locations that have joined
    def handle_loc_joins(self,loc_names): 
        for loc in loc_names: 
          if loc in self.nat_config: 
            self.handle_change(loc,self.nat_config[loc])
      

    def dp_join(self, dpid, attrs):
      if self.nat_config == None: 
        lg.error("switchconfig uninitialized on dp_join")
        return CONTINUE 
      
      # get all location names for this switch 
      d = self.do_location_lookup(dpid, None) 
      d.addCallbacks(self.handle_loc_joins)
      return CONTINUE

    def port_status(self, dpid, reason, port):
      if reason != 0: 
        return # only interested in ADDED ports
      
      if self.nat_config == None: 
        lg.error("switchconfig uninitialized on port_status")
        return CONTINUE 
      
      # get all location names for this switch 
      d = self.do_location_lookup(dpid, None) 
      d.addCallbacks(self.handle_loc_joins)
      return CONTINUE 

    # this method is called each time we are alerted via
    # a trigger that the switch_nat_config has changed. 
    # We cycle through the new values, comparing them to the
    # old ones and call self.handle_change() for each . 
    def handle_nat_config_update(self, new_props):
      old_config = self.nat_config
      self.nat_config = new_props

      # if this is not our first fetch, find out what changed 
      # and push updates to switches 
      if old_config is not None: 
        changes = {}
        for new_key, new_params in self.nat_config.iteritems():
          if new_key not in old_config: 
            changes[new_key] = new_params # new location
          elif old_config[new_key] != new_params: 
            changes[new_key] = new_params # new params, old location

        for switchport in old_config.keys():
          if not switchport in new_props: 
            changes[switchport] = [] # nat disabled

        for port_name, params in changes.iteritems(): 
          self.handle_change(port_name, params)


    # the configuration has changed for location 'loc_name'
    # do a directory lookup on the name to find the dpid and 
    # port number needed to send a message to the switch to let it know
    def handle_change(self,loc_name, params): 

      def err(res): 
        lg.error("error on directory query: %s" % str(res))
      def ok(loc_info):
        if(loc_info is None): 
          if (params != []): 
            lg.error("nat change for unknown location '%s'" % loc_name)
          return
        self.send_change(loc_info.dpid.as_host(),loc_info.port,params)

      d = self.dm.get_principal(Directory.LOCATION_PRINCIPAL,loc_name)
      d.addCallbacks(ok, err) 

    # actually send a single change to a switch 
    def send_change(self,dpid_int, port_no, str_params): 
      if(len(str_params) == 0): 
        ret = self.ctxt.send_del_snat(dpid_int,port_no)
      else:
        external_prefix_arr = str_params[0].split("/")
        ip_start = c_ntohl(create_ipaddr(str(external_prefix_arr[0])).addr)
        if len(external_prefix_arr) > 1: 
          # this is a prefix, not a single IP address
          prefix_len = int(external_prefix_arr[1]) 
          ip_start = ip_start & (U32_ALL << (32 - prefix_len)) 
          ip_end = ip_start | (U32_ALL >> prefix_len)
        else: 
          ip_end = ip_start
      
        mac_str = str_params[4]
        if mac_str == "": 
          mac_str = u"00:00:00:00:00:00"
        mac_addr = create_eaddr(mac_str.encode('utf-8'))

        # for now, the UI does not set restrictions on the 
        # external ports used. 
        tcp_start = 0
        tcp_end = 0
        udp_start = 0
        udp_end = 0

        ret = self.ctxt.send_add_snat(dpid_int,port_no,
            ip_start,ip_end,tcp_start,tcp_end,udp_start,udp_end,mac_addr)

      if(ret): 
        lg.error("add/delete cmd snat failed with code = %s" % ret)

    def install(self):

        self.dm = self.resolve(directorymanager)
        
        # temporarily need switchstats until port names
        # are stored in the directory
        self.switchstats = self.resolve(switchstats)

        self.register_for_datapath_join (self.dp_join)
        self.register_for_port_status(self.port_status)
       
        self.register_handler(Principal_name_event.static_get_name(),
                              self.handle_principal_name_event)
        # must listen for switch rename, delete

        self.simple_config = self.resolve(simple_config)
        d = self.simple_config.get_config("switch_nat_config",
                              self.handle_nat_config_update) 
        d.addCallback(self.handle_nat_config_update) #initial load
        return d


    def getInterface(self):
        return str(switchconfig)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return switchconfig(ctxt)

    return Factory()
