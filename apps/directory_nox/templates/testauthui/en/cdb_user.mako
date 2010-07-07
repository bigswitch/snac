##
## auth.mako - web portal authentication apge
##
## ---------------------------------------------------------------------------
<h1>CDB Authentication User</h1>
<A HREF="/testauth/cdb">See All Users</A>
% if user is None or len(user) == 0:
${create_user_table()}
% else:
${user_table()}
% endif

## ---------------------------------------------------------------------------

<%inherit file="base.mako"/>

<%def name="page_title()">CDB Authentication Users</%def>

<%def name="create_user_table()">
  <br>
  <br>
  <form name="newuser" action="user" method="post">
    <table border="1">
      <tr>
        <th>Field</th>
        <th>Value</th>
      </tr>
      <tr>
        <td>USER_ID</td>
        <td>Not settable for now</td>
      </tr>
      <tr>
        <td>USERNAME</td>
        <td><input type="text" name="USERNAME" tabindex="1"/></td>
      </tr>
      <tr>
        <td>PASSWORD</td>
        <td><input type="text" name="PASSWORD" tabindex="2"/></td>
      </tr>
      <tr>
        <td>PASSWORD_EXPIRE_EPOCH</td>
        <td><input type="text" name="PASSWORD_EXPIRE_EPOCH" tabindex="2"/></td>
      </tr>
      <tr>
        <td>USER_REAL_NAME</td>
        <td><input type="text" name="USER_REAL_NAME" tabindex="3"/></td>
      </tr>
      <tr>
        <td>DESCRIPTION</td>
        <td><input type="text" name="DESCRIPTION" tabindex="4"/></td>
      </tr>
      <tr>
        <td>LOCATION</td>
        <td><input type="text" name="LOCATION" tabindex="5"/></td>
      </tr>
      <tr>
        <td>PHONE</td>
        <td><input type="text" name="PHONE" tabindex="6"/></td>
      </tr>
      <tr>
        <td>USER_EMAIL</td>
        <td><input type="text" name="USER_EMAIL" tabindex="7"/></td>
      </tr>
      <tr>
        <td>NOX_ROLE</td>
        <td><input type="text" name="NOX_ROLE" tabindex="8"/></td>
      </tr>
      <tr>
          <td align="center" colspan="2">
            <button name="Submit" type="submit" tabindex="9" 
             onclick="document.newuser.submit()">SUBMIT</button>
          </td>
      </tr>
    </table>
  </form>
</%def>

<%def name="user_table()">
  <p>The following user is configured in CDB</p>
  <table border="1">
    <tr>
      <th>Field</th>
      <th>Value</th>
    </tr>
    <%
      cols = user[0].get_columns()
      cols.sort()
    %>
    %for field in cols:
        <tr>
          <td>${field}</td>
          <%
            import urllib
            val = '&lt;Not Set&gt;'
            if hasattr(user[0], field.lower()):
                v = str(getattr(user[0], field.lower()))
                val = urllib.quote(v, ' \t@')
          %>
          <td>${val}</td>
        </tr>
    %endfor
  </table>
</%def>
