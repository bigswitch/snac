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
from nox.lib.netinet.netinet import datapathid, create_datapathid_from_host
from nox.ext.apps.directory.dir_utils import *
from nox.webapps.webservice.web_arg_utils import new_get_cmp_fn,get_nametype_from_string, filter_item_list 
from twisted.internet import defer
from nox.ext.apps.visibility.visibility_ws import visibility_ws
from nox.ext.apps.sepl.policy import PyPolicyComponent
from nox.ext.apps.coreui.template_utils import utf8quote
from nox.ext.apps.directory.directorymanager import directorymanager
import copy 
import math
import urllib
import time
import logging 

lg = logging.getLogger('flow_table_pages') 
 
dl_map = { "0x0806" : "ARP" } 
nw_map = { "0x01" : "ICMP", "0x06" : "TCP", "0x11" : "UDP" } 


# helper class to do all of the lookups for mapping dpids 
# to switch names
class location_map_op:
  def __init__(self): 
    pass

  def start(self, dpid_list, dm): 
      self.d = defer.Deferred()
      if len(dpid_list) == 0: 
        self.d.callback({})
        return self.d
    
      self.data = {}
      dpid_list = list(set(dpid_list))
      self.p_count = len(dpid_list)
      self.cb_count = 0
      for id in dpid_list:
        d = dm.search_principals(Directory.SWITCH_PRINCIPAL, 
            {'dpid': create_datapathid_from_host(id) })
        d.addCallback(self._search_callback, id)
        d.addErrback(self._eb)
      return self.d
 
  def _eb(self,res):
    self.d.errback(res) # just pass it on 

  def _search_callback(self, res, dpid):
      self.data[dpid] = res
      self.cb_count += 1  
      if self.cb_count == self.p_count: 
        self.d.callback(self.data)

def set_proto_str(flow): 
  dl_type = flow['dl_type']
  nw_proto = flow['nw_proto'] 
  if dl_type == "0x0800": 
    flow['proto_str'] = nw_map.get(nw_proto, "IP Type: %s" % nw_proto)
  else :
    flow['proto_str'] = dl_map.get(dl_type, "Ether Type: %s" % dl_type)

def set_action_str(flow):
  if len(flow['policy_actions']):
    actionstr = flow['policy_actions'][0]
    if flow['routing_action_taken'] == "not routed" \
            and actionstr[:5] == "allow":
        actionstr += " (nr)"
    flow['action'] = actionstr
  else:
    #flow was broadcast (broadcast destination address or discovery)
    #TODO: if policy enforcement is turned off, the flow may not have been
    #      allowed, but we don't have visibility into what happened yet
    flow['action'] = "allow()"

def set_policy_str(policy, flow):
  if policy.policy_id != long(flow['policy_id']):
    flow['policy_str'] = "Unknown (policy id %s is no longer current)" \
        % flow['policy_id']  
    return 
  rules = flow['policy_rules'] 
  if len(rules) == 0:
    flow['rule_id'] = ""
    flow['policy_str'] = "None"
    return 
  # ignore all but first policy rule
  flow['rule_id'] = flow['policy_rules'][0] 
  long_id = long(flow['policy_rules'][0])
  flow['policy_str']  = policy.rules[long_id].ustr()

def set_time_str(flow): 
  time_float = float(flow['received_ts'])
  t = time.localtime(int(time_float))
  remainder = "%0.2f" % (time_float - float(int(time_float)))
  s = time.strftime("%b %d %H:%M:%S",t) 
  flow['received_ts'] = s + str(remainder)[1:len(remainder)]

class FlowTableRes(MonitorResource): 
    
    def __init__(self, component,capabilities):
        UIResource.__init__(self, component)
        self.required_capabilities = capabilities
        self.vis_ws = component.resolve(visibility_ws) 
        self.policy = component.resolve(PyPolicyComponent)
        self.dm = component.resolve(directorymanager)

    def err(self, res, request): 
      msg = "Unable to load flow list."
      lg.error("%s : %s " % (msg,str(res)))
      request.write(self.render_tmpl(request, "error.mako",
                msg = msg, header_msg = "Server Error:"))
      request.finish()

    def render_GET(self, request):
      try : 

        #args come as bytestrings, but they might be utf-8, so treat as unicode
        self.arg_cpy = dict([(k, [unicode(v1, 'utf-8') for v1 in v])
                for (k,v) in request.args.items()])
        
       # get sorting values, default places most recent flows at top of page
        sort_attr = request.args.get("sort_attr",["received_ts"])[-1]
        sort_desc_str = request.args.get("sort_desc",["true"])[-1]
        sort_desc = sort_desc_str == "true"

        mangled_name = None
        policy_rule_txt = None
        policyid = long(request.args.get('policy_id',[-1])[-1])
        ruleid = long(request.args.get('rule_id',[-1])[-1])
        if policyid > 0 and ruleid > 0: 
            if policyid == self.policy.policy_id and \
               ruleid in self.policy.rules:
                  policy_rule_txt = self.policy.rules[ruleid].ustr()
        
        if (request.args.get('allowed', [0])[0]):
            append_params = '"allowed=1"'
            unparsed_flows = self.vis_ws._fc.get_allowed_flows()
            title = "Recent Allowed Flow History"
        elif (request.args.get('denied', [0])[0]):
            append_params = '"denied=1"'
            unparsed_flows = self.vis_ws._fc.get_denied_flows()
            title = "Recent Denied Flow History"
        elif (request.args.get('all', [0])[0]):
            append_params = '"all=1"'
            unparsed_flows = self.vis_ws._fc.get_all_flows()
            title = "Recent Flow History"
        elif ('hostname' in request.args): 
          # this is a host flow page!
          mangled_name = request.args.get('hostname', 
                            [''])[-1].replace(r'\\', r'\\\\')
          unparsed_flows = self.vis_ws._fc.get_host_flows(mangled_name) 
          mangled_name = unicode(mangled_name, 'utf-8')
          title = "Flow History for Host: " + mangled_name
          append_params = '"hostname=" + encodeURIComponent("%s")' % mangled_name
          if policyid > 0 and ruleid > 0: 
            append_params += '+ "&policy_id=" + encodeURIComponent("%s") + "&rule_id=" + encodeURIComponent("%s")' % (policyid,ruleid)
        elif (policy_rule_txt is not None): 
            # this is a policy page
            unparsed_flows = self.vis_ws._fc.get_policy_flows(policyid, ruleid)
            title = "Flow History for Rule: " + policy_rule_txt
            append_params = '"policy_id=" + encodeURIComponent("%s") + "&rule_id=" + encodeURIComponent("%s")' % (policyid,ruleid)
        else:
            return badRequest(request, "Could not load flow table: Bad hostname or rule specified")
        
        all_flows = self.vis_ws.flow_infos_to_dict(unparsed_flows)

        # change some fields for easier viewing 
        # we must do this BEFORE filtering
        for flow in all_flows: 
          set_proto_str(flow)
          set_action_str(flow)
          set_policy_str(self.policy,flow)
          set_time_str(flow)
        
        # do this before filtering...
        unique_protos = set()
        unique_actions = set()
        unique_protos.add("")
        unique_actions.add("")
        for flow in all_flows:
          unique_protos.add(flow['proto_str'])
          unique_actions.add(flow['action'])

        filtered_flows = filter_item_list(all_flows, 
                        ["received_ts", "action", "src_host", "dst_host",
                           "proto_str", "nw_src", "nw_dst", "dl_src", 
                           "dl_dst", "tp_src", "tp_dst", "dl_vlan",
                           "policy_id", "rule_id" 
                        ], 
                        self.arg_cpy)
        
        if len(filtered_flows) > 1: 
          cmp_fn = new_get_cmp_fn(filtered_flows, sort_attr,sort_desc)
          filtered_flows.sort(cmp = cmp_fn)
        
        def write_to_html(dpid_map):
            for f in filtered_flows: 
              dpid = long(f['dpid'])
              switch_names = dpid_map.get(dpid,[])
              if len(switch_names) > 0: 
                f['switch_name'] = switch_names[0]

            request.write(self.render_tmpl(request, "flow_visibility.mako", 
                readable_flows=filtered_flows, args=self.arg_cpy,
                hostname = mangled_name, unique_protos=unique_protos,
                unique_actions=unique_actions, 
                policy_rule_txt=policy_rule_txt,title=title,
                append_params=append_params, 
                sort_attr=sort_attr, sort_desc_str=sort_desc_str))
            request.finish() 
        
        dpids = [ long(f['dpid']) for f in filtered_flows]
        op = location_map_op()
        d = op.start(dpids,self.dm)
        d.addCallback(write_to_html)
        d.addErrback(self.err,request)

      except Exception, e: 
        self.err(Failure(),request)
      return NOT_DONE_YET

class HostFlowSummaryRes(MonitorResource): 
    
    def __init__(self, component,capabilities):
        UIResource.__init__(self, component)
        self.required_capabilities = capabilities
        self.vis_ws = component.resolve(visibility_ws) 
        self.policy = component.resolve(PyPolicyComponent)
    
    def render_GET(self, request):
      try : 

        if not ('hostname' in request.args): 
            return badRequest(request, "No hostname specified")

        mangled_name = request.args.get('hostname', 
                            [''])[-1].replace(r'\\', r'\\\\')
        unparsed_flows = self.vis_ws._fc.get_host_flows(mangled_name) 
        rule_counts = {} 
        for fi in unparsed_flows: 
          if fi['policy_id'] != self.policy.policy_id: 
            continue
          for rid in fi['policy_rules']: 
            rule_counts[rid] = 1 + rule_counts.get(rid,0)

        res = [] 
        for rid,count in rule_counts.items(): 
          if rid in self.policy.rules:
            rule_txt = self.policy.rules[rid].ustr()
            res.append({ 'policy_id' : self.policy.policy_id,
                         'rule_id' : rid, 
                         'rule_text' : rule_txt, 
                         'matches' : count }) 

        request.write(self.render_tmpl(request, "host_flow_summary.mako", 
                readable_flows=res, hostname = mangled_name)) 
        
      except Exception, e: 
        lg.error("error generating host flow summary : %s " % str(Failure()))
        request.write("<center> Error loading policy match data </center>")

      request.finish()
      return NOT_DONE_YET
