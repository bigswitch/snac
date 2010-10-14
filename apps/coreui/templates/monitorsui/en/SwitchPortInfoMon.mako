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
<%def name="page_title()">&nbsp;</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox.ext.apps.user_event_log/networkevents/NetEvents.css"; 
  @import "/static/nox.ext.apps.coreui/coreui/ItemInspector.css";
  @import "/static/nox.ext.apps.coreui/coreui/ItemList.css";
  @import "/static/nox.ext.apps.coreui/monitorsui/SwitchPortInfoMon.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("dijit.TitlePane");
  dojo.require("nox.ext.apps.coreui.monitorsui.SwitchPortInfoMon");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_switch = "${unicode(request.args.get('switch',[''])[-1], 'utf-8')}";
  var selected_port = "${unicode(request.args.get('port',[''])[-1], 'utf-8')}";
</%def>

<%def name="monitor_header()">
  ${parent.monitor_header()}
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <div style="display: none" id="invalid-switch-error">
    <span class="errormsg">An invalid switch was specified.</span>
    You can select a valid switch from the
    <a href="/Monitors/Switches">Switches page</a>.
  </div>

  <div style="display: none" id="invalid-port-error">
    <span class="errormsg">An invalid switch port was specified.</span>
    You can select a valid switch port from the
    <a id="error-switch-page-ref" href="">Switches page</a>.
  </div>

  <div id="switch-port-info"></div>

  <div dojoType="dijit.TitlePane" title="NAT Configuration">
    <div id="nat-port-config"></div> 
  </div>

  <div dojoType="dijit.TitlePane" title="Related Network Events">
  <div dojoType="dijit.layout.ContentPane">

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
  </div>  

</div>
