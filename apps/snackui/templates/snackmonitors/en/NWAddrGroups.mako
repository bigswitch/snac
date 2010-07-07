## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Host Groups</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/snackmonitors/NWAddrGroups.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.snackui.snackmonitors.NWAddrGroups");
</%def>

<%def name="monitor_header()">
  <div class="buttonContainer">
    <button dojoType="dijit.form.Button" id="add_group_button">Create Group</button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" id="remove_group_button">Delete Group</button>
  </div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.BorderContainer" id="monitor_content" jsid="monitor_content" design="headline" region="center">
</div>
