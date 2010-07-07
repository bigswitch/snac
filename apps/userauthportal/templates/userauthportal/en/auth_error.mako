## -*- coding: utf-8 -*-
##
## auth_error.mako - web portal authentication page displayed when an
##                   unexpected error occurs
##  
<table>
  <tr>
    <td width="540"align="center">
    An unexpected error has occurred.
    </td>
  </tr>
% if msg:
  <tr>
    <td width="540"align="center">
      Details: ${msg}
    </td>
  </tr>
% endif
  <tr>
    <td width="540"align="center">
    If you are experiencing network problems, please contact your network
    administrator.
    </td>
  </tr>
</table>
\
## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
<%def name="page_title()">Network Access Authentication Error</%def>\
\
<%def name="redir_url()" filter="trim">
% if msg:
<%
  import urllib
  qmsg = urllib.quote(msg)
%>
${r.error}?msg=${qmsg}
% else:
${r.error}
% endif:
</%def> \
\
<%def name="body_args()" filter="trim">
% if close_if_pu:
onload="if (window.name=='lopu') {redirectParent('${redir_url()}'); close();}"\
% endif
</%def> \

