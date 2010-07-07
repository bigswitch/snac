## -*- coding: utf-8 -*-
<%inherit file="monitors-layout.mako"/>

<%def name="page_title()">${title}</%def>


<%def name="head_css()"> 
  @import "/static/nox/ext/apps/snackui/snackmonitors/PrincipalList.css";
</%def> 

<%def name="head_js()">
${parent.head_js()} 

function toggle_details(id) { 
  var display_val = dojo.style(id, "display"); 
  if(display_val == "none") { 
    dojo.style(id, "display", "table-row");
    var txt = "v"; 
  }else {  
    dojo.style(id, "display", "none");
    var txt = "&gt"; 
  }
  dojo.byId(id + "-label").innerHTML = txt;  
}

function toggle_all() { 
  dojo.query(".policy-row").forEach(toggle_details); 
} 

dojo.require("dijit.Tooltip");  
dojo.require("nox.apps.coreui.coreui.ListTableHelper"); 

var listHelper = null; 
 
dojo.addOnLoad(function () {
  listHelper = new nox.apps.coreui.coreui.ListTableHelper({ 
      filters : [
          { id : "filter_time", urlParam : "received_ts"} ,
          { id : "filter_action", urlParam : "action"} ,
          { id : "filter_src_host", urlParam : "src_host"} ,
          { id : "filter_dst_host", urlParam : "dst_host"}, 
          { id : "filter_proto", urlParam : "proto_str"}, 
          { id : "filter_src_ip", urlParam : "nw_src"} ,
          { id : "filter_dst_ip", urlParam : "nw_dst"}, 
          { id : "filter_src_port", urlParam : "tp_src"} ,
          { id : "filter_dst_port", urlParam : "tp_dst"}, 
          { id : "filter_src_mac", urlParam : "dl_src"} ,
          { id : "filter_dst_mac", urlParam : "dl_dst"}, 
          { id : "filter_vlan", urlParam : "dl_vlan"}, 
          { id : "filter_sort_attr", urlParam : "sort_attr"}, 
          { id : "filter_sort_desc", urlParam : "sort_desc"} 
          ],
      append_params : ${append_params}
    });
    // hide update spinner 
    nox.apps.coreui.coreui.getUpdateMgr()._recurring_updates = [];  

%if hostname is not None:
    host = new nox.apps.directory.directorymanagerws.Host({ 
              initialData : { name : '${hostname}' } });  
    nox.apps.coreui.coreui.base.set_nav_title([
        {
            title_text: "Host:",
            nav_text: "Hosts",
            nav_url: "/Monitors/Hosts"
        },
        {
            title_text: host.directoryName() + " -",
            nav_text: host.directoryName(),
            nav_url: "/Monitors/Hosts?directory=" + host.directoryName()
        },
        {
            title_text: host.principalName(),
            nav_text: host.principalName(),
            nav_url: host.uiMonitorPath()
        }, 
        {
            title_text: host.principalName() + "Flow History ",
            nav_text: "Flow History", 
            nav_url : null 
        }
    ]);
%endif


});

 
</%def> 
<%!

import time
from nox.apps.coreui.web_arg_utils import get_html_for_select_box
from nox.apps.coreui.template_utils import utf8quote,get_principal_path,get_group_path

attr_map = { 'users' : "Users", 
             'host_groups' : "Host Groups", 
             'user_groups' : "User Groups", 
             'location_groups' : "Location Groups", 
             'switch_groups' : "Switch Groups",
             'dladdr_groups' : "MAC Address Groups",
             'nwaddr_groups' : "IP Address Groups"
          }

def format_port(flow, attr): 
  v = flow[attr]
  p = flow['proto_str'] 
  if p == "ICMP" or p == "TCP" or p == "UDP": 
    return v
  return ""

%> 


<%

def geta(attr): 
  return args.get(attr,[''])[0]

def sort_link(val,text): 
  return """<a onclick="javascript:listHelper.sort_clicked('%s')">%s </a>""" %\
    (val,text)

def get_principal_link(type,name): 
  for n in ["discovered;unknown", "discovered;unauthenticated"]: 
    if name.find(n) != -1: 
      return name
  return "<a href='" + get_principal_path(type,name) + "'>" + name + "</a>" 

def get_group_link(type,name): 
  for n in ["discovered;unknown", "discovered;unauthenticated"]: 
    if name.find(n) != -1: 
      return name
  return "<a href='" + get_group_path(type,name) + "'>" + name + "</a>" 
 
%> 


%if hostname is not None and policy_rule_txt is not None: 
  <p> Showing only flows that matched rule: <b>${policy_rule_txt}</b>
   &nbsp;&nbsp;
  ( <a href="/Monitors/FlowHistory?hostname=${utf8quote(hostname)}"> 
       Show all recent flows </a> ) </p>
%endif
<span style="float: right; size: 110em;"><a href="javascript:listHelper._apply_filter()"> refresh results </a></span> 
<br>
<br> 

<table> 
<tr class="headerRow">
<th> <a href="javascript:toggle_all()"></a></th> <!-- don't show for now -->
<th> ${sort_link("received_ts", "Time")} </th> 
<th> ${sort_link("action", "Action")} </th>
<th> ${sort_link("src_host", "Src Host")} </th>
<th> ${sort_link("dst_host", "Dst Host")} </th> 
<th> ${sort_link("proto_str", "Protocol")} </th> 
<th> ${sort_link("nw_src", "Src IP")} </th>
<th> ${sort_link("nw_dst", "Dst IP")} </th>
<th> ${sort_link("tp_src", "Src Port")} </th> 
<th> ${sort_link("tp_dst", "Dst Port")} </th> 
<th> ${sort_link("dl_src", "Src MAC")} </th>
<th> ${sort_link("dl_dst", "Dst MAC")} </th>
<th> ${sort_link("dl_vlan", "VLAN")} </th>
</tr>

<tr class="noxPrincipalGridFilter filterTable" >
<td> 
<button id="clear_btn" dojoType="dijit.form.Button" style="float: left;">
<img src="/static/nox/apps/coreui/coreui/images/clearFilterButton.png" alt="Clear Filters" />
<span dojoType="dijit.Tooltip" connectId="clear_btn" label="Clear Filters"></span> 
</button>
</td> 
<td> <input type="textbox" id="filter_time" size="4" value="${geta('received_ts')}"> </td> 
<td>  
${get_html_for_select_box(unique_actions, geta('action'), [('id','filter_action')]) } 
</td>
<td> <input type="textbox" id="filter_src_host" size="9" value="${geta('src_host')}"> </td> 
<td> <input type="textbox" id="filter_dst_host" size="9" value="${geta('dst_host')}"> </td> 
<td> 
${get_html_for_select_box(unique_protos, geta('proto_str'), [('id','filter_proto')]) } 
</td> 
<td> <input type="textbox" id="filter_src_ip" size="4" value="${geta('nw_src')}"> </td> 
<td> <input type="textbox" id="filter_dst_ip" size="4" value="${geta('nw_dst')}"> </td> 
<td> <input type="textbox" id="filter_src_port" size="2" value="${geta('tp_src')}"> </td> 
<td> <input type="textbox" id="filter_dst_port" size="2" value="${geta('tp_dst')}"> </td> 
<td> <input type="textbox" id="filter_src_mac" size="9" value="${geta('dl_src')}"> </td> 
<td> <input type="textbox" id="filter_dst_mac" size="9" value="${geta('dl_dst')}"> </td> 
<td> <input type="textbox" id="filter_vlan" size="2" value="${geta('dl_vlan')}"> </td> 
</tr>


<% i = 0 %>  
%for flow in readable_flows: 
<tr class="rowclass${i % 2}">
<td> 
<a href="javascript:toggle_details('policy-row' + ${i})"> 
<span id="policy-row${i}-label">&gt;</span></a> 
</td> 
<td> ${flow['received_ts']} </td> 
<td> ${flow['action']} </td> 
<td> ${get_principal_link('Host',flow['src_host'])}</td>
<td> ${get_principal_link('Host',flow['dst_host'])}</td>
<td> ${flow['proto_str']} </td> 
<td>${flow["nw_src"]}</td>
<td>${flow["nw_dst"]}</td>
<td>${format_port(flow,"tp_src")}</td>
<td>${format_port(flow,"tp_dst")}</td>
<td>${flow["dl_src"]}</td>
<td>${flow["dl_dst"]}</td>
<td> ${flow['dl_vlan']} </td>
</tr> 

<tr id="policy-row${i}" class="policy-row rowclass${i%2}" style="display: none">
  <td colspan="13">
<hr> 
  <table> 
<tr><td colspan="3"> <b>Policy Rule:</b> </td></tr> 
<tr><td colspan="3"> ${flow['policy_str']} <td></tr> 
<tr/> 
<tr><td> <b>Name Bindings:</b></td><td><b>Source</b></td><td><b>Destination</b></td></tr> 
  <% found_a_binding = False %> 
  % for attr in attr_map.keys() : 
    % if ((len(flow['src_' + attr]) > 0) or (len(flow['dst_' + attr]) > 0)) : 
      <% 
        found_a_binding = True 
        if attr == "users": 
          cap_ptype = "User"
          link_fn = get_principal_link
        else: 
          cap_ptype = attr_map[attr].split()[0]
          link_fn = get_group_link
        src_names = [link_fn(cap_ptype, n) for n in flow['src_' + attr]]
        dst_names = [link_fn(cap_ptype, n) for n in flow['dst_' + attr]]
      %> 
      <tr><td>${attr_map[attr]}</td>
          <td>${" <br> ".join(src_names)} </td> 
          <td>${" <br> ".join(dst_names)} </td> 
      </tr> 
    %endif 
  %endfor
  % if not found_a_binding: 
    <tr> <td colspan="3"> None </td></tr> 
  % endif
<tr/> 
<tr><td colspan="3"><b>First Hop Switch:</b></td></tr>
% if 'switch_name' in flow: 
<tr><td colspan="3">${get_principal_link("Switch",flow['switch_name'])} 
(port: ${flow['in_port']}) </td></tr>
% else: 
<tr><td colspan="3">dpid: ${flow['dpid']} 
(port: ${flow['in_port']}) </td></tr>
% endif 
</table> 
<hr> 
</td></tr> 
<% i += 1 %> 
%endfor 
</table>
% if len(readable_flows) == 0:
<center><h2> No Flows Found </h2></center> 
% endif
<input type="hidden" id="filter_sort_attr" value="${sort_attr}"> 
<input type="hidden" id="filter_sort_desc" value="${sort_desc_str}"> 
