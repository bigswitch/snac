## -*- coding: utf-8 -*-
##
## auth_error.mako - web portal authentication page displayed when an
##                   unexpected error occurs
##  
<table>
  <tr>
    <td width="540"align="center">
    ネットワークエラーが発生しました。ネットワーク管理者にお問い合わせください。
    </td>
  </tr>
</table>
\
## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
<%def name="page_title()">ネットワークエラー</%def>\
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

