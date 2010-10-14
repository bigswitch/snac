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

from nox.lib.core import *

from nox.apps.coreui  import webservice

from nox.lib.config   import version
from nox.lib.directory import Directory, DirectoryException
from nox.lib.netinet.netinet import datapathid

from nox.apps.switchstats.switchstats    import switchstats
from nox.apps.switchstats.pycswitchstats import pycswitchstats
from nox.apps.directory.directorymanager import directorymanager
from nox.apps.miscws.cpustats            import cpustats

from twisted.internet import defer
from twisted.python.failure import Failure

lg = logging.getLogger('noxinfows')

class dp_name_resolve_fsm:
    
    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def __init__(self, request, hitter_list, dirman, num_req):
        self.dm          = dirman
        self.request     = request
        self.hitter_list = hitter_list
        self.num_requested = num_req

        ds = []
        for item in hitter_list:
            dpid_obj =  datapathid.from_host(item[0])
            query = {'dpid' :  dpid_obj}
            ds.append(self.dm.search_principals(Directory.SWITCH_PRINCIPAL, 
                                                query))

        d = defer.DeferredList(ds, consumeErrors=True)
        d.addCallback(self.switch_names_resolved) 
        d.addErrback(self.err, self.request, "dp_name_resolve_fsm",
                     "Could not retrieve switch names.")

    def switch_names_resolved(self, resList):
        named_list = []
        for i in xrange(len(resList)):
            res = resList[i]
            if res[0] == defer.FAILURE:
                return self.err(res[1], self.request, "switch_names_resolved",
                                "Could not retrieve switch names.")

            item = self.hitter_list[i]
            if len(res[1]) > 0:
                named_list.append((res[1][0], item[1]))
            else:
                named_list.append(item)

        def hitter_comp(x,y):
            if x[1] < y[1]:
                return 1
            else:
                return -1
        named_list.sort(hitter_comp)
        to_send = named_list[:self.num_requested]
        self.request.write(simplejson.dumps(to_send))
        self.request.finish()

class loc_name_resolve_fsm:
    
    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def __init__(self, request, hitter_list, dirman, num_req):
        self.dm          = dirman
        self.request     = request
        self.hitter_list = []
        self.num_requested = num_req

        ds = []
        for item in hitter_list:
            dpid_obj =  datapathid.from_host(item[0])
            query = {'dpid' :  dpid_obj, 'port' :  item[1]}
            ds.append(self.dm.search_principals(Directory.LOCATION_PRINCIPAL,query))
            self.hitter_list.append([item, {"value" : item[2]}, dpid_obj])

        d = defer.DeferredList(ds, consumeErrors=True)
        d.addCallback(self.loc_search_done) 
        d.addErrback(self.err, self.request, "loc_name_resolve_fsm",
                     "Could not retrieve location names.") 
    
    def loc_search_done(self, resList):
        ds = []
        for i in xrange(len(resList)):
            res = resList[i]
            if res[0] == defer.FAILURE:
                return self.err(res[1], self.request, "loc_search_done",
                                "Could not retrieve location names.")
            hitter = self.hitter_list[i]
            if len(res[1]) > 0:
                hitter[1]["name"] = res[1][0]
                ds.append(self.dm.get_principal(Directory.LOCATION_PRINCIPAL, res[1][0]))

            else:
                item = hitter[0]
                raise Exception("Location search failed for dpid = '%s' port '%s'." % \
                                    (str(item[0]),  str(item[1])))

        d = defer.DeferredList(ds, consumeErrors=True)
        d.addCallback(self.loc_get_done)
        return d

    def loc_get_done(self, resList):
        ds = []
        for i in xrange(len(resList)):
            res = resList[i]
            if res[0] == defer.FAILURE:
                return self.err(res[1], self.request, "loc_get_done",
                                "Could not retrieve location info.")
            hitter = self.hitter_list[i]
            if res[1] is None:
                raise Exception("get_principal failed for: %s" % hitter[1]["name"])
            else: 
                hitter[1]["port_name"] = res[1].port_name
                query = {'dpid' :  hitter[2] }
                ds.append(self.dm.search_principals(Directory.SWITCH_PRINCIPAL, query))

        d = defer.DeferredList(ds, consumeErrors=True)
        d.addCallback(self.switch_search_done) 
        return d

    def switch_search_done(self, resList):
        named_list = []
        for i in xrange(len(resList)):
            res = resList[i]
            if res[0] == defer.FAILURE:
                return self.err(res[1], self.request, "switch_search_done",
                                "Could not retrieve switch info.")
            hitter = self.hitter_list[i]
            if len(res[1]) > 0:
                hitter[1]["switch_name"] = res[1][0]
            else:
                raise Exception("Switch search failed for dpid = '%s'" % str(hitter[2]))
            named_list.append(hitter[1])

        def hitter_comp(x,y):
            if x["value"] < y["value"]:
                return 1
            else:
                return -1
        named_list.sort(hitter_comp)    
        to_send = named_list[:self.num_requested]
        self.request.write(simplejson.dumps(to_send))
        self.request.finish()
        

class noxinfows(Component):
    """Web service interface info about nox"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def _get_nox_stat(self, request, arg):
        try: 
            stats = {}
            stats['version'] = version
            stats['uptime']  = self.ctxt.get_kernel().uptime()
            stats['load']    = self.cswitchstats.get_global_conn_p_s()
            # this is using undocumented parts of the twisted API
            # It might break if they change things
            stats['active_admins'] = len(request.site.sessions)
            return simplejson.dumps(stats)
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_stat",
                            "Could not retrieve nox stats.")

    def _get_nox_hitters_switch_p_s(self, request, arg):
        try:
            # FIXME: this should take a number of heavy hitters to show
            swlist = self.switchstats.get_switch_conn_p_s_heavy_hitters()
            if len(swlist) == 0:
                return simplejson.dumps([])
            dp_name_resolve_fsm(request, swlist, self.dm, 5)  
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_hitters_switch_p_s",
                            "Could not retrieve switch heavy hitters.")

    def _get_nox_hitters_port_err(self, request, arg):    
        try:
            # FIXME: this should take a number of heavy hitters to show
            portlist = self.switchstats.get_switch_port_error_heavy_hitters()
            if len(portlist) == 0:
                return simplejson.dumps([])
            l = loc_name_resolve_fsm(request, portlist, self.dm, 5)  
            self.l = l
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_hitters_port_err",
                            "Could not retrieve port error heavy hitters.")

    def _get_nox_hitters_port_bw(self, request, arg):   
        try:
            # FIXME: this should take a number of heavy hitters to show
            portlist = self.switchstats.get_switch_port_bandwidth_hitters()
            if len(portlist) == 0:
                return simplejson.dumps([])
            l = loc_name_resolve_fsm(request, portlist, self.dm, 5)  
            self.l = l
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_hitters_port_bw",
                            "Could not retrieve port bandwith heavy hitters.")

    def _get_nox_version(self, request, arg):
        try:
            return simplejson.dumps(version)
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_version",
                            "Could not retrieve NOX version.")

    def _get_nox_uptime(self, request, arg):
        try:
            return simplejson.dumps(self.ctxt.get_kernel().uptime())
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_uptime",
                            "Could not retrieve NOX uptime.")

    def _get_nox_cpu_stats(self, request, arg):
        try:
            results = {}
            results['user'] = self.cpu.last_user_time
            results['sys']  = self.cpu.last_sys_time
            results['io']   = self.cpu.last_io_time
            results['irq']  = self.cpu.last_irq_time
            return simplejson.dumps(results)
        except Exception, e:
            return self.err(Failure(), request, "_get_nox_cpu_stats",
                            "Could not retrieve NOX CPU stats.")

    def install(self):
        
        self.switchstats  = self.resolve(switchstats)
        self.cswitchstats = self.resolve(pycswitchstats)
        self.dm           = self.resolve(directorymanager)
        self.cpu          = self.resolve(cpustats)

        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/nox
        noxpath = ( webservice.WSPathStaticString("nox"), )

        # /ws.v1/nox/stat
        noxstatpath = noxpath + \
                        ( webservice.WSPathStaticString("stat"), )
        reg(self._get_nox_stat, "GET", noxstatpath,
            """Get nox stats""")

        # /ws.v1/nox/version
        noxversionpath = noxpath + \
                        ( webservice.WSPathStaticString("version"), )
        reg(self._get_nox_version, "GET", noxversionpath,
            """Get nox version""")

        # /ws.v1/nox/uptime
        noxuptimepath = noxpath + \
                        ( webservice.WSPathStaticString("uptime"), )
        reg(self._get_nox_uptime, "GET", noxuptimepath,
            """Get nox uptime""")

        # /ws.v1/nox/cpu/stats
        noxcpupath = noxpath + \
                        ( webservice.WSPathStaticString("cpu"), )
        noxcpupathstats = noxcpupath + \
                        ( webservice.WSPathStaticString("stat"), )
        reg(self._get_nox_cpu_stats, "GET", noxcpupathstats,
            """Get nox cpu stat""")

        # heavy hitters
        noxhitterspath = noxpath + ( webservice.WSPathStaticString("heavyhitters"), )
        
        # /ws.v1/nox/heavyhitters/switch_p_s        
        noxhitters_switch = noxhitterspath + \
                        ( webservice.WSPathStaticString("switch_p_s"), )
        reg(self._get_nox_hitters_switch_p_s, "GET", noxhitters_switch,
            """Get heavy hitters list for switch flows/s""")

        # /ws.v1/nox/heavyhitters/port_err
        noxhitters_port_err = noxhitterspath + \
                        ( webservice.WSPathStaticString("port_err"), )
        reg(self._get_nox_hitters_port_err, "GET", noxhitters_port_err,
            """Get heavy hitters list for port errors""")

        # /ws.v1/nox/heavyhitters/port_bw
        noxhitters_port_bw = noxhitterspath + \
                        ( webservice.WSPathStaticString("port_bw"), )
        reg(self._get_nox_hitters_port_bw, "GET", noxhitters_port_bw,
            """Get heavy hitters list for port bandwidth""")

    def getInterface(self):
        return str(noxinfows)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return noxinfows(ctxt)

    return Factory()
