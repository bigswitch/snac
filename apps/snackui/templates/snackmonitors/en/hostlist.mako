## -*- coding: utf-8 -*-
<%inherit file="principallist_base.mako"/>

<%def name="page_title()">Hostlist</%def>
<%def name="head_js()">
  ${parent.head_js()} 
 
  var pFilter = null;
  dojo.addOnLoad(function () {
      var filters = nox.netapps.directory.directorymanagerws.PrincipalListFilter; 
      pFilter = filters.init_principal_list_page("host");
  });
</%def> 

<%def name="infopage_link(p_info)"> 
<a href="#" onclick="javascript:change_main_page('/Monitors/Hosts/HostInfo?name=${utf8quote(p_info['full_name'])}')"> ${p_info["name"]} </a> 
</%def> 
## ---------------------------------------------------------------------------
<%!
from nox.netapps.directory.directorymanager import demangle_name
from nox.ext.apps.snackui.principal_list_pages import get_status_markup
from nox.webapps.coreui.template_utils import utf8quote

%> 
<%
def geta(attr): 
  return args.get(attr,[''])[0]

##for key,val in args.iteritems(): 
##  context.write("arg: %s : %s <br>" % (str(key),str(val)))
##context.write("<br>")

%>
<div class="buttonContainer">
    <button dojoType="dijit.form.Button" id="add_principal_button">Create Host</button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" id="remove_principal_button">Delete Host</button>
</div>
${self.refresh_link()} 

<div dojoType="dijit.layout.BorderContainer" id="monitor_content" design="headline" region="center"></div>


<table cellspacing="8" >
<tr class="headerRow">
<th> </th>  
<th><a onclick="javascript:pFilter.sort_clicked('name')"> Name </a> </th>
<th> <a onclick="javascript:pFilter.sort_clicked('dir')">  Directory</a></th>
<th> <a onclick="javascript:pFilter.sort_clicked('ip_str')">  IP Address </a> </th>
<th> <a onclick="javascript:pFilter.sort_clicked('mac_str')">  MAC Address </a> </th> 
<th> <a onclick="javascript:pFilter.sort_clicked('loc_str')">  Location </a> </th>
<th><a onclick="javascript:pFilter.sort_clicked('status')">   Status </a> </th> 
</tr>
<tr class="noxPrincipalGridFilter filterTable" >
<td>${self.clear_btn_html()} </td> 
<td> <input type="textbox" id="filter_name" value="${geta('name_glob')}"> </td> 
<td>  <select id="filter_directory">
<option value="${geta('directory')}" selected="true"> ${geta('directory')}</option>  
</select> 
</td>
<td> <input type="textbox" id="filter_ip" size="16" value="${geta('nwaddr_glob')}"> </td> 
<td> <input type="textbox" id="filter_mac" value="${geta('dladdr_glob')}"> </td> 
<td> <input type="textbox" id="filter_loc" value="${geta('location_name_glob')}"></td> 
<td> 
${self.status_select_box()} 
</td> 
</tr>
  <% i = 0 %>  
  % for p_info in p_list:
    <tr class="rowclass${i % 2}">
    <td> <input type="checkbox" class="select-box" id="${p_info['full_name']}"> </td> 
    <td> ${self.infopage_link(p_info)} </td>
    <td> ${p_info["dir"]} </td>
    <td> ${p_info["ip_str"] } </td>
    <td> ${p_info["mac_str"] } </td>
    <td> ${p_info["loc_str"] } </td>
    <td> ${ get_status_markup(p_info["status"]) } </td> 
    </tr> 
    <% i += 1 %> 
  % endfor 
</table>

