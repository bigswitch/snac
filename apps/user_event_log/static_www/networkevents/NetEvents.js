/*
 Copyright 2008 (C) Nicira,

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

dojo.provide("nox.ext.apps.user_event_log.networkevents.NetEvents");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.user_event_log.networkevents.NetEventsFormatter");

dojo.declare("nox.ext.apps.user_event_log.networkevents.NetEventsTable", [], { 

  _new_item : function(item) {
    
    if(this.table_elem.rows.length >= this.max_size) { 
      this.table_elem.deleteRow(-1); 
    } 
    this.highest_logid = item.logid;  
    var row = this.table_elem.insertRow(0);
    var dt = new Date(item.timestamp * 1000);
    row.innerHTML = "<td class='priority msg-level-" + item.level + "'>" + 
    item.level + "</td><td class='timestamp msg-level-" + item.level + "'>" + 
    dt.toLocaleString() + "</td><td class='msg msg-level-" + item.level + 
    "'>" + nox.apps.user_event_log.networkevents.NetEventsFormatter.format_msg(item.msg) + "</td>";
  }, 

  _get_error: function(error, ioArgs) { 
    //FIXME: once this is a widget, add a visual notification
    // that events are failing to update. 
    console_log("Error retrieving netevents"); 
  }, 

  // note: filter_str must already be encoded with encodeURIComponent() 
  constructor: function(table_elem, max_size, filter_str) {
    this.table_elem = table_elem;
    this.max_size = max_size; 
    this.filter_str = filter_str;
    this.highest_logid = 0; 
    var coreui = nox.apps.coreui.coreui;
    coreui.getUpdateMgr().suspendDuringMousemoveOn(this.table_elem);
      //    coreui.getUpdateMgr().recurrence_period = 1;
  
    var create_url = function() {
        return "/ws.v1/networkevents?end=" + this.max_size + "&after=" + 
        this.highest_logid + "&" + this.filter_str;   
    };  
    coreui.getUpdateMgr().xhrGet({
        url_fn : dojo.hitch(this,create_url), 
        load: dojo.hitch(this, 
                function (response, ioArgs) {
                    for(var i = 0; i < response.items.length; i++) { 
                        this._new_item(response.items[i]);
                    } 
                }
            ),
        sort: [ { attribute: "logid", descending: false } ],
        timeout: 30000,
        handleAs: "json",
        recur: true, 
        error: this._get_error
    });
    
  }
});

// vim:et:ts=4:sw=4
