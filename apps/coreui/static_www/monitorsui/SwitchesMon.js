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

// TBD: when adding a switch, check name is not in current list of names

dojo.provide("nox.ext.apps.coreui.monitorsui.SwitchesMon");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.Switch");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");

dojo.require("dojox.grid.DataGrid");
dojo.require("nox.ext.apps.coreui.coreui.PrincipalGridFilter");

var coreui = nox.ext.apps.coreui.coreui;
var dmws = nox.ext.apps.directory.directorymanagerws;

var swStore = null;
var swTable = null;
var swFilter = null; 

/* 
  Adding switches manually is not current exposed to the UI. 

function onAddSwitchDialogOpen(p) {
    var w = dijit.byId("add-switch-directory");
    if (dmws.Directories.write_default["switch"] != null) {
        w.setValue(dmws.Directories.write_default["switch"], true, dmws.Directories.write_default["switch"]);
    }
    dojo.style("directory-field-input-row",
        { display: dmws.Directories.num_write["switch"] < 2 ? "none" : "" });
}
 
function add_switch(info) {
    var dir = dijit.byId("add-switch-directory").getValue();
    coreui.getUpdateMgr().rawXhrPut({
        url: "/ws.v1/switch/" + encodeURIComponent(dir) + "/" + encodeURIComponent(info.name),
        load: function (response, ioArgs) {
            return
        },
        error: coreui.UpdateErrorHandler.create(null, {
            409: function (response, ioArgs) {
                console_log("Tried to add a switch with the same name as an existing one...");
            }
        }),
        headers: { "content-type" : " application/json" },
        putData: dojo.toJson(info),
        timeout: 30000
    })
    coreui.getUpdateMgr().updateNow(); // Will be queued after the post by updatemgr
}
*/ 

function handle_updates(component) {
    if (component == "nox.ext.apps.directory.directorymanagerws.Directories") {
        if (dmws.Directories.num_write["switch"] == 0) {
            addSwitchButton.setAttribute("disabled", true);
        } else {
            addSwitchButton.setAttribute("disabled", false);
        }
    }
}


// manually 'hitch', beause this is called from
// the mako template
function clear_switch_filter() {
  clear_filter(swStore);
}

swTable_getName = function(index, item){
    if(item){
        return item.uiMonitorLinkText();
    }
    return null;
}
swTable_getFlowMisses = function(index, item){
    if(item){
        if(item.total_matched_pkt == null || item.total_lookup_pkt == null){
            return null;
        }
        // Prevent divide by zero errors when there's been
        // no traffic
        if(item.total_lookup_pkt == 0){
            return "0%";
        }
        return Math.floor(100*(item.total_lookup_pkt - item.total_matched_pkt)/item.total_lookup_pkt) + "%";
    }
    return '-';
}
swTable_getStatus = function(index, item){
    if(!item){ return null; }
    if(!item.is_registered()){
        return "unregistered";
    }
    return item.getValue("status");
}
swTable_formatStatus = function(value, index){
    var cl = "errormsg";
    if(value && value != "unregistered" && value != "inactive"){
        cl = "successmsg";
    }
    return "<span class='" + cl + "'>" + value + "</span>";
}
dojo.addOnLoad(function(){
    //dojo.subscribe("update_completions", handle_updates);
    //dojo.connect(addSwitchDialog, "onOpen", onAddSwitchDialogOpen);
    swStore = new dmws.SwitchStore({
        url: "/ws.v1/switch",
        itemParameters: {
            updateList: [ "status", "stat", "approval" ]
        },
        autoUpdate: {
            onError : dmws.getPrincipalUtil().get_listpage_store_error_handler("Switches")
        }
    });

    swTable = new dojox.grid.DataGrid({
        store: swStore,
        query: { name: '*' },
        rowsPerPage: 20,
        region: 'center',
        selectionMode: 'single', 
		    sortInfo: 1,
        structure: {
            defaultCell: { styles: "text-align: center;" },
            cells: [
                { name: "Name", get: swTable_getName, field: "name", width: "16%", styles: "text-align: left;" },
                {name: "Directory", width: "14%", field: "directoryName"},
                { name: "Active Flows", field: "active_flows", width: "14%" },
                { name: "Flow Misses", get: swTable_getFlowMisses, width: "14%" },
                { name: "Rx Packets", field: "total_rx_pkt", width: "14%" },
                { name: "Tx Packets", field: "total_tx_pkt", width: "14%" },
                { name: "Dropped Packets", field: "total_dropped_pkt", width: "14%" },
                { name: "Status", get: swTable_getStatus, formatter: swTable_formatStatus, width: "14%" }
            ]
        }
    });

  /*
   * This line was intended to let the user deselect rows by clicking 
   * elsewhere on the page.  Unfortunately, it doesn't let us click on 
   * buttons and read selected rows. lame. 
   *
	dojo.connect(swTable, "onBlur", function(){
		swTable.selection.deselectAll();
	});
  */ 

    // FIXME: re-enable this code once we can have filters on all
    // principal pages

    //swFilter = new dmws.PrincipalListFilter("switch",swStore);
    //	swFilter = new coreui.PrincipalGridFilter({
    //		region: 'top',
    //		grid: swTable,
    //		principalType: "switch"
    //	});
    //
    //monitor_grid_border_container.addChild(swFilter);
  monitor_grid_border_container.addChild(swTable);

  // wire-up buttons to register / deregister switch
  var regSwitchButton = dojo.byId("regSwitchButton"); 
  var deregSwitchButton = dojo.byId("deregSwitchButton"); 
  dojo.connect(regSwitchButton, "onClick", function() { 
                var selected_list = swTable.selection.getSelected();
                dmws.getSwitchUtil().register_switch(selected_list); 
              }); 

  dojo.connect(deregSwitchButton, "onClick", function() {
            var selected = swTable.selection.getSelected();
            for (var i in selected) {
                var item = selected[i];
                item.set_approval(false, function() { 
                    swStore.update(); // show new status
                }); 
            }
          });
  regSwitchButton.setAttribute('disabled', true);
  deregSwitchButton.setAttribute('disabled', true);
  dojo.connect(swTable.selection, "onChanged", function(){
      var selected = swTable.selection.getSelectedCount();
      regSwitchButton.setAttribute('disabled', !(selected > 0));
      deregSwitchButton.setAttribute('disabled', !(selected > 0));
  });

  // for switches, this only sets up a 'delete' button
  dmws.getPrincipalUtil().setup_listpage_edit_hooks("switch",
                                swStore,dmws.Switch,swTable);

  swTable.startup();
});
