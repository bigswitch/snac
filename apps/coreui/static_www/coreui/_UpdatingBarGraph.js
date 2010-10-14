/*
 Copyright 2008 (C) Nicira, Inc.

 This file is part of NOX.

 NOX is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 NOX is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

dojo.provide("nox.ext.apps.coreui.coreui._UpdatingBarGraph");
dojo.require("dojox.charting.Chart2D");
dojo.require("dojox.charting.themes.Grasshopper");
dojo.require("dojox.charting.action2d.Tooltip");

dojo.require("nox.ext.apps.directory.directorymanagerws.Location"); 
dmws = nox.ext.apps.directory.directorymanagerws; 

coreui = nox.ext.apps.coreui.coreui; 

var _get_tooltip = function(o){
    if(o == null) 
      return; 

    var t = o.run, text = "";
    if(t && typeof t == "object" && t.tooltip){
        text = t.tooltip;
    }
    return text + (text ? "<br>" : "") + "Click for more info";
};


dojo.declare("_Link", dojox.charting.action2d.Base, {
     constructor: function(){
          this.connect();
     },
     process: function(o){
        if(o.type === "onclick" && o.run && o.run.url){
            document.location = o.run.url;
        }
    }
});


dojo.declare("nox.ext.apps.coreui.coreui._UpdatingBarGraph", [], {

  _chart : null, 
  _domNode : null, 
  _graph_size : 5, // default 
  _last_response : [],
  x_axis_label : "", 

  constructor: function (domNode, kwarg) {
        this._domNode = domNode;
        if (kwarg.url != null)
          this._url = kwarg.url; 

        coreui.getUpdateMgr().xhrGet({
            url: this._url,
            load: dojo.hitch(this,"_handle_new_response"), 
                 error: dojo.hitch(this, function (err, ioArgs) {
                    this._set_err_msg(
                      "Error Fetching Data"); 
                    console_log("Error fetching chart data from for " + 
                      this._url + " : ", err, ioArgs); 
                }),
            timeout: this.timeout,
            handleAs: "json",
            recur: true
        });

  }, 

  _get_graph_items: function(response) { 
    throw Error("Child class must implement _get_graph_items"); 
  }, 

  _set_err_msg: function(msg) { 
      coreui.base.remove_all_children(this._domNode); 
      var error_node = document.createElement("p");
      dojo.addClass(error_node, "chart-error-msg");  
      error_node.innerHTML = msg; 
      this._domNode.appendChild(error_node);

      //FIXME: this is ugly, as we are making assumptions
      //about the markup surrunding us, b/c dojox.charting
      //currently does not support labeling an axis
      var axis_label = dojo.byId("chart_x_axis_label"); 
      if(axis_label != null) 
          axis_label.innerHTML=""; 
 
  }, 

  _handle_new_response: function(response, ioArgs) { 
    this._last_response = response; 

    to_graph = this._get_graph_items(response); 

    // remove old graph node
    coreui.base.remove_all_children(this._domNode); 
    if(this._chart != null) {  
      this._chart.destroy(); 
      this._chart = null; 
    } 
    
    if(to_graph.length == 0) {
      this._set_err_msg("No Data Available"); 
      return; 
    } 


    var axis_label = dojo.byId("chart_x_axis_label"); 
    if(axis_label != null && axis_label.innerHTML == ""
            && this.x_axis_label != null) {  
          axis_label.innerHTML= "<center><b>" + this.x_axis_label 
                                + "</b></center>"; 
    } 
    
    var labels = []; 
    for(var i = 1; i <= this._graph_size; i++) {
        var old_index = this._graph_size - i; 
        if(old_index < to_graph.length) 
          txt = to_graph[old_index].label_text; 
        else 
          txt = ""; 
        labels.push({ value : i, text : txt}); 
    }

    this._chart = new dojox.charting.Chart2D(this._domNode);
    this._chart.setTheme(dojox.charting.themes.Grasshopper);
    
    this._chart.addAxis("x", {fixLower: "major", fixUpper: "major", 
              includeZero: true,  htmlLabels: false  });
    this._chart.addAxis("y", {vertical: true, fixLower: "minor", 
              fixUpper: "minor", natural: true, htmlLabels: false,
              labels: labels
    });
     
    this._chart.addPlot("default", {type: "Bars", gap: 4});

    var start_array = []; 
    for(var i = 0; i < this._graph_size; i++) {
      start_array.push(0); 
    }
  
    for(var i = this._graph_size; i >= 1; i--) {
      var old_index = this._graph_size - i;
      var modified_array = dojo.clone(start_array);
      if(old_index < to_graph.length) { 
        modified_array[i - 1] = to_graph[old_index].value;
        this._chart.addSeries("Series " + i, modified_array, 
          { 
            tooltip: to_graph[old_index].tooltip, 
            url: to_graph[old_index].link 
          });
        var tootltip = new dojox.charting.action2d.Tooltip(this._chart, 
                        "default", {text: _get_tooltip});
        var link = new _Link(this._chart);
      }  
    }
      
    this._chart.render();
  }, 

  setVisible: function(is_visible) { 
    var d = is_visible ? "block" : "none";
    dojo.style(this._domNode, {display: d});

    // FIXME: This is a nasty hack where when we change
    // the display type, we re-render each graph as if we
    // got new data from the server.  I'm not sure why 
    // just hiding or showing the div doesn't work.  Weird.
    if(this._last_response != null) 
      this._handle_new_response(this._last_response); 
  }
}); 
