from nox.lib.core import *

from nox.ext.apps.coreui.authui import UISection, UIResource
from nox.webapps.webserver.webauth import Capabilities
from nox.webapps.webserver.webserver import redirect
from nox.ext.apps.coreui import coreui
from nox.webapps.webservice.webservice import *
from nox.ext.apps.coreui.monitorsui import *
from nox.netapps.bindings_storage.bindings_directory import *
from nox.ext.apps.directory.directorymanager import *
from nox.webapps.webservice.webservice import *
from nox.ext.apps.directory.dir_utils import *
from nox.webapps.webservice.web_arg_utils import new_get_cmp_fn,get_nametype_from_string, filter_item_list 
from nox.netapps.bindings_storage.bindings_directory import *
from nox.ext.apps.directory.principal_search import do_principal_search
from nox.netapps.switchstats.switchstats import switchstats
from twisted.internet import defer
from nox.ext.apps.directory.dm_ws_switch import dm_ws_switch
from nox.ext.apps.directory.dm_ws_location import dm_ws_location
import copy 
import math
import urllib
import logging 

lg = logging.getLogger('principal_list_pages') 

PAGINATION_COUNT_DEFAULT = 15


class PrincipalListRes(MonitorResource): 
    
    def __init__(self, ptype, component,capabilities):
        UIResource.__init__(self, component)
        self.dm = component.resolve(directorymanager)
        self.bd = component.resolve(BindingsDirectory) 
        self.required_capabilities = capabilities
        self.to_remove = [ "start", "count","sort_attr","sort_desc"]
        self.ptype = ptype
        self.template_args = {} 

    def err(self, res, request): 
      msg = "Unable to load %s list." % (self.ptype)
      lg.error("%s : %s " % (msg,str(res)))
      request.write(self.render_tmpl(request, "iframe_error.mako",
                msg = msg, header_msg = "Server Error:"))
      request.finish()

    def render_GET(self, request):
      try : 

        #args come as bytestrings, but they might be utf-8, so treat as unicode
        self.arg_cpy = dict([(k, [unicode(v1, 'utf-8') for v1 in v])
                for (k,v) in request.args.items()])
        
        # get pagination values
        start = int(request.args.get("start",["0"])[-1])
        count = int(request.args.get("count",[PAGINATION_COUNT_DEFAULT])[-1])
        end = start + count

        # get sorting values
        sort_attr = request.args.get("sort_attr",["name"])[-1]
        sort_desc_str = request.args.get("sort_desc",["false"])[-1]
        sort_desc = sort_desc_str == "true"

        # remove args that we don't want to pass to the directory 
        for key in self.to_remove: 
          if key in request.args:
            del request.args[key]
            
        def write_to_html(ret_list):
            total = len(ret_list) 
            if len(ret_list) > 1: 
                cmp_fn = new_get_cmp_fn(ret_list, sort_attr,sort_desc)
                ret_list.sort(cmp = cmp_fn)

            ret_list = ret_list[start:end]
            
            num_rows = len(ret_list)
            first_res_num = start + 1
            if num_rows == 0: 
              first_res_num = 0
            
            # repopulate status combobox
            a = self.arg_cpy.get('active',[''])[0]
            status_selected = [] 
            for x in [ "", "true", "false" ]: 
              if a == x: 
                status_selected.append('selected = "true"')
              else: 
                status_selected.append("") 
            
            request.write(self.render_tmpl(request, "%slist.mako" % self.ptype, 
                p_list=ret_list, args=self.arg_cpy, start=start,count=count,
                total=total, sort_attr=sort_attr, sort_desc_str=sort_desc_str,
                num_rows = num_rows, first_res_num = first_res_num,
                status_selected=status_selected,ptype = self.ptype, **self.template_args))
            request.finish() 
        
        dir = None
        if "directory" in request.args: 
          dir = request.args["directory"][-1]
          del request.args["directory"]

        d = do_principal_search(request,self.ptype, dir, self.dm, self.bd)
        d.addCallbacks(self.handle_search_results)
        d.addCallback(write_to_html)
        d.addErrback(self.err,request)
      except Exception, e: 
        self.err(Failure(),request)
      return NOT_DONE_YET

    # by default, just convert (name,dir,status) 
    def handle_search_results(self, res): 
        gather_op = gather_status_op()
        d = gather_op.start(res, self.ptype, self.bd)
        return d
      
class SwitchListRes(PrincipalListRes):

    def __init__(self, component,capabilities):
        PrincipalListRes.__init__(self,"switch",component,capabilities)
        self.switch_stats = component.resolve(switchstats) 
        self.dm_ws_switch = dm_ws_switch(self.dm,self.bd,self.switch_stats)
    
    def handle_search_results(self, res): 
        status_op = gather_status_op()
        d = status_op.start(res, self.ptype, self.bd)
        switchstats_op = gather_switchstats_op()
        d.addCallback(switchstats_op.start, self.dm, self.dm_ws_switch)
        switchcreds_op = gather_switchcreds_op()
        d.addCallback(switchcreds_op.start, self.dm)
        return d

class LocationListRes(PrincipalListRes):

    def __init__(self, component,capabilities):
        PrincipalListRes.__init__(self,"location",component,capabilities)
        self.dm_ws_location = dm_ws_location(self.dm,self.bd)
        self.to_remove += ["switch_name","port_name"]

    def handle_search_results(self, res): 
        gather_op = gather_status_op()
        d = gather_op.start(res, self.ptype, self.bd)
        locinfo_op = gather_locinfo_op()
        d.addCallback(locinfo_op.start, self.dm_ws_location)
        def final_processing(res):
          unique_ports = set()
          unique_ports.add("")
          for i in res: 
            i["name"] = demangle_name(i["name"])[1]
            i["switch_name"] = demangle_name(i["switch_name"])[1]
            unique_ports.add(i["port_name"])
          self.template_args["unique_ports"] = unique_ports
          return res
        d.addCallback(final_processing) 
        def filter_locations(res): 
          return filter_item_list(res, ["port_name", "switch_name" ], self.arg_cpy)
        d.addCallback(filter_locations) 
        return d


class HostListRes(PrincipalListRes):

    def __init__(self, component,capabilities):
        PrincipalListRes.__init__(self,"host",component,capabilities)
        self.to_remove += ["nwaddr_glob","dladdr_glob","location_name_glob"]

    # takes the ifaces returned from the gather operation 
    # and converts them to standard dictionary format
    def _build_host_info(self,iface_data):
      ret_list = []
      for h, ifaces in iface_data.iteritems(): 
          dirname, name = demangle_name(h)
          status = "inactive"
          if len(ifaces) > 0: 
              status = "active"
          ret_list.append({
                              "full_name" : h, 
                              "name" : name, 
                              "dir" : dirname,
                              "ip_str" : gen_iface_str(ifaces,"nwaddr"), 
                              "mac_str" : gen_iface_str(ifaces,"dladdr"), 
                              "loc_str" : gen_iface_str(ifaces,"location_name"), 
                              "status" : status,
          })
      return ret_list

    # for hosts, we need to do extra binding storage lookups
    def handle_search_results(self, res):
        gather_op = gather_hostlist_data_op()
        d = gather_op.start(res,self.arg_cpy, self.bd)
        d.addCallback(self._build_host_info) 
        return d

# helper classes / functions

class gather_status_op(): 
  def __init__(self):
    pass
  
  def start(self, principal_list, ptype_str, bindings_dir):
      self.d = defer.Deferred()
      if len(principal_list) == 0: 
        self.d.callback([])
        return self.d
      self.data = {}
      for p in principal_list:
        dir,name = demangle_name(p)
        self.data[p] = { "full_name" : p, 
                          "name" : name,
                          "dir" : dir
                       }
      self.p_count = len(principal_list)
      self.cb_count = 0
      ptype = get_nametype_from_string(ptype_str)  
      bstore = bindings_dir.get_bstore()
      i = 0
      for p in principal_list:
        i += 1
        cb = (lambda x: lambda y: self._bs_callback(x,y))(p)
        if ptype == Name.USER or ptype == Name.HOST: 
          bstore.get_entities_by_name(p,ptype,cb)
        else : 
          bstore.get_location_by_name(p,ptype,cb)
      return self.d
    
  def _bs_callback(self, name, res):
      if len(res) > 0: 
        self.data[name]["status"] = "active"
      else: 
        self.data[name]["status"] = "inactive"
      self.cb_count += 1
      if self.cb_count == self.p_count: 
        self.d.callback(self.data.values())
 
class gather_hostlist_data_op(): 
    def __init__(self):
      pass

    # for a particular attribute 'nwaddr','dladdr', or 'location'
    # remove the host from self.data if none of the interfaces
    # match the glob
    def _filter_iface_glob(self,attr):
      if(attr + "_glob" in self.args):
        regex_str = glob_to_regex(self.args[attr + "_glob"][-1])
        regex = re.compile(regex_str,re.IGNORECASE)
        for h,ifaces in self.data.items():
          match = False
          for i in ifaces:
            if regex.match(i[attr]):
              match = True
          if not match: 
            del self.data[h]
    
    def finish(self): 
      self._filter_iface_glob("nwaddr")       
      self._filter_iface_glob("dladdr")       
      self._filter_iface_glob("location_name")     
      self.d.callback(self.data) 
    
    def _get_ifaces_cb(self,res, h): 
      self.data[h] = res
      self.iface_cb_count += 1
      if self.iface_cb_count == self.host_count: 
        self.finish()

    def start(self, hostname_list, args, bindings_dir):
      self.d = defer.Deferred()
      if len(hostname_list) == 0: 
        self.d.callback({})
        return self.d
      self.args = args
      self.data = {} 
      for h in hostname_list:
        self.data[h] = {} 
      self.host_count = len(hostname_list)
      self.iface_cb_count = 0
      for h in hostname_list:
        # chaining too many callbacks can be bad news
        # so we just do many different deferreds
        dx = bindings_dir.get_interfaces_for_host(h)
        dx.addCallback(self._get_ifaces_cb,h)
      return self.d

class gather_switchstats_op(): 
  def __init__(self):
    pass
  
  def start(self, switch_list, dm,dm_ws):
      self.d = defer.Deferred()
      if len(switch_list) == 0: 
        self.d.callback(switch_list)
        return self.d
     
      self.dm_ws = dm_ws 
      self.data = {}
      for s in switch_list: 
        self.data[s['full_name']] = s
      self.p_count = len(switch_list)
      self.cb_count = 0
      for s in self.data.keys():
        d = dm.get_principal(Directory.SWITCH_PRINCIPAL,s)
        d.addCallback(self._switchinfo_callback, s)
        d.addErrback(self._got_stat_cb)
      return self.d
  
  def _got_stat_cb(self,res):
    self.cb_count += 1  
    if self.cb_count == self.p_count: 
        self.d.callback(self.data.values())

  def _get_flowmiss_rate(self, stats): 
      matches = stats["total_matched_pkt"]
      lookups = stats["total_lookup_pkt"]
      if matches == None or lookups == None:
        return None
      if matches == 0: 
        return 0
      return math.floor(100 * (lookups - matches) / lookups)
  
  def _switchinfo_callback(self, res,name):
    if res is None: 
      del self.data[name]
    else: 
      stats = self.dm_ws.get_switch_stats(res.dpid.as_host())
      self.data[name].update(stats) 
      self.data[name]["flowmiss_rate"] = self._get_flowmiss_rate(stats)
    self._got_stat_cb(res)

class gather_switchcreds_op(): 
  def __init__(self):
    pass
  
  def start(self, switch_list, dm):
      self.d = defer.Deferred()
      if len(switch_list) == 0: 
        self.d.callback(switch_list)
        return self.d
    
      self.data = {}
      for s in switch_list: 
        self.data[s['full_name']] = s
      self.p_count = len(switch_list)
      self.cb_count = 0
      for s in self.data.keys():
        d = dm.get_credentials(Directory.SWITCH_PRINCIPAL,s, 
              Directory_Factory.AUTHORIZED_CERT_FP)
        d.addCallback(self._switchcred_callback, s)
        d.addErrback(self._got_cred_cb)
      return self.d
  
  def _got_cred_cb(self,res):
    self.cb_count += 1  
    if self.cb_count == self.p_count: 
        self.d.callback(self.data.values())

  def _switchcred_callback(self, res,name):
      if res is not None: 
        is_registered = False
        for c in res: 
          if c.is_approved:
            is_registered = True
            break
        if not is_registered: 
          self.data[name]["status"] = "unregistered"
      self._got_cred_cb(res)


class gather_locinfo_op(): 
  def __init__(self):
    pass
  
  def start(self, loc_list, dm_ws_location):
      self.d = defer.Deferred()
      if len(loc_list) == 0: 
        self.d.callback(loc_list)
        return self.d
    
      self.data = {}
      for l in loc_list: 
        self.data[l['full_name']] = l
      self.p_count = len(loc_list)
      self.cb_count = 0
      for s in self.data.keys():
        d = dm_ws_location.start(s)
        d.addCallback(self._locinfo_callback, s)
        d.addErrback(self._got_info_cb)
      return self.d
  
  def _got_info_cb(self,res):
    self.cb_count += 1  
    if self.cb_count == self.p_count: 
        self.d.callback(self.data.values())

  def _locinfo_callback(self, res,name):
      self.data[name].update(res)
      self._got_info_cb(res)

# this does not provide deterministic ordering, but that is ok
# as the underlying data returned from binding storage is not
# in any meaningful order either.  
# eventually we should figure out which interface is 'primary'
def gen_iface_str(ifaces, attr): 
    unique_vals = list(sets.Set([i[attr] for i in ifaces]))
    l = len(unique_vals)
    if l == 0: 
      return ""
    elif l == 1: 
      return unique_vals[0]; 
    else: 
      return unique_vals[0] + "( +%s)" % l
# general utilities

def get_status_markup(status): 
  if status == "active" : 
    cls = "successmsg"
  else : 
    cls = "errormsg" 
  return "<span class='%s'>%s</span>" % (cls, status)

def get_not_none(v):
  if v == None:
    return "?"
  return v


