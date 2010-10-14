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
#

import logging
import simplejson
import copy

from twisted.internet import defer
from twisted.python.failure import Failure
from nox.ext.apps.coreui      import webservice
from nox.ext.apps.coreui.webservice import *
from nox.ext.apps.directory.query import query
from nox.ext.apps.directory.directorymanagerws import *
from nox.ext.apps.directory.directorymanager import mangle_name
from nox.lib.directory import Directory, DirectoryException, CertFingerprintCredential
from nox.lib.directory_factory import Directory_Factory 

lg = logging.getLogger('dm_ws_switch')

# TBD: - Push changes down to switchstats.py so it returns data in
# TBD:   as needed here instead of reworking it.
# TBD: - Make gets for unknown switches return 404
# TBD: - Make gets for known but inactive switches return configured
# TBD:   data and null values for stuff that can only be read from the
# TBD:   switch
# TBD: - ??? Move read-only switch and port attributes from
# TBD:   <basepath>/config into just <basepath>.

class dm_ws_switch:
    """Exposes openflow switch state that does not correspond
    directly to a call in the standard directory interface"""

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def is_active(self, request, arg, switch_info):
        try:
            active = switch_info.dpid.as_host() in self.switchstats.dp_stats
            request.write(simplejson.dumps(active))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "is_active",
                            "Could not retrieve switch active status.")

    def switch_reset(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()
            res = self.dm.switch_reset(dpid)
            request.write(simplejson.dumps(res))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "switch_reset",
                            "Could not reset switch.")

    def send_switch_command(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()
            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request,"Unable to parse message body.")
            if type(content) != type({}):
                return webservice.badRequest(request,"Bad message body, expecting dict.")
            if 'command' not in content:    
                return webservice.badRequest(request,"No 'command' key in put")
            args = []
            if 'args' in content:    
                args = content['args']
            res = self.dm.send_switch_command(dpid, content['command'], args)
            request.write(simplejson.dumps(res))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "send_switch_command",
                            "Sending command failed.")

    def switch_update(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()
            res = self.dm.switch_update(dpid)
            request.write(simplejson.dumps(res))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "switch_update",
                            "Could not update switch.")

    def get_config(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()

            if dpid in self.switchstats.dp_stats:
                config  = copy.copy(self.switchstats.dp_stats[dpid])
                config['dpid'] = dpid
                config['port_stats_poll_period'] = self.switchstats.dp_poll_period[dpid]['port']
                config['table_poll_period'] = self.switchstats.dp_poll_period[dpid]['table']
                config['aggregate_poll_period'] = self.switchstats.dp_poll_period[dpid]['aggr']
                del config["ports"]
            else:
                config = {}
                config['dpid'] = dpid
                config['n_bufs'] = None
                config['n_tables'] = None
                config['caps'] = None
                config['actions'] = None
                config['port_stats_poll_period'] = None
                config['table_poll_period'] = None
                config['aggregate_poll_period'] = None

            request.write(simplejson.dumps(config))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_config",
                            "Could not retrieve switch config.")

    def get_desc(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()

            if dpid in self.switchstats.dp_stats:
                config = copy.copy(self.switchstats.dp_desc_stats[dpid])
            else:
                config = {}
                config['mfr_desc'] = None
                config['hw_desc'] = None
                config['sw_desc'] = None
                config['serial_num'] = None

            request.write(simplejson.dumps(config))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_desc",
                            "Could not retrieve switch description.")

    def get_switch_stats(self,dpid): 
            stats = {}
            if dpid in self.switchstats.dp_port_stats:
                stats['total_rx_pkt']      = 0
                stats['total_tx_pkt']      = 0
                stats['total_dropped_pkt'] = 0
                stats['active_flows']      = 0
                stats['total_lookup_pkt']  = 0
                stats['total_matched_pkt'] = 0
                stats['packets_s']         = self.switchstats.get_switch_conn_p_s(dpid) 
                for port in self.switchstats.dp_port_stats[dpid].values():
                    stats['total_rx_pkt']   += port['rx_packets']
                    stats['total_tx_pkt']   += port['tx_packets']
                for tables in self.switchstats.dp_table_stats[dpid]:
                    # The first table sees every lookup, so use its value for
                    # the lookup count
                    if tables['table_id'] == 0:
                        stats['total_lookup_pkt'] = tables['lookup_count']
                    stats['active_flows']  += tables['active_count']
                    stats['total_matched_pkt'] += tables['matched_count']
            else:
                stats['total_rx_pkt']       = None
                stats['total_tx_pkt']       = None
                stats['total_dropped_pkt']  = None
                stats['active_flows']       = None
                stats['total_lookup_pkt']   = None
                stats['total_matched_pkt']  = None
                stats['packets_s']          = None 
            return stats

    def get_switch_stats_ws(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()
            stats = self.get_switch_stats(dpid)
            request.write(simplejson.dumps(stats))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_switch_stats",
                            "Could not return switch stats.")

    def get_tables(self, request, arg, switch_info):
        try:
            tablelist = []
            dpid = switch_info.dpid.as_host()
            stats_tbl = self.switchstats.dp_table_stats
        
            if dpid in stats_tbl: 
                for table in stats_tbl[dpid]:
                    tablelist.append(table['name'])

            request.write(simplejson.dumps(tablelist))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_tables",
                            "Could not retrieve switch tables.")

    def get_table_name_stats(self, request, arg, switch_info):
        try:
            name   = arg['<switch table>']
            stats = {}
            stats['active_count'] = 0
            stats['lookup_count'] = 0
            stats['matched_count'] = 0
            stats_tbl = self.switchstats.dp_table_stats
            dpid = switch_info.dpid.as_host()

            if dpid in stats_tbl: 
                for tables in stats_tbl[int(dpid)]:
                    if tables['name'] == name:
                        stats['active_flows']  = tables['active_count']
                        stats['lookup_pkts'] = tables['lookup_count']
                        stats['matched_pkts'] = tables['matched_count']
                        break

            # TBD: want to return 404 if table name not found?
            # Then what happens if switch not active - how can check for table name?

            request.write(simplejson.dumps(stats))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_table_name_stats",
                            "Could not retrieve switch table name stats.")

    def get_ports(self, request, arg, switch_info):
        try:
            ports = []
            for loc in switch_info.locations:
              if not loc.port_name.startswith("of"):
                  ports.append(loc.port_name)
            request.write(simplejson.dumps(ports))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_ports",
                            "Could not retrieve switch ports.")

    def __init_port_config__(self, arg, portname, dentry, sentry):
        if sentry is None:
            d = {}
            d['name'] = portname
            d['hw_addr'] = None
            d['curr'] = None
            d['supported'] = None
            d['enabled'] = None
            d['flood'] = None
            d['state'] = None
            d['link'] = None
            d['advertised'] = None
            d['peer'] = None
            d['config'] = None
            d['stat_speed'] = None
            d['stat_port_no'] = None
        else:
            d = copy.copy(sentry)
            d['stat_speed'] = d['speed']
            d['stat_port_no'] = d['port_no']
            del d['speed']
            del d['port_no']

        if dentry is None:
            d['location'] = None
            d['config_port_no'] = None
            d['config_speed'] = None
            d['config_duplex'] = None
            d['config_auto_neg'] = None
            d['config_neg_down'] = None
            d['config_admin_state'] = None
        else:
            if dentry.name is not None:
                d['location'] = mangle_name(arg['<dir name>'], dentry.name)
            d['config_port_no'] = dentry.port
            d['config_speed'] = dentry.speed
            d['config_duplex'] = dentry.duplex
            d['config_auto_neg'] = dentry.auto_neg
            d['config_neg_down'] = dentry.neg_down
            d['config_admin_state'] = dentry.admin_state

        return d

    def get_port_name_config(self, request, arg, switch_info):
        try:
            portname = arg['<port name>']
            dpid = switch_info.dpid.as_host()

            dentry = sentry = None
            for loc in switch_info.locations:
                if loc.port_name == portname:
                    dentry = loc
                    break

            if dpid in self.switchstats.dp_stats:
                ports = self.switchstats.dp_stats[dpid]['ports']
                for p in ports:
                    if p['name'] == portname:
                        sentry = p

            if dentry is None and sentry is None:
                return webservice.notFound(request, "Port '%s' not on switch." % portname)

            request.write(simplejson.dumps(self.__init_port_config__(arg, portname, dentry, sentry)))
            request.finish()
            return NOT_DONE_YET
        except:
            return self.err(Failure(), request, "get_port_name_config",
                            "Could not retrieve switch port name config.")

    def set_port_name_config(self, request, arg, switch_info):
        try:
            dpid = switch_info.dpid.as_host()
            if dpid not in self.switchstats.dp_stats:
                return webservice.notFound(request, "Switch not active to set config.")
            portname = arg['<port name>']
            port = None
            for p in self.switchstats.dp_stats[dpid]['ports']:
                if p['name'] == portname:
                    port = p
                    break
            if port is None:
                return webservice.notFound(request, "Port not active to set config.")

            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request,"Unable to parse message body.")
            port_no = port['port_no']    
            hw_addr = port['hw_addr'].replace('-',':')
            config = 0
            mask  = 0
            if 'flood' in content:
                mask |= openflow.OFPPC_NO_FLOOD
                if content['flood'] == False:
                    config |= openflow.OFPPC_NO_FLOOD
            if 'enabled' in content:
                mask |= openflow.OFPPC_PORT_DOWN
                if content['enabled'] == False:
                    config |= openflow.OFPPC_PORT_DOWN
            ret = self.switchstats.send_port_mod(dpid, port_no, hw_addr, mask, config)
            request.write(simplejson.dumps(ret))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "set_port_name_config",
                            "Could not set port name config.")

    def set_port_name_config_bool(self, request, arg, switch_info, maskbit): 
        try:
            dpid = switch_info.dpid.as_host()
            if dpid not in self.switchstats.dp_stats:
                return webservice.notFound(request, "Switch not active to set config.")
            portname = arg['<port name>']
            port = None
            for p in self.switchstats.dp_stats[dpid]['ports']:
                if p['name'] == portname:
                    port = p
                    break
            if port is None:
                return webservice.notFound(request, "Port not active to set config.")

            content = json_parse_message_body(request)
            if content != True and content != False:
                return webservice.badRequest(request, "Excepts a boolean value as message body.")
            port_no = port['port_no']    
            hw_addr = port['hw_addr'].replace('-',':')
            mask = 0 | maskbit 
            if content:
                config = 0
            else:    
                config = 0xffffffff 
            ret = self.switchstats.send_port_mod(dpid, port_no, hw_addr, mask, config)
            request.write(simplejson.dumps(ret))
            request.finish()
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "set_port_name_config",
                            "Could not set port name config.")

    def set_port_name_config_flood(self, request, arg, switch_info): 
        return self.set_port_name_config_bool(request, arg, switch_info, openflow.OFPPC_NO_FLOOD)
    def set_port_name_config_enable(self, request, arg, switch_info): 
        return self.set_port_name_config_bool(request, arg, switch_info, openflow.OFPPC_PORT_DOWN)

    def get_port_name_stats(self, request, arg, switch_info):
        try:
            portname = arg['<port name>']
            dpid = switch_info.dpid.as_host()

            if dpid in self.switchstats.dp_port_stats:
                ports  = self.switchstats.dp_port_stats[dpid]
                portno = self.switchstats.map_name_to_portno(dpid, portname)
                for p in ports.values():
                    if p['port_no'] == portno:
                        pc = copy.deepcopy(p)
                        del pc['port_no']
                        request.write(simplejson.dumps(pc))
                        request.finish()
                        return NOT_DONE_YET

            for loc in switch_info.locations:
                if loc.port_name == portname:
                    stats = {}
                    stats['collisions'] = None
                    stats['delta_bytes'] = None
                    stats['tx_bytes'] = None
                    stats['tx_packets'] = None
                    stats['tx_dropped'] = None
                    stats['tx_errors'] = None
                    stats['rx_bytes'] = None
                    stats['rx_packets'] = None
                    stats['rx_dropped'] = None
                    stats['rx_errors'] = None
                    stats['rx_`crc_err'] = None
                    stats['rx_over_err'] = None
                    stats['rx_frame_err'] = None
                    request.write(simplejson.dumps(stats))
                    request.finish()
                    return NOT_DONE_YET

            return webservice.notFound(request, "Port '%s' not on switch." % portname)
        except Exception, e:
            return self.err(Failure(), request, "get_port_name_stats",
                            "Could not retrieve switch port name stats.")


    # FIXME: this function should really just call get_name_for_name
    # in bindings_directory, instead of replicating the functionality 
    # (and bugs) of that function here.  
    def get_port_principals(self, request, arg, switch_info):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "get_port_principals",
                            "Could not retrieve port principals.")
        try:
            switchname = mangle_name(arg['<dir name>'], arg['<principal name>'])
            portname = arg['<port name>']
        
            # what type of names are we looking for ?
            name_type = Name.USER
            if 'host' in arg:
                name_type = Name.HOST
       
            def done(arr):
                # list may contain duplicates, remove them
                l = list(sets.Set(arr))
                request.write(simplejson.dumps(l))
                request.finish()   

            def cb1(loc_list):
                if len(errCalled) > 0:
                    return
                try:
                    if len(loc_list) == 0: 
                        done([]) 
                        return 

                    dpid_obj = datapathid.from_host(int(loc_list[0][0]))
                    port_num = int(loc_list[0][1])
                    def cb2(name_list):
                        if len(errCalled) > 0:
                            return
                        try:
                            ret = [] 
                            for n in name_list: 
                                if n[1] == name_type: 
                                    ret.append(n[0])
                            done(ret)
                        except Exception, e:
                            return err_specific(Failure())

                    self.bstore.get_names_by_ap(dpid_obj,port_num,cb2)
                except Exception, e:
                    return err_specific(Failure())
        
            self.bstore.get_location_by_switchport_name(switchname, portname, cb1)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
    
    def get_creds_as_json(self,cred_list): 
      l = [ { "fingerprint" : c.fingerprint, 
              "is_approved" : c.is_approved } for c in cred_list]
      return simplejson.dumps({ "fp_credentials" : l })

    def get_approval_handler(self,request,cred_list,switch_name,dir_name, 
                                                            fp,approved): 
        try:
            filtered = [] 
            for c in cred_list: 
                if fp == None or fp == c.fingerprint: 
                    if approved == None or approved == c.is_approved: 
                        filtered.append(c) 
            request.write(self.get_creds_as_json(filtered))
            request.finish()
        except Exception, e:
            return self.err(Failure(), request, "get_approval_handler",
                            "Could not retrieve switch approvals.")


    def set_approval_handler(self,request,cred_list,switch_name,dir_name,
                                                            fp,approved):
        try:
            if approved == None: 
                approved = True # default


            # if approving and no cred exists, fake it (e.g., non-ssl switches) 
            if approved == True and len(cred_list) == 0: 
                cred_list.append(CertFingerprintCredential("",True))

            if fp is not None or approved == True:
              # limit action to a particular fingerprint 
              for c in cred_list: 
                  if fp == None or fp == c.fingerprint: 
                      c.is_approved = approved
            else : 
              # approved == False, no fingeprint
              # remove all credentials
              cred_list = [] 
        
            def set_cred_cb(c_list): 
                request.write(self.get_creds_as_json(c_list))
                request.finish()
            
            d = self.dm.put_credentials(Directory.SWITCH_PRINCIPAL, 
                                        switch_name, cred_list, 
                                        Directory_Factory.AUTHORIZED_CERT_FP, dir_name) 
            d.addCallback(set_cred_cb) 
            d.addErrback(self.err, request, "set_approval_handler",
                         "Could not set switch approval.")
            return d
        except Exception, e:
            return self.err(Failure(), request, "set_approval_handler",
                            "Could not set switch approval.")


    def start_cred(self, request, arg,handler):
        try:
            switch_name = arg["<principal name>"] 
            dir_name = arg["<dir name>"]
            fp = None
            if request.args.has_key("fingerprint"): 
                fp = request.args["fingerprint"][0]
            approved = None
            if request.args.has_key("approved"): 
                if "false" == request.args["approved"][0]: approved = False
                if "true" == request.args["approved"][0]: approved = True
           
            def get_cred_cb(cred_list): 
                handler(request,cred_list,switch_name,dir_name,fp,approved) 

            d = self.dm.get_credentials(Directory.SWITCH_PRINCIPAL, 
                                        switch_name, Directory_Factory.AUTHORIZED_CERT_FP, dir_name)
            d.addCallback(get_cred_cb)
            d.addErrback(self.err, request, "start_cred",
                         "Could not retrieve switch credentials.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "start_cred",
                            "Could not retrieve switch credentials.")


    # this method initially handles most of the webservice
    # requests by looking up the switch info.

    def start(self, request, arg, handler, include_locs):
        try:
            switch_name = arg["<principal name>"] 
            dir_name = arg["<dir name>"] 
           
            d = self.dm.get_principal(Directory.SWITCH_PRINCIPAL, 
                                      switch_name, dir_name, include_locations=include_locs)
            d.addCallback(self.start2, handler, request, arg)
            d.addErrback(self.err, request, "start", "Could not retrieve switch %s." % switch_name)
            return NOT_DONE_YET
        except Exception,e :
            return self.err(Failure(), request, "start", "Could not retrieve switch.")
    
    def start2(self, switch_info, handler, request, arg):
        if switch_info == None:
            return webservice.notFound(request, "Switch does not exist.")
        return handler(request, arg, switch_info)

#   code for avoiding 404's and distinguishing between a non-existant
#   switch and one that is merely not currently active.  We may want to 
#   go down this path later, so i'm saving the code for now. 
#               - dan  (7-14-08)
#     
#          def ok(switch_info): 
#            if switch_info is None: 
#              webservice.internalError(request,
#                "no switch %s found" % mangled_name )
#            else:
#              # switch is in a directory but is not active
#              # we'll just return empty stats for it, indicated
#              # by the fact that dpid is still None
#              handler(request,arg,dpid)
#          def err(request, res): 
#            webservice.internalError(request, 
#                "error searching for switch %s: %s" % (mangled_name,str(res)) )
#          d = self.dm.get_switch(mangled_name)
#          d.addCallback(ok)
#          d.addErrback(err) 




    def __init__(self, dm, bindings_dir, stats):
        self.switchstats = stats
        self.dm = dm
        self.bstore = bindings_dir.get_bstore()

    def register_webservices(self, reg): 
        ss = webservice.WSPathStaticString
        dirname = WSPathExistingDirName(self.dm, "<dir name>");
        principalname = WSPathArbitraryString("<principal name>")
        tblname = WSPathArbitraryString("<switch table>")
        portname = WSPathArbitraryString("<port name>")

        # WSPathArbitraryString must use '<principal name>' in order to
        # play nicely with the URLs created by the directory manager
        switchpath = ( ss("switch"), dirname, principalname )

        # GET /ws.v1/switch/<dir name>/<switch name>/active
        reg(lambda x, y: self.start(x, y, self.is_active, False),
            "GET", switchpath + (ss("active"),),
            """Boolean indicator of whether a switch is currently active""")
        
        #GET /ws.v1/switch/<dir name>/<switch name>/approval
        reg(lambda x,y: self.start_cred(x,y,self.get_approval_handler),
            "GET",switchpath + (ss("approval"),),
            """Test whether this switch is adminstratively approved""")

        #PUT /ws.v1/switch/<dir name>/<switch name>/approval
        reg(lambda x,y: self.start_cred(x,y,self.set_approval_handler),
            "PUT",switchpath + (ss("approval"),),
            """Set whether this switch is adminstratively approved""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/reset
        reg(lambda x, y: self.start(x, y, self.switch_reset, False),
            "PUT", switchpath + (ss("reset"),),
            """Reset a switch""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/command
        reg(lambda x, y: self.start(x, y, self.send_switch_command, False),
            "PUT", switchpath + (ss("command"),),
            """Send switch an arbitrary command""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/update
        reg(lambda x, y: self.start(x, y, self.switch_update, False),
            "PUT", switchpath + (ss("update"),),
            """update a switch""")

        # GET /ws.v1/switch/<dir name>/<switch name>/config
        reg(lambda x, y: self.start(x, y, self.get_config, False),
            "GET", switchpath + (ss("config"),),
            """Get gobal config parameters for a switch""")

        # GET /ws.v1/switch/<dir name>/<switch name>/desc
        reg(lambda x, y: self.start(x, y, self.get_desc, False),
            "GET", switchpath + (ss("desc"),),
            """Get description of a switch""")


        # GET /ws.v1/switch/<dir name>/<switch name>/stat
        reg(lambda x, y: self.start(x, y, self.get_switch_stats_ws, False),
            "GET", switchpath + (ss("stat"),),
            """Get aggregate stats for the switch.""")

        # GET /ws.v1/switch/<dir name>/<switch name>/table
        reg(lambda x, y : self.start(x, y, self.get_tables, False),
            "GET", switchpath + (ss("table"),),
            """Get list of tables for a switch""")

        switchtablepath = switchpath + (ss("table"), tblname)

        # GET /ws.v1/switch/<dir name>/<switch name>/table/<switch table>/stat
        reg(lambda x, y : self.start(x, y, self.get_table_name_stats, False),
            "GET", switchtablepath + (ss("stat"),),
            """Get stats for a switch's table""")

        # GET /ws.v1/switch/<dir name>/<switch name>/port
        reg(lambda x, y : self.start(x, y, self.get_ports, True),
            "GET", switchpath + (ss("port"),),
            """Get list of ports for a switch""")

        switchportpath = switchpath + (ss("port"), portname)
        switchportpathconfig = switchportpath +  (ss("config"), )

        # GET /ws.v1/switch/<dir name>/<switch name>/port/<port name>/config
        reg(lambda x, y : self.start(x, y, self.get_port_name_config, True),
            "GET", switchportpathconfig,
            """Get configuration for a named port on a switch""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/port/<port name>/config
        # { "flood" : true/false
        #   "enabled" : true/false }
        reg(lambda x, y: self.start(x, y, self.set_port_name_config, False),
            "PUT", switchportpathconfig,
            """Set gobal config parameters for a switch""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/port/<port name>/config/flood
        # values: true/false
        reg(lambda x, y: self.start(x, y,self.set_port_name_config_flood, False),
            "PUT", switchportpathconfig + (ss("flood"),),
            """Set flood status for a port""")

        # PUT /ws.v1/switch/<dir name>/<switch name>/port/<port name>/config/enable
        # values: true/false
        reg(lambda x, y: self.start(x, y, self.set_port_name_config_enable, False),
            "PUT", switchportpathconfig + (ss("enable"),),
            """Set port up or down""")

        # GET /ws.v1/switch/<dir name>/<switch name>/port/<port name>/stat
        reg(lambda x, y : self.start(x, y, self.get_port_name_stats, True),
            "GET", switchportpath + (ss("stat"),),
            """Get stats for a named port on a switch""")

        # GET /ws.v1/switch/<dir name>/<switch name>/port/<port name>/<principal type> 
        for v in [ "user", "host" ]:
            path = switchportpath + (ss(v),)
            desc = "Get all %ss for a named port on a switch" % v
            fn = lambda x, y : self.start(x, y, self.get_port_principals, False)
            reg(fn, "GET", path, desc)
