/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.NetworkOverview");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.apps.coreui.coreui.ItemInspector");
dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.user_event_log.networkevents.NetEvents");
dojo.require("nox.ext.apps.snackui.snackmonitors.NetworkOverviewData");
dojo.require("dijit.form.TextBox"); 
dojo.require("nox.apps.coreui.coreui.simple_config");
dojo.require("nox.ext.apps.snackui.snackmonitors.SnackBarGraphs");

var coreui = nox.apps.coreui.coreui;
var snackmonitors = nox.ext.apps.snackui.snackmonitors;


var barChartModel = []; 

var nox_uptime = null;
var updatemgr = null;
var summaryInspector = null;

var data = null;

function chart_select_changed() { 
  var selected_key = graph_selector.getValue();
  if(selected_key == "" && barChartModel.length > 0) { 
    selected_key = barChartModel[0].key; 
    graph_selector.setValue(selected_key); 
  } 

  var x_axis_text = "";
  for(var i = 0; i < barChartModel.length; i++) {
    var is_visible = barChartModel[i].key == selected_key; 
    barChartModel[i].chart.setVisible(is_visible);
    if(is_visible) 
      x_axis_text = barChartModel[i].chart.x_axis_label; 
  } 
  dojo.byId("chart_x_axis_label").innerHTML = 
    "<center><b>" + x_axis_text + "</b></center>"; 
} 

function chart_step(delta) {
  var cur_index = 0; 
  var selected_key = graph_selector.getValue();
  for(var i = 0; i < barChartModel.length; i++) {
    if(barChartModel[i].key == selected_key) { 
      cur_index = i; 
      break; 
    } 
  }
  var new_index = (cur_index + delta) % barChartModel.length; 
  if (new_index == -1) 
    new_index = barChartModel.length - 1; 
  graph_selector.setValue(barChartModel[new_index].key);
  chart_select_changed(); 
} 

function init_page() { 
    updatemgr = coreui.getUpdateMgr();
    updatemgr.recurrence_period = 10;

    data = new nox.ext.apps.snackui.snackmonitors.NetworkOverviewData({
        updateList: [ "serverinfo", "serverstat", "servercpu", "entitycnts", "policystats" ]
    });

    summaryInspector = new coreui.ItemInspector({
        item: data,
        model: [
            {name: "nox-info", header: "Server Information", separator: true},
            {name: "uptime", header: "Uptime", attr: "uptime_str"},
            {name: "cpu-load", header: "CPU Load", attr: "cpu-load"},
            {name: "flow-load", header: "Flows/sec", get: function (i) {
                return Math.ceil(i.getValue("load"));
            }},
            //{name: "admins", header: "Active Administrators", attr: "active_admins"},
            {name: "entity-cnts", header: "Entity Counts (Active/Total/Unregistered)", separator: true},
            {name: "switch-cnts", header: "Switches", attr: "switch_cnts"},
            {name: "location-cnt", header: "Locations", attr: "location_cnts"},
            {name: "host-cnt", header: "Hosts", attr: "host_cnts"},
            {name: "user-cnt", header: "Users", attr: "user_cnts"},
            {name: "policy-stats", header: "Policy Statistics", separator: true},
            {name: "flow-cnts", header: "Flows Allowed/Denied/Total", attr: "flow_cnts"},
            {name: "total-rules", header: "Total Rules", attr: "num_rules"},
            {name: "exception-rules", header: "Exception Rules", attr: "num_exception_rules"}
        ]
    });
    dojo.byId("stats-inspector").appendChild(summaryInspector.domNode);

    dojo.connect(data, "uptimeUpdated", summaryInspector, "update");

    updatemgr.userFnCall({
        purpose: "Update network overview page data.",
        scope: this,
        fn: function () {
            data.update({
                onComplete: dojo.hitch(summaryInspector, "update"),
                errorHandlers: {}
            });
        },
        recur: true
    });
    
    //FIXME: NetworkOverview.mako currently hardcodes these keys
    var chartNode1 = dojo.byId("top5SwitchConnection"); 
    
    var chartNode2 = dojo.byId("top5LocationBandwidth"); 
    var loc_bw_graph = 
        new snackmonitors.LocationBandwidthBarGraph(chartNode2, {}); 
    barChartModel.push({key :"top5LocationBandwidth", chart : loc_bw_graph}); 
    
     
    var switch_rate_graph = 
        new snackmonitors.SwitchFlowRateBarGraph(chartNode1, {}); 
    barChartModel.push({ key : "top5SwitchConnection", 
                        chart : switch_rate_graph } ); 
      
    var chartNode3 = dojo.byId("top5LocationError"); 
    var loc_error_graph = 
        new snackmonitors.LocationErrorBarGraph(chartNode3, {}); 
    barChartModel.push({key :"top5LocationError", chart : loc_error_graph});        
    dojo.connect(back_button,"onClick",dojo.hitch(dojo.global, chart_step,-1)); 
    dojo.connect(forward_button,"onClick",dojo.hitch(dojo.global,chart_step,1)); 
    
    // hide all but currently selected
    chart_select_changed();
  
    netevent_log = new nox.apps.user_event_log.networkevents.NetEventsTable(dojo.byId("netevents-table"), 30, "max_level=2");

}

dojo.addOnLoad(init_page); 
