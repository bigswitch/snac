## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Overview</%def>

<%def name="dojo_imports()">
   ${parent.dojo_imports()}
   @import "/static/nox/apps/coreui/coreui/ItemInspector.css";
   @import "/static/nox/ext/apps/snackui/snackmonitors/HostInfo.css";
   @import "/static/nox/apps/user_event_log/networkevents/NetEvents.css";
   @import "/static/nox/ext/apps/snackui/snackmonitors/NetworkOverview.css";
</%def>

<%def name="dojo_requires()">
   ${parent.dojo_requires()}
   dojo.require("nox.ext.apps.snackui.snackmonitors.NetworkOverview");
   dojo.require("dijit.form.FilteringSelect");
   dojo.require("dijit.form.Button");
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <table id="layout1">
    <tr>
      <td id="statsContainer"><div id="stats-inspector"></div></td>
      <td class="graphsContainer">
	    <div id="graphs">
		  <div class="chartsControls">
		  	<div class="chartsFilterLeft">
		  	  <select dojoType="dijit.form.FilteringSelect"
          	    name="chartsControlsLeft"
                jsId="graph_selector"
          	    autocomplete="false"
                onChange="chart_select_changed();"
          	    <option value="top5LocationBandwidth" >
                Top 5 Switch Ports by Tx Bandwidth</option>
          	  	<option value="top5SwitchConnection">
                Top 5 Switches by Flow Setup Rate</option>
          	    <option value="top5LocationError" >
                Top 5 Switch Ports by Error Counts</option>
          	  </select>
		  	</div>
        <!--
		  	<div class="chartsFilterRight">
		  	  <select dojoType="dijit.form.FilteringSelect"
          	    name="chartsControlsRight"
          	    autocomplete="false"
          	    value="internal">
          	  	<option value="internal" selected="selected">Only internal</option>
          	      <option value="external" >Only external</option>
          	  </select>
		  	</div>
        --> 
	    	<div class="chartButtons">
          	  <div class="buttonBack">
              <button dojoType="dijit.form.Button" jsId="back_button"
                type="back" iconClass="chartsBack">
                </button>
              </div>
<!--			  <div class="buttonCycle">
          <button dojoType="dijit.form.Button" type="cycle" iconClass="chartsCycle"></button></div> --> 
			  <!--<div class="buttonPause"><button dojoType="dijit.form.Button" type="pause" iconClass="chartsPause"></button></div>-->
	          <div class="buttonForward">
            <button dojoType="dijit.form.Button" jsId="forward_button"
                    type="forward" iconClass="chartsForward">
            </button>
            </div>
	   		</div>		  
		  </div>
      <div style="background-color: white"> 
      <div id="top5SwitchConnection" style="background-color: white; width: 475px; height: 326px;">
      </div>
      <div id="top5LocationBandwidth" style="background-color: white; width: 475px; height: 326px;">
      </div>
      <div id="top5LocationError" style="background-color: white; width: 475px; height: 326px;">
      </div>
       <br> <br> 
       </div> 
      <div id="chart_x_axis_label" style="background-color: white"></div> 
		</div>
	  </td>
    </tr>
  </table>

  <h2>Recent Events</h2>

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
