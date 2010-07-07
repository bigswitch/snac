## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Groups</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  //dojo.require("nox.ext.apps.snackui.snackmonitors.Groups");
</%def>

<%def name="head()">
  ${parent.head()}
  <script type="text/javascript" src="/static/nox/ext/apps/snackui/snackmonitors/Groups.js"></script>
</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/snackmonitors/Groups.css";
</%def>

## ---------------------------------------------------------------------------

<table class="itemRows">
  <tr class="headerRow"><th id="group-type-column">Group Type</th><th id="count-column">Count</th></tr>
  <tbody class="itemRows">
    <tr class="rowclass0">
      <td><a href="/Monitors/Groups/SwitchGroups">Switch Groups</a></td>
      <td id="switch-group-count">-</td>
    </tr>
    <tr class="rowclass1">
      <td><a href="/Monitors/Groups/HostGroups">Host Groups</a></td>
      <td id="host-group-count">-</td>
    </tr>
    <tr class="rowclass0">
      <td><a href="/Monitors/Groups/UserGroups">User Groups</a></td>
      <td id="user-group-count">-</td>
    </tr>
      <tr class="rowclass1">
      <td><a href="/Monitors/Groups/LocationGroups">Location Groups</a></td>
      <td id="location-group-count">-</td>
    </tr>
      <tr class="rowclass0">
      <td><a href="/Monitors/Groups/NWAddrGroups">Network Address Groups</a></td>
      <td id="nwaddr-group-count">-</td>
    </tr>
  </tbody>
</table>
