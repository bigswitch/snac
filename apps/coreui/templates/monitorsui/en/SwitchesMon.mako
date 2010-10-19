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

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Switches</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/coreui/monitorsui/SwitchesMon.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.coreui.monitorsui.SwitchesMon");
  dojo.require("dijit.Dialog");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dojox.grid.DataGrid");
</%def>

<%def name="monitor_header()">
  ${parent.monitor_header()}
   <div class="buttonContainer">
     <button jsId="regSwitchButton" dojoType="dijit.form.Button">  
        Register Switch </button>
     <span class="buttonDivider"></span>
     <button jsId="deregSwitchButton" dojoType="dijit.form.Button">  
        Deregister Switch </button>
     <span class="buttonDivider"></span>
     <button id="remove_principal_button" dojoType="dijit.form.Button">  
        Delete Switch </button>
   </div>
</%def>

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <div dojoType="dijit.layout.BorderContainer" jsid="monitor_grid_border_container" design="headline">

## Main table will go here---------------------------------------------------------------
  </div>
</div>
