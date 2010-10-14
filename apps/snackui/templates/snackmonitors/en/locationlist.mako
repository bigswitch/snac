## -*- coding: utf-8 -*-

<%inherit file="principallist_base.mako"/>
<%def name="page_title()">Locations</%def>
<%def name="head_js()">
  ${parent.head_js()} 
  
  var pFilter = null;
  dojo.addOnLoad(function () {
      var filters = nox.ext.apps.directory.directorymanagerws.PrincipalListFilter; 
      pFilter = filters.init_principal_list_page("location");
  }); 
</%def>

<%def name="infopage_link(p_info)">
<% full_switch_name = mangle_name(p_info["dir"],p_info["switch_name"]) %> 
<a onclick="javascript:change_main_page('/Monitors/Switches/SwitchPortInfo?switch=${utf8quote(full_switch_name)}&port=${utf8quote(p_info['port_name'])}')"> ${p_info["full_name"]} </a> 
</%def> 

<%def name="switch_infopage_link(p_info)"> 
<% full_switch_name = mangle_name(p_info["dir"],p_info["switch_name"]) %> 
<a href="#" onclick="javascript:change_main_page('/Monitors/Switches/SwitchInfo?name=${utf8quote(full_switch_name)}')"> ${p_info["switch_name"]} </a> 
</%def> 

## ---------------------------------------------------------------------------

<%!
from nox.ext.apps.directory.directorymanager import demangle_name,mangle_name
from nox.ext.apps.snackui.principal_list_pages import get_status_markup
from nox.ext.apps.coreui.template_utils import utf8quote
from nox.webapps.webservice.web_arg_utils import get_html_for_select_box
%> 
<%
def geta(attr): 
  return args.get(attr,[''])[0]
 
%> 
${self.refresh_link()} 
<div dojoType="dijit.layout.BorderContainer" id="monitor_content" design="headline" region="center"></div>

 
<table cellspacing="8" >
<tr class="headerRow">
<th> </th>  
<th><a onclick="javascript:pFilter.sort_clicked('name')"> Name </a> </th>
<th> <a onclick="javascript:pFilter.sort_clicked('dir')">  Directory</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('switch_name')">  Switch</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('port_name')">  Port</a></th>
<th><a onclick="javascript:pFilter.sort_clicked('status')">   Status </a> </th> 
</tr>
<tr class="noxPrincipalGridFilter filterTable" >
<td>${self.clear_btn_html()} </td> 
<td> <input type="textbox" id="filter_name" value="${geta('name_glob')}"> </td> 
<td>  <select id="filter_directory">
<option value="${geta('directory')}" selected="true"> ${geta('directory')}</option>  
</select> 
</td>
<td> <input type="textbox" id="filter_switch_name" size="16" value="${geta('switch_name')}"> </td> 
<td>
${get_html_for_select_box(unique_ports, geta('port_name'), [('id','filter_port_name')]) } 
</td>
<td> 
${self.status_select_box()} 
</td> 
</tr>
  <% i = 0 %>  
  % for p_info in p_list:
    <% print "pinfo: %s" % str(p_info) %> 
    <tr class="rowclass${i % 2}">
    <td> </td> 
    <td> ${self.infopage_link(p_info)} </td>
    <td> ${p_info["dir"]} </td>
    <td> ${self.switch_infopage_link(p_info)} </td>
    <td> ${p_info["port_name"] } </td> 
    <td> ${ get_status_markup(p_info["status"]) } </td> 
    </tr> 
    <% i += 1 %> 
  % endfor 
</table>

