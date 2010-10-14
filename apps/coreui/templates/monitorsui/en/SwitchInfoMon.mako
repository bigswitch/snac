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

## TBD: - add "tables" stats
## TBD: - add more switch configuration information
## TBD: - provide method of baselining stats.

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">&nbsp;</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox.ext.apps.coreui/coreui/ItemTable.css";
  @import "/static/nox.ext.apps.coreui/coreui/ItemInspector.css";
  @import "/static/nox.ext.apps.coreui/coreui/ItemList.css";
  @import "/static/nox.ext.apps.coreui/monitorsui/SwitchInfoMon.css";
  @import "/static/nox.netapps.user_event_log/networkevents/NetEvents.css"; 
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.coreui.monitorsui.SwitchInfoMon");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.TitlePane");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_switch = "${unicode(request.args.get('name', [''])[-1], 'utf-8')}";
</%def>

<%def name="monitor_header()">
  ${parent.monitor_header()}
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <div class="buttonContainer">
    <button dojoType="dijit.form.Button" jsid="reset_button">
      Reset Switch
      <script type="dojo/method" event="onClick">reset();</script>
    </button>
<!-- Switch updates may not be fully automated, so disable this for now   
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="update_button">
      Update Switch
      <script type="dojo/method" event="onClick">update();</script>
    </button>
    -->
  </div>
  <div style="display: none" id="invalid-switch-error">
    <span class="errormsg">An invalid switch name was specified.</span>
    You can select an existing switch on the
    <a href="/Monitors/Switches">Switches page</a>.
  </div>

  <div id="switch-info"></div>

  <div dojoType="dijit.TitlePane" title="Ports">
    <div id="port-table"></div>
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

## switch reset/update confirmation dialog

<div id="reset_confirmation_dialog" dojoType="dijit.Dialog"
     title="Confirmation"> 
  <table> 
    <tr> <td> Are you sure you want to reset the switch? </td></tr> 
    <tr><td> 
        <button dojoType="dijit.form.Button">
          OK
          <script type="dojo/method" event="onClick">
            reset_ok();
          </script>
        </button>
        <button dojoType="dijit.form.Button">
          Cancel
          <script type="dojo/method" event="onClick">
             dijit.byId("reset_confirmation_dialog").hide();
          </script>
        </button>
    </td></tr>
  </table> 
</div>

<div id="update_confirmation_dialog" dojoType="dijit.Dialog"
     title="Confirmation">       
  <table> 
    <tr> <td> Are you sure you want to update the switch? </td></tr> 
    <tr><td> 
        <button dojoType="dijit.form.Button">
          OK
          <script type="dojo/method" event="onClick">
            update_ok();
          </script>
        </button>
        <button dojoType="dijit.form.Button">
          Cancel
          <script type="dojo/method" event="onClick">
             dijit.byId("update_confirmation_dialog").hide();
          </script>
        </button>
    </td></tr>
  </table> 
</div>
