## -*- coding: utf-8 -*-

## Copyright 2008 (C) Nicira, Inc.
##
## This file is part of NOX.
##
## NOX is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## NOX is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with NOX.  If not, see <http://www.gnu.org/licenses/>.

## TBD: Things to enhance on this page include:
## TBD:   - Add update time to component status info.
## TBD:   - Keep table headers while scrolling components list items.

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Status</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox.ext.apps.coreui/monitorsui/NOXStatusMon.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dojo.data.ItemFileReadStore");
  dojo.require("nox.ext.apps.coreui.monitorsui.NOXStatusMon");
</%def>

<%def name="monitor_header()">
<div class="sectionSubHeading">
  <div class="statusHeaderContainer">
 	<div class="label headerLeft"><h3>Overall Status</h3></div>
	<div class="label headerMid"><h3>System Uptime</h3></div>
	<div class="label headerRight"><h3>NOX Version</h3></div>
  </div>
  <div class="toggleHeaderContainer">
    <div id="overall_status_field"></div>
    <div id="uptime_field"></div>
    <div id="version_field"></div>
  </div>
</div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center" style="padding-right:0;">

  <div id="components" dojoType="dijit.layout.ContentPane" region="center" class="componentHeaderContainerWrap">
    <div dojoType="dijit.layout.ContentPane">
      <div class="componentHeaderContainer">
      	<div class="current_state headerLeft"><h3>Current State</h3></div>
		<div class="name headerMid"><h3>Component Name</h3></div>
        <div class="version headerMid"><h3>Version</h3></div>
        <div class="required_state headerRight"><h3>Required State</h3></div>
      </div>
    </div>

    <div id="component-data" dojoType="dijit.layout.ContentPane">
      <table id="components-table" class="components">
        <!-- Dummy row to make browser table layout/Javascript happy... -->
        <tr>
        <td class="current_state"></td>
        <td class="name"></td>
        <td class="version"></td>
        <td class="required_state"></td>
        </tr>
      </table>
    </div>
  </div>

</div>
