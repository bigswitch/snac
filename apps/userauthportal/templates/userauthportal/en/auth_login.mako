## -*- coding: utf-8 -*-
##
## auth_login.mako - captive portal auth page displayed in main window
##                   before authentication
##
## ---------------------------------------------------------------------------

% if login_failed == True:
<p><span class="errormsg">Log in failed, please try again.</span></p>
% endif
% if dev_fake == True:
<p><span class="errormsg">No Openflow access point information provided,
simulating to ease development.</span></p>
% endif
<h1>Authentication Required</h1>
<p>Please log in to gain access to the network.</p>
<div id="login-message">
${c.message}
</div>
<br>
${login_form()} \
\
## ---------------------------------------------------------------------------
\
<%inherit file="auth_base.mako"/>
\
<%def name="page_title()" filter="trim">
${c.org_name} Network Access Authentication
</%def>\
\
<%def name="body_args()" filter="trim">
% if is_popup is True:
onload="redirectParent('${r.auth}?e=1'); close()"
% else:
onload="watchForAuth('${r.check_for_auth}', '${r.success}', '${c.auth_check_interval_ms}')"
%endif
</%def> \
\
## Login form used here and on the access denied pages.
<%def name="login_form()" filter="trim">
  <div id="login-form">
  <form id="login" name="login" action="${r.do_login}" method="post" onSubmit="lopu(this, '${r.opening_pu}', '${r.wait_for_pu}')">
    <table>
      <tr>
        <td align="right">Username:</td>
        <td><input type="text" name="username" tabindex="1"></td>
      </tr>
      <tr>
        <td align="right">Password:</td>
        <td><input type="password" name="password" tabindex="2"></td>
      <tr>
        <td align="center" colspan="2">
        <input name="Log In" type="submit" tabindex="3" value="Log In">
        </td>
      </tr>
    </table>
    <input type="hidden" name="pu" value="0">
    <input type="hidden" name="havepu" value="0">
    ${self.ses_post_form_inputs()}
  </form>
  </div>
</%def> \
\
