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

dojo.provide("nox.ext.apps.coreui.monitorsui.SwitchInfoMon");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchGroup");
dojo.require("nox.ext.apps.coreui.coreui.ItemInspector");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.TextBox");
dojo.require("nox.netapps.user_event_log.networkevents.NetEvents");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");
dojo.require("nox.ext.apps.directory.directorymanagerws.PrincipalInfoEditUtils"); 

var coreui = nox.ext.apps.coreui.coreui;
var dmws = nox.ext.apps.directory.directorymanagerws;
var pinfo_util = nox.ext.apps.directory.directorymanagerws.PrincipalInfoEditUtils;

var sw = null;
var swStore = null;
var portStore = null;
var sw_update = null;
var swInspector = null;
var portTable = null;
var netevent_log = null;
var notFoundError = false;
var is_editable = false; 

function show_invalid_switch_error() {
    dojo.style(dojo.byId("invalid-switch-error"), {display: "block"});
    dojo.style(dojo.byId("monitor_content"), {display: "none"});
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-switch-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display: "block"});
    portTable.render();
}

function update_nav_title () {
    coreui.base.set_nav_title([
        {
            title_text: "Switch:",
            nav_text: "Switches",
            nav_url: "/Monitors/Switches"
        },
        {
            title_text: sw.directoryName() + " -",
            nav_text: sw.directoryName(),
            nav_url: "/Monitors/Switches?directory=" + sw.directoryName()
        },
        {
            title_text: sw.principalName(),
            nav_text: sw.principalName(),
            nav_url: sw.uiMonitorPath()
        }
    ]);
}

function reset() {
    dijit.byId("reset_confirmation_dialog").show();
}

function reset_ok() {
    dijit.byId("reset_confirmation_dialog").hide();
    coreui.getUpdateMgr().xhr("PUT", {
            url : "/ws.v1/switch/" + sw.directoryName() + "/" + 
                sw.principalName() + "/reset",
            load: dojo.hitch(this, function(response) {
                // Nothing to do here, since there's no completion
                // callback from switches anyway.
            }),
            putData: dojo.toJson({}),
            timeout: 30000,
            handleAs: "json",
            recur: false,
            error: nox.ext.apps.coreui.coreui.UpdateErrorHandler.create()
        });
}

function update() {
    dijit.byId("update_confirmation_dialog").show();
}

function update_ok() {
    dijit.byId("update_confirmation_dialog").hide();
    coreui.getUpdateMgr().xhr("PUT", {
            url : "/ws.v1/switch/" + sw.directoryName() + "/" + 
                sw.principalName() + "/update",
            load: dojo.hitch(this, function(response) {
                // Nothing to do here, since there's no completion
                // callback from switches anyway.
            }),
            putData: dojo.toJson({}),
            timeout: 30000,
            handleAs: "json",
            recur: false,
            error: nox.ext.apps.coreui.coreui.UpdateErrorHandler.create()
        });
}

function init_page() {
    coreui.base.update_page_title("Switch Information");
    dijit.byId("reset_confirmation_dialog").hide();
    dijit.byId("update_confirmation_dialog").hide();

    sw = new dmws.Switch({
        initialData: { name: selected_switch },
        updateList: [ "status", "config", "stat", "approval", "info", "desc" ]
    });
    if (sw.isNull()) {
        show_invalid_switch_error();
        return;
    }

    dmws.Directories.datastore.update({ 
      onComplete : function() { 
          dmws.Directories.datastore.fetch({ 
            query : { name: sw.directoryName() }, 
            onItem: function (directory) {
              if (notFoundError != true) {
                is_editable = 
                    directory.getValue('enabled_principals')['switch'] == 'RW';
              }
              notFoundError = false;
              build_page();
            }
        });
      }
    }); 
}

function build_page() { 
    update_nav_title();
    
    var groupStore = sw.groupStore({
        autoUpdate: {
            errorHandlers : function () { /* ignore */ } 
        }
    });

    var groupList = new coreui.ItemList({
        store: groupStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "name"
        },
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });

      swInspector = new coreui.ItemInspector({
        item: sw,
        model: [
            pinfo_util.get_name_row("Switch Name",is_editable),
            pinfo_util.get_directory_row("switch",sw.directoryName(),is_editable),
            nox.ext.apps.directory.directorymanagerws.getSwitchUtil().get_status_cell(false), 
            {name: "groups", header: "Group Membership", 
             noupdate: true, editable: true, 
             dialogEditor: true, editor: dmws.PrincipalModifyDialog,
             editorProps: { principal: sw, type: "add_to_group", title: "Add to Switch Group",
                            group_ctor : dmws.SwitchGroup, principal_type: "switch",
                            ctor : dmws.Switch },
             get: function (item) {
                 return groupList.domNode;
             }},
        /*  We're not using these fields for TMDU, and maybe never
         *
         * {name: "info-sep", separator: true},
            {name: "caps", header: "Capabilities", attr:"caps"},
            {name: "n-bufs", header: "Buffers Count", attr: "n_bufs"},
            {name: "n-tables", header: "Tables", attr: "n_tables"},
        */ 
            {name: "stats-sep", separator: true},
            {name: "flows", header: "Active Flows", attr: "active_flows"},
            {name: "lookup-pkt", header: "Looked-Up Packets", attr: "total_lookup_pkt"},
            {name: "matched-pkt", header: "Matched Packets", attr: "total_matched_pkt"},
            {name: "rx-pkt", header: "Total Rx Packets", attr: "total_rx_pkt"},
            {name: "tx-pkt", header: "Total Tx Packets", attr: "total_tx_pkt"},

            {name: "desc-sep", separator: true},
            {name: "dpid", header: "DPID", attr: "dpid"},
            {name: "sw_desc", header: "Software Version", attr: "sw_desc"}
        /*  For now, we don't want these fields either
         *
            {name: "mfr_desc", header: "Manufacturer", attr: "mfr_desc"},
            {name: "hw_desc", header: "Hardware Type", attr: "hw_desc"},
            {name: "serial_num", header: "Serial Number", attr: "serial_num"},
        */ 
        ],
        changeAnimFn: coreui.base.changeHighlightFn
      }, "switch-info");

    portStore = sw.portStore({
        itemParameters: {
            updateList: [ "config", "stat" ]
        }
    });

    portTable = new dojox.grid.DataGrid({
        store: portStore,
        query: { },
        autoHeight: true,
        selectionMode: 'none', 
		    sortInfo: 1,
        structure: [
            { name: "Interface", field: "uiMonitorLinkText", width: "20%" },
            { name: "Num", field: "port_no", width: "16%" },
	    { name: "Location", field: "locationPrincipalName", width: "16%", editable: false, type: dojox.grid.cells._Widget },
            { name: "Speed", get: function (index, item) {
                if (item == null) return;
                var sp = item.getValue("speed");
                if (sp == null) {
                    return null;
                }
                return sp + "Mbps";
            }, width: "16%" },
            { name: "Rx Packets", field: "rx_packets", width: "16%" },
            { name: "Tx Packets", field: "tx_packets", width: "16%" }
        ]
    }, "port-table");
    portTable.startup();
	dojo.connect(portTable, "onBlur", function(){
		portTable.selection.deselectAll();
	});

    sw_update = coreui.getUpdateMgr().userFnCall({
        purpose: "Updating switch information",
        fn: function () {
            sw.update({
                onComplete: function () {
                    if (notFoundError != true) {
                        show_monitor_content();
                        swInspector.update();
                        var active = "active" == sw.getValue("status");
                        reset_button.attr('disabled', !active); 
                        portStore.update({
                           errorHandlers: {
                               // TBD: want to just remove port item?
                               404: function (err, request, pt, utype) {
                                //FIXME: Show an error but allow the rest of
                                //the page to display. 
                               }
                           }
                        });
                    }
                    notFoundError = false;
                },
                errorHandlers: {
                    404: function (error, ioArgs) {
                        notFoundError = true;
                        reset_button.attr('disabled',true);
                        show_invalid_switch_error();
                        var fn = dmws.getPrincipalUtil().get_principal_not_found_fn(
                                  "switch", sw.getValue("name"));
                        fn.call(error,ioArgs);
                    }
                }
            });
        },
        recur: true
    });

    netevent_log = new nox.netapps.user_event_log.networkevents.NetEventsTable( 
                    dojo.byId("netevents-table"), 10, 
                   "switch=" + encodeURIComponent(sw.getValue("name")));
}

dojo.addOnLoad(init_page);
