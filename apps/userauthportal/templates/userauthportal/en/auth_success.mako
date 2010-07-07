## -*- coding: utf-8 -*-
##
## auth_success.mako - captive portal auth page displayed in main window
##                     after successfull authentication
## 
%if username:
<p>You are now logged in as '${username}'.</p>
%else:
<h3>Log in successful.</h3>
%endif
<table>
  <tr>
    <td width="540"align="center">
%if redir_url != None:
    In a moment, you should be redirected to your <A href="${redir_url}">original destination</A>.
    If you are not redirected, you can click <A href="${redir_url}">here</A>, or reissue your request.
    </td>
  </tr>
%else:
    Please reissue your request to continue to your original destination.
%endif
    </td>
  </tr>
</table>

## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
<%def name="page_title()">Log in Successful</%def>

<%def name="meta_tags()">
%if redir_url != None:
  <meta http-equiv="refresh" content="3;url=${redir_url}"/>
%endif
</%def>

