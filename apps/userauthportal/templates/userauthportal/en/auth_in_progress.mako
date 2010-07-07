## -*- coding: utf-8 -*-
##
## auth_in_progress.mako - web portal authentication page displayed when 
##                         checking credentials
##  
<table>
  <tr>
    <td width="540"align="center">
      Logging in, please wait.
    </td>
  </tr>
</table>
\
## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
\
<%def name="page_title()" filter="trim">${c.org_name} Network Authentication</%def>
\
## TODO: it would be nice to support js refreshes if they are available
<%def name="meta_tags()" filter="trim">
% if (refresh_ms is not UNDEFINED) and (refresh_url is not UNDEFINED):
  <meta http-equiv="refresh" content="${refresh_ms/1000};url=${refresh_url}"/>
% endif
</%def>
\
<%def name="header()" filter="trim">
<table width="294" cellpadding="0" cellspacing="0" border="0" align="center" bgcolor="#FFFFFF" style="background: white; border-bottom: 1px solid #199;  border-top: 1px solid #199; border-left: 1px solid #199; border-right: 1px solid #199; padding: 1px solid #199;" >
  <tr>
    <td align="center">
      <img src="${c.logo_sm}" alt="${c.org_name}"/>
    </td>
  </tr>
  <tr>
    <td align="center">
</%def>
\
<%def name="footer()" filter="trim">
    </td>
  </tr>
  <tr>
    <td class="footer" height="10">
    </td>
  </tr>
</table>
</%def>


