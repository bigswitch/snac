## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Locations</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/snackmonitors/Locations.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("nox.ext.apps.snackui.snackmonitors.Locations");
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.BorderContainer" id="monitor_content" jsid="monitor_content" design="headline" region="center">
</div>
