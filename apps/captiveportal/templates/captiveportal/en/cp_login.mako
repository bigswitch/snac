## -*- coding: utf-8 -*-
##
## cp_login.mako - captive portal page displayed in main window
##                 before authentication
##
## ---------------------------------------------------------------------------
% if hasattr(session, "server_message"):
<div class="serverMsg">
${session.server_message}
</div>
% endif
\
<div id="heading">
<h1>Authentication Required</h1>
</div>
\
% if login_failed == True:
<div class="errorMsg">
Log in failed, please try again.
</div>
% endif
\
<div id="loginMsg">
Please log in to gain access to the network.
</div>
\
% if p('banner'):
<div id="bannerMsg">
${p('banner')}
</div>
% endif
\
${login_form()}\
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
% if p('org_name') is not None:
${p('org_name')} Network Authentication
% else:
Network Authentication
% endif
</%def>\
\
<%def name="body_args()" filter="trim">
% if not preview:
onload="redirOnTrue('${r['auth_check'] + '&rurl='+rurl+proxy_param}', '', '${r['root']+'?rurl='+rurl + proxy_param}', '${p('auth_check_interval_sec')*1000}')"
% endif
</%def>\
\
<%def name="head_ext()" filter="trim">
  <script type="text/javascript">
    in_progress_message="Logging in, please wait."
  </script>
</%def>\
\
## Login form used here and on the access denied pages.
<%def name="login_form()" filter="trim">
<div id="loginForm">
% if preview:
  <form id="login" name="login" action="" onSubmit="return false;" method="post">
% else:
  <form id="login" name="login" action="${r['root']+"?rurl="+rurl+proxy_param}" method="post" onSubmit="return disableLogin(this)">
% endif
    <table id="loginTable">
      <tr>
        <td align="right">Username:</td>
        <td><input type="text" name="username" tabindex="1" class="textinput"></td>
      </tr>
      <tr>
        <td align="right">Password:</td>
        <td><input type="password" name="password" tabindex="2" class="textinput"></td>
      <tr>
        <td align="center" colspan="2">
        <input name="Log In" type="submit" tabindex="3" value="Log In">
        </td>
      </tr>
    </table>
    <input type="hidden" name="rurl" value="${rurl}">
    <input type="hidden" name="proxy_cookie" value="${proxy_cookie}">
  </form>
</div>
</%def>\
\
