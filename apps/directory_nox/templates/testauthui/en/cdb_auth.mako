##
## auth.mako - web portal authentication apge
##
## ---------------------------------------------------------------------------
<h1>CDB Authentication Test</h1>

% if invalid_param is True:
<P>Invalid parameter(s) specified, please try again.</P>
% endif

% if is_auth:
%   if authresult is None:
      <P><span class="errormsg">Authentication failed</span></P>
%   else:
      <P><span class="errormsg">Authentication successful.</span></P>
%   endif
% endif

<p>Please enter a username and password to test authentication.</p>
${login_form()}

## ---------------------------------------------------------------------------

<%inherit file="base.mako"/>

<%def name="page_title()">CDB Authentication Test</%def>

## Login form used here and on the access denied pages.
<%def name="login_form()">
  <form name="login" action="auth" method="post">
    <table>
      <tr>
        <td align="right">Username:</td>
        <td><input type="text" name="username" tabindex="1"/></td>
      </tr>
      <tr>
        <td align="right">Password:</td>
        <td><input type="password" name="password" tabindex="2"/></td>
      <tr>
        <td align="center" colspan="2">
        <button name="Log In" type="submit" tabindex="3" onclick="document.login.submit()">Log In</button>
        </td>
      </tr>
    </table>
  </form>
</%def>
