/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.SnackBarGraphs");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.coreui.coreui._UpdatingBarGraph"); 
dojo.require("nox.apps.directory.directorymanagerws.Switch"); 
dojo.require("nox.apps.directory.directorymanagerws.SwitchPort"); 

dmws = nox.apps.directory.directorymanagerws; 

// this is a hack to generate a switch port link from a switch 
// and port name in a way that should still work if we change
// the URLs.  
function make_switchport_link(switch_name, port_name) { 

      var fake_switch = new dmws.Switch({name: switch_name});
      fake_switch.setValue("name", switch_name); 
      var fake_loc = new dmws.SwitchPort({  name: port_name, 
                                            switchObj: fake_switch
                                        });
      fake_loc.setValue("name", port_name); 
      return fake_loc.uiMonitorPath(); 
} 

dojo.declare("nox.ext.apps.snackui.snackmonitors.LocationBandwidthBarGraph", 
            [nox.apps.coreui.coreui._UpdatingBarGraph], {

  _url : "/ws.v1/nox/heavyhitters/port_bw",  
  x_axis_label : "Tx Bandwidth (KB/second)",

  _get_graph_items: function(response) { 
    
    // expect sorted data from the webservice 
    var to_graph = []; 
    for(var i = 0; i < response.length; i++) { 
      var name = response[i].name;
      var val = response[i].value / 1000; // do KB/s
      var link = make_switchport_link(response[i].switch_name,
                                      response[i].port_name); 
      to_graph.push({   label_text : name, 
                        tooltip: val + " KB/s", 
                        value: val, 
                        link: link 
                    }); 
                      
    }
    return to_graph; 
  }

}); 

dojo.declare("nox.ext.apps.snackui.snackmonitors.LocationErrorBarGraph", 
            [nox.apps.coreui.coreui._UpdatingBarGraph], {

  _url : "/ws.v1/nox/heavyhitters/port_err",  
  x_axis_label : "Port Errors (total)",

  _get_graph_items: function(response) { 
    
    // expect sorted data from the webservice 
    var to_graph = []; 
    for(var i = 0; i < response.length; i++) { 
      var name = response[i].name;
      var val = response[i].value;
      var link = make_switchport_link(response[i].switch_name,
                                      response[i].port_name); 
      to_graph.push({   label_text : name , 
                        tooltip: val + " Errors", 
                        value: val, 
                        link: link
                    }); 
                      
    }
    return to_graph; 
  } 

}); 

dojo.declare("nox.ext.apps.snackui.snackmonitors.SwitchFlowRateBarGraph", 
            [nox.apps.coreui.coreui._UpdatingBarGraph], {

  _url : "/ws.v1/nox/heavyhitters/switch_p_s",  
  x_axis_label : "Flow Setup Rate (flows/second)",

  _get_graph_items: function(response) { 
    
    // expect sorted data from the webservice 
    var to_graph = []; 
    for(var i = 0; i < response.length; i++) { 
      var name = response[i][0];
      var swObj = new dmws.Switch({ name: name });
      swObj.setValue("name", name); 
      var val = response[i][1];
      to_graph.push({ label_text: name , 
                      tooltip: val + " conn/sec", 
                      value: val, 
                      link: swObj.uiMonitorPath()
                    }); 
                      
    }
    return to_graph; 
  }
}); 
