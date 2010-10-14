## -*- coding: utf-8 -*-
<%inherit file="principallist_base.mako"/>
<%def name="page_title()">Switchlist</%def>

<%def name="head_js()">
  ${parent.head_js()} 
  dojo.require("nox.ext.apps.directory.directorymanagerws.Switch"); 
  
  var pFilter = null;
  dojo.addOnLoad(function () {
      var filters = nox.ext.apps.directory.directorymanagerws.PrincipalListFilter; 
      pFilter = filters.init_principal_list_page("switch");
      filters.setup_switch_registration_hooks(); 
  }); 
</%def>

<%def name="infopage_link(p_info)"> 
<a href="#" onclick="javascript:change_main_page('/Monitors/Switches/SwitchInfo?name=${utf8quote(p_info['full_name'])}')"> ${p_info["name"]} </a> 
</%def> 

## ---------------------------------------------------------------------------

<%!
from nox.ext.apps.directory.directorymanager import demangle_name
from nox.ext.apps.snackui.principal_list_pages import get_status_markup, get_not_none
from nox.ext.apps.coreui.template_utils import utf8quote

%> 

<%
def geta(attr): 
  return args.get(attr,[''])[0]

i = 0
%>
   
<div class="buttonContainer">
     <button id="regSwitchButton" dojoType="dijit.form.Button">  
        Register Switch </button>
     <span class="buttonDivider"></span>

<!--
Right now the approval code is broken with respect to 
reregistering a switch that has been registered and then 
deregistered, so for now we should just prevent deregistration 
to minimize confusion

     <button id="deregSwitchButton" dojoType="dijit.form.Button">  
        Deregister Switch </button>
--> 
     <span class="buttonDivider"></span>
     <button id="remove_principal_button" dojoType="dijit.form.Button">  
        Delete Switch </button>
</div>
${self.refresh_link()} 

<div dojoType="dijit.layout.BorderContainer" id="monitor_content" design="headline" region="center"></div>

<table cellspacing="8" >
<tr class="headerRow">
<th> </th>  
<th><a onclick="javascript:pFilter.sort_clicked('name')"> Name </a> </th>
<th> <a onclick="javascript:pFilter.sort_clicked('dir')">  Directory</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('active_flows')">  Active Flows </a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('flowmiss_rate')">  Flow Miss Rate </a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('total_rx_pkt')">  Rx Packets</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('total_tx_pkt')">  Tx Packets</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('total_dropped_pkt')"> Dropped Packets</a></th>

<th><a onclick="javascript:pFilter.sort_clicked('status')">   Status </a> </th> 
</tr>
<tr class="noxPrincipalGridFilter filterTable" >
<td>  ${self.clear_btn_html()} </td> 
<td> <input type="textbox" id="filter_name" value="${geta('name_glob')}"> </td> 
<td>  <select id="filter_directory">
<option value="${geta('directory')}" selected="true"> ${geta('directory')}</option>  
</select> 
</td>
<td></td>
<td></td>
<td></td>
<td></td>
<td></td>
<td> ${self.status_select_box()} </td>
</tr> 
  <% i = 0 %>  
  % for p_info in p_list:
    <tr class="rowclass${i % 2}">
    <td> <input type="checkbox" class="select-box" id="${p_info['full_name']}"> </td> 
    <td> ${self.infopage_link(p_info)} </td>
    <td> ${p_info["dir"]} </td>
    <td> ${get_not_none(p_info["active_flows"])} </td>
    <td> ${get_not_none(p_info["flowmiss_rate"])} </td> 
    <td> ${get_not_none(p_info["total_rx_pkt"])} </td>
    <td> ${get_not_none(p_info["total_tx_pkt"])} </td>
    <td> ${get_not_none(p_info["total_dropped_pkt"])} </td>
    <td> ${ get_status_markup(p_info["status"]) } </td>
    </tr> 
    <% i += 1 %> 
  % endfor 
</table>

