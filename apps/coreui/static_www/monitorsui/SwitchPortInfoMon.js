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

dojo.provide("nox.ext.apps.coreui.monitorsui.SwitchPortInfoMon");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchPortStore");
dojo.require("nox.ext.apps.coreui.coreui.ItemList");
dojo.require("nox.ext.apps.coreui.coreui.ItemInspector");
dojo.require("nox.ext.apps.user_event_log.networkevents.NetEvents");
dojo.require("nox.ext.apps.directory.directorymanagerws.Location");
dojo.require("dijit.form.FilteringSelect");
dojo.require("nox.ext.apps.coreui.monitorsui.SwitchPortNatConfig"); 

var netevents = nox.ext.apps.user_event_log.networkevents;
var dmws = nox.ext.apps.directory.directorymanagerws;
var coreui = nox.ext.apps.coreui.coreui;
var monitorsui = nox.ext.apps.coreui.monitorsui;

var netevent_log = null;

var sw = null;
var port = null;
var userStore = null;
var hostStore = null;
var notFoundError = false;
var portInspector = null; 

var loc_gbl = null; 
var groupList = null; 

function show_invalid_switch_error() {
    dojo.style(dojo.byId("invalid-switch-error"), {display : "block"});
    dojo.style(dojo.byId("invalid-port-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display : "none"});
}

function show_invalid_port_error() {
    dojo.byId("error-switch-page-ref").href = sw.uiMonitorPath();
    dojo.style(dojo.byId("invalid-switch-error"), {display : "none"});
    dojo.style(dojo.byId("invalid-port-error"), {display: "block"});
    dojo.style(dojo.byId("monitor_content"), {display : "none"});
}

function show_error() {
    // Select between invalid switch and invalid switch port messages.
    var err = false;
    sw.update({
        onComplete: function () {
            if (err)
                show_invalid_switch_error();
            else
                show_invalid_port_error();
        },
        onError: function () {
            err = true;
        }
    });
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-switch-error"), {display : "none"});
    dojo.style(dojo.byId("invalid-port-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display : "block"});
}

function init_page() {
    coreui.base.update_page_title("Switch Port Details");
    sw = new dmws.Switch({
        initialData: { name: selected_switch }
    });
    if (sw.isNull()) {
        show_invalid_switch_error();
        return;
    }
    port = new dmws.SwitchPort({
        initialData: { name: selected_port },
        updateList: [ "config", "stat" ],
        switchObj: sw
    });
    if (port.isNull()) {
        show_error();
        return;
    }

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
            title_text: sw.principalName() + " -",
            nav_text: sw.principalName(),
            nav_url: sw.uiMonitorPath()
        },
        {
            title_text: port.getValue("name"),
            nav_text: port.getValue("name"),
            nav_url: port.uiMonitorPath()
        }
    ]);

    userStore = port.userStore({
          autoUpdate: {
              errorHandlers: {
                  404: function (err, req) {
                        show_error();
                  }
              }
          }
        });

    userList = new coreui.ItemList({
        store: userStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "displayName"
            },
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
        });

    hostStore = port.hostStore({
          autoUpdate: {
              errorHandlers: {
                  404: function (err, req) {
                        show_error();
                  }
              }
          }
        });

    hostList = new coreui.ItemList({
        store: hostStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "name"
            },
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
        });
    

  buildPortInspector = function() {
    // how to grab an unmangled location name from a switch port
    var get_loc_name = function (item) {
                 if(!item) return null; 
                 var loc = new dmws.Location({
                     initialData: { name: item.getValue("location") }
                 });
                 return loc.principalName();
              }; 

    portInspector = new coreui.ItemInspector({
        item: port,
        model: [
            {name: "location-name", header: "Location Name", 
             get: get_loc_name,
             editor: dijit.form.TextBox,
             editable: true, 
             getEdit: get_loc_name,
             editSet: function (item, value) {
                 var loc = new nox.ext.apps.directory.directorymanagerws.Location({
                     initialData: { name: item.getValue("location") }
                 });
                 if(!loc.isNull()){
                     loc.rename({
                         name: value,
                         onComplete: function (arg) {
                             document.location = item.uiMonitorPath();
                         },
                         onError: function (item) {
                              console_log("Error occurred during location rename.");
                         }
                     });
                 }
             }},
            {name: "switch-name", header: "Switch Name", get: function (i) {
                return i.switchObj.uiMonitorLink();
            }},
            {name: "directory", header: "Directory", get: function (i) {
                return i.switchObj.directoryName();
            }},
            {name: "groups", header: "Group Membership", noupdate: true, 
                    dialogEditor: true, editor: dmws.PrincipalModifyDialog,
                    editorProps: {  principal: loc_gbl, type: "add_to_group", 
                                    title: "Add to Location Group",
                                    group_ctor : dmws.LocationGroup, 
                                    principal_type: "location",
                                    ctor : dmws.Location },
                    get:        function (item) {
                                    return groupList.domNode; 
                                    //return groupListParent;
                                } 
            },  
            {name: "port-name", header: "Port Name", attr : "name" },
            {name: "port-no", header: "Port Number", attr: "port_no"},
            {name: "hwaddr-field", header: "HW Addr", attr: "hw_addr"},
            {name: "speed-field", header: "Speed", attr: "speed"},
            {name: "rxpkt-field", header: "Received Packets", attr: "rx_packets"},
            {name: "txpkt-field", header: "Transmitted Packets", attr: "tx_packets"},
            {name: "users", header: "Users", get: function (item) {
                return userList.domNode;
            }, noupdate: true},
            {name: "hosts", header: "Hosts", get: function (item) {
                return hostList.domNode;
            }, noupdate: true}
        ],
        changeAnimFn: coreui.base.changeHighlightFn
    });
    dojo.byId("switch-port-info").appendChild(portInspector.domNode);

  } 

    port_update = coreui.getUpdateMgr().userFnCall({
            purpose: "Updating port information",
            fn: function () {
                port.update({
                    onComplete: function () {
                        if (notFoundError != true) {
                            // create log if it does not exist
                            if(!netevent_log && port._data.location) { 
                                  nat_config = 
                                        new monitorsui.SwitchPortNatConfig(
                                        { name : port._data.location, 
                                          port_name : port._data.name}, 
                                                    "nat-port-config");  
                                  nat_config.startup(); 

                                // filter for network events table
                                var filter_str = "location=" + 
                                  encodeURIComponent(port._data.location + 
                                  "#" + selected_switch + "#" + port._data.name); 
                                netevent_log = new netevents.NetEventsTable( 
                                    dojo.byId("netevents-table"), 10, filter_str);
                            
                                // now that we know the location name, we can 
                                // find out what groups it is in  
                                // loc_gbl is global - needed by buildPortInspector
                                loc_gbl = new dmws.Location({
                                  initialData: { name: port.getValue("location") } });
                                var groupsStore = loc_gbl.groupStore({
                                                    locationObj: this,
                                                    autoUpdate: {
                                                      errorHandlers: function () { /*ignore*/ }
                                                    }
                                });
                                
                                
                                // groupList is global - needed by buildPortInspector
                                groupList = new coreui.ItemList({
                                    store: groupsStore,
                                    labelAttr: "uiMonitorLink",
                                    sort: {
                                        decreasing: false,
                                        attr: "name"
                                    },
                                    changeAnimFn: coreui.base.changeHighlightFn,
                                    ignoreNull: true
                                });
                               
                                // finally, we can build the inspector now that
                                // we know the location name and have the group 
                                // store setup 
                                buildPortInspector(); 
                                
                            }
                            portInspector.update();
                            show_monitor_content();
                        }
                        notFoundError = false;
                    },
                    errorHandlers: {
                        404: function (error, ioArgs) {
                            notFoundError = true;
                            show_error();

                            var fn = dmws.getPrincipalUtil().get_principal_not_found_fn(
                                  "port", port.getValue("name"));
                            fn.call(error,ioArgs);
                        }
                    }
                });
            },
            recur: true
        });
}

dojo.addOnLoad(init_page);
