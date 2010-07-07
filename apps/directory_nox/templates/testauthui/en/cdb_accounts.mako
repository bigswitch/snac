##
## auth.mako - web portal authentication apge
##
## ---------------------------------------------------------------------------
<h1>CDB Authentication Users</h1>
<A HREF="cdb/auth">Test Authentication</A>
% if users is None:
<p>Failed to query users</p>
% else:
<p>The following users are configured in CDB: </p>
${user_table()}
% endif
<br>
<A HREF="cdb/user">Create New User</A>

## ---------------------------------------------------------------------------

<%inherit file="base.mako"/>

<%def name="page_title()">CDB Authentication Users</%def>

## Login form used here and on the access denied pages.
<%def name="user_table()">
  <table border="1">
    <tr>
      <th>User ID</th>
      <th>Username</th>
      <th>Real Name</th>
      <th>NOX Role</th>
    </tr>
    %for user in users:
        <tr>
          <td>${user.user_id}</td>
          <td><A HREF="cdb/user/${user.username}">${user.username}</A></td>
          <td>${user.user_real_name}</td>
          <td>${user.nox_role}</td>
        </tr>
    %endfor
  </table>
</%def>
