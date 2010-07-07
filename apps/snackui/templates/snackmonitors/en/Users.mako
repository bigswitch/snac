## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Users</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/snackmonitors/Users.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("nox.ext.apps.snackui.snackmonitors.Users");
</%def>

<%def name="monitor_header()">
  <div class="buttonContainer">
    <button dojoType="dijit.form.Button" id="add_principal_button">Create User</button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" id="remove_principal_button">Delete User</button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" id="deauth_principal_button">
        Deauthenticate User </button>
  </div>
</%def>


## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.BorderContainer" id="monitor_content" jsid="monitor_content" design="headline" region="center"></div>
