## -*- coding: utf-8 -*-
<%inherit file="base.mako"/>

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

<%def name="head_css()"> 
  @import "/static/nox/ext/apps/snackui/snackmonitors/PrincipalList.css";
</%def> 
<%def name="head_js()"> 
${parent.head_js()} 
  function change_main_page(url) { 
    top.location = url; 
  } 
</%def> 
<%!
from nox.ext.apps.coreui.template_utils import utf8quote
%>

<table> 
<tr class="headerRow">
<th> Policy Rule </th> 
<th> Matches </th>
</tr>
<% i = 0 %>  
%for flow in readable_flows: 
<tr class="rowclass${i % 2}">
<td> <a onclick="javascript:change_main_page('/Monitors/FlowHistory?hostname=${utf8quote(hostname)}&policy_id=${flow['policy_id']}&rule_id=${flow['rule_id']}')"> 
  ${flow['rule_text']} </a> </td> 
<td> ${flow['matches']} </td> 
</tr> 
<% i += 1 %> 
%endfor 
</table>
% if len(readable_flows) == 0:
<center><h2> No Flows Found </h2></center> 
% else:
<br> 
<center> <a onclick="javascript:change_main_page('/Monitors/FlowHistory?hostname=${utf8quote(hostname)}')"> View Detailed Flow List </a></center>   
% endif
