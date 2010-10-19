## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Network Events Log</%def>

<%def name="dojo_imports()">
   ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/user_event_log/networkevents/NetEvents.css";
</%def>

<%def name="dojo_requires()">
   ${parent.dojo_requires()}
   dojo.require("nox.ext.apps.snackui.snackmonitors.NetEventsMon");
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">
  <div dojoType="dijit.layout.ContentPane">
    <table id="netevents-header-table" class="log">
      <tr id="netevents-header-table">
        <th class="priority">Priority</th>
        <th class="timestamp">Timestamp</th>
        <th class="message">Message</th>
      </tr>
    </table>
  </div>

  <div dojoType="dijit.layout.ContentPane">
    <table id="netevents-table" class="log">
      <!-- Dummy row to make browser table layout/Javascript happy... -->
      <tr>
      <td class="priority"></td>
      <td class="timestamp"></td>
      <td class="message"></td>
      </tr>
    </table>
  </div>

</div>
