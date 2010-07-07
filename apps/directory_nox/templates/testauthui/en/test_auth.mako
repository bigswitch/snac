##
## test_auth.mako - web portal authentication apge
##
## ---------------------------------------------------------------------------
<h1>User Authentication Test</h1>
<p><A HREF="testauth/cdb">Manage CDB Accounts</A></p>

% if invalid_param is True:
<P>Invalid parameter(s) specified, please try again.</P>
% endif

% if failure:
  <P><span class="errmsg">Authentication system failure: '${failure}'</span></P>
% endif

% if is_auth:
%   if authresult == 0:
      <P><span class="errormsg">Authentication successful.</span></P>
%   else:
      <P><span class="errormsg">Authentication failed: ${authresult}</span></P>
%   endif
% endif

<p>Please enter a username and password to test authentication.</p>
${auth_form()}

## ---------------------------------------------------------------------------

<%inherit file="base.mako"/>

<%def name="page_title()">CDB Authentication Test</%def>

## Authentication form used here
<%def name="auth_form()">
  <form name="auth" action="/testauth" method="post">
    <table>
      <tr>
        <td align="right">Method:</td>
        <td>
          <select name="method" tabindex="1">
            <option value="all">All
            <option value="cdb">CDB
            <option value="ldap" selected="selected">LDAP
          </select>
        </td>
      </tr>
      <tr>
        <td align="right">Username:</td>
        <td><input type="text" name="username" tabindex="2"/></td>
      </tr>
      <tr>
        <td align="right">Password:</td>
        <td><input type="password" name="password" tabindex="3"/></td>
      <tr>
        <td align="center" colspan="2">
        <button name="Log In" type="submit" tabindex="4" onclick="document.auth.submit()">Log In</button>
        </td>
      </tr>
    </table>
  </form>
</%def>
