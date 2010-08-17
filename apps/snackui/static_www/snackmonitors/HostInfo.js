/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.HostInfo");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.netapps.directory.directorymanagerws.HostStore");
dojo.require("nox.webapps.coreui.coreui.ItemList");
dojo.require("nox.webapps.coreui.coreui.ItemInspector");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.Dialog");
dojo.require("dijit.form.ComboBox");
dojo.require("dijit.form.ValidationTextBox");
dojo.require("nox.netapps.user_event_log.networkevents.NetEvents");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("nox.webapps.coreui.coreui.EditableGridUtil"); 
dojo.require("nox.netapps.directory.directorymanagerws.Directories"); 
dojo.require("nox.netapps.directory.directorymanagerws.PrincipalInfoEditUtils"); 
dojo.require("nox.netapps.directory.directorymanagerws.PrincipalModifyDialog"); 
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");

dojo.declare("nox.ext.apps.snackui.snackmonitors.ValidationCell", dojox.grid.cells._Widget, {
    widgetClass: "dijit.form.ValidationTextBox",
    getWidgetProps: function(inDatum){
        return dojo.mixin({}, this.widgetProps||{}, {
            constraints: dojo.mixin({}, this.constraint) || {}, //TODO: really just for ValidationTextBoxes
            regExp: this.regExp || dijit.form.ValidationTextBox.prototype.regExp,
            promptMessage: this.promptMessage || dijit.form.ValidationTextBox.prototype.promptMessage,
            invalidMessage: this.promptMessage || dijit.form.ValidationTextBox.prototype.invalidMessage,
            value: inDatum
        });
    }
});

var coreui = nox.webapps.coreui.coreui;
var snackmon = nox.ext.apps.snackui.snackmonitors;
var dmws = nox.netapps.directory.directorymanagerws;
var pinfo_util = nox.netapps.directory.directorymanagerws.PrincipalInfoEditUtils;

var is_editable = false; // default. this value is set below
hostInspector = null; 
bindingTable = null; 
var num_ifaces = 0; // global var counts number of active interfaces 
                  // this avoids having to have to HostInterfacesStores

//NOTE: we use a special edit formatter for 
//the 'static bindings' table, as a field's editability depends on 
//whether a MAC or IP is already set.  But this is better than nothing. 

var edit_fmt = function(value) {
          // if value is empty ... still show that it is editable
          // NOTE: it seems like there is a dojo bug that make this
          // markup not reappear if you cancel an edit on a cell. 
          if(value == null || value == undefined || value == "") 
            return ""; 
          return '<span class="editable-grid-entry">' + 
            '<span class="editable-grid-value-wrapper">' + value + "</span>" + 
            '<img class="grid-edit-icon" style="visibility: hidden"' + 
            ' src="/static/nox/webapps/coreui/coreui/images/editIndicator.png" />' + 
            '</span>'; 
        } 



var host = null;
var hostStore = null;
var netevent_log = null; 
var bindingStore = null;
var bindingTable = null;
var notFoundError = false;
var default_error_handlers =  {
                404: function (response, ioArgs) {
                    show_invalid_error(); 
                } 
            }; 

function show_invalid_error() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "block"});
    dojo.style(dojo.byId("monitor_content"), {display: "none"});
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display: "block"});
}

//function saveAlways(item) {
//    bindingStore.save();
//}

//function saveIfDirty(item) {
//    if (bindingStore.isDirty(item)) {
//        bindingStore.save();
//    }
//}

function insert_binding(type) { 
  
    var binding = { is_gateway: "False" };
    var query = {}; 
    if(type == "ip") {
      var ip = ip_binding.getValue(); 
      if(!ip_binding.isValid() || ip == "")
        return; 
      binding["is_router"] =  "False"; 
      binding["nwaddr"] = ip_binding.getValue(); 
      query["nwaddr"] = ip_binding.getValue(); 
      ip_add_binding_dialog.hide();
    }else if (type == "mac") {
      var mac = mac_binding.getValue();
      var type = mac_iface_type.getValue();  
      if(! (type == "End-Host" || type == "Router"))
        return; 
      if(!mac_binding.isValid() || mac == "")
        return; 
      binding["is_router"] = mac_iface_type.getValue() == "Router" ? 
                              "True" : "False"; 
      binding["dladdr"] = mac_binding.getValue(); 
      query["dladdr"] = mac_binding.getValue(); 
      mac_add_binding_dialog.hide();
    }  
    reset_binding_dialogs(); 
    var error_str = ""; 
    bindingStore.fetch({ 
        query: query, // search for duplicates
        onItem: function (i) {
          var ip = i.getValue("nwaddr"); 
          if(ip != null)  
              error_str = "IP Address " + ip; 
          var mac = i.getValue("dladdr"); 
          if(mac != null)  
              error_str = "MAC Address " + mac; 
        }, 
        onComplete: function() { 
          if(error_str != "") {   
                coreui.UpdateErrorHandler.showError(
                              "Binding already exists for " + error_str + ".",
                              { 
                                hide_retry : true,
                                validation_error : true, 
                                header_msg : "Cannot Add Static Binding:"
                              });
          }
          else {
              bindingStore.newItem(binding);
              bindingStore.save();
          }
        }
    }); 
} 

function reset_binding_dialogs() { 
    ip_binding.setValue(""); 
    mac_iface_type.setValue("End-Host"); 
    mac_binding.setValue(""); 
} 

function add_binding(e) {
    bindingStore.newItem({ is_gateway: "False", is_router: "False" });  
}

function delete_binding(e) {
    var selected = bindingTable.selection.getSelected();
    for (var i in selected) {
        var item = selected[i];
        bindingStore.deleteItem(item);
    }

    bindingStore.save();
    bindingTable.selection.deselectAll();
}

var grid_row_count_hack;


// this function is called first, kicks off an asynchronous 
// query, and then calls build_page() in the callback. 
function init_page() { 
    coreui.base.update_page_title("Host Information");
    host = new nox.netapps.directory.directorymanagerws.Host({
        initialData: { name: selected_host },
        updateList: [ "status", "info","lastSeen","osFingerprint" ]
    });
    if (host.isNull()) {
        show_invalid_error();
        return;
    }
    dmws.Directories.datastore.update({ 
      onComplete: function() {
        dmws.Directories.datastore.fetch({ 
            query : { name: host.directoryName() }, 
            onItem: function (directory) {
              if (notFoundError != true) {
                is_editable = 
                    directory.getValue('enabled_principals')['host'] == 'RW';
                add_binding_btn1.attr('disabled', !is_editable);
                add_binding_btn2.attr('disabled', !is_editable);
              }
              notFoundError = false;
              build_page(); 
            }
        })
      }
    }); 
} 

function build_page() {

    coreui.base.set_nav_title([
        {
            title_text: "Host:",
            nav_text: "Hosts",
            nav_url: "/Monitors/Hosts"
        },
        {
            title_text: host.directoryName() + " -",
            nav_text: host.directoryName(),
            nav_url: "/Monitors/Hosts?directory=" + host.directoryName()
        },
        {
            title_text: host.principalName(),
            nav_text: host.principalName(),
            nav_url: host.uiMonitorPath()
        }
    ]);

    var userStore = host.userStore({
        autoUpdate: {
            errorHandlers : default_error_handlers
        }
    });

    var userList = new coreui.ItemList({
        store: userStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "name"
        },
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });

    var groupStore = host.groupStore({
        autoUpdate: {
            errorHandlers : default_error_handlers
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
        //editable : true,
        ignoreNull: true
    });
    /*
      We don't let users delete from the Info pages, as the info pages show
      transitive group membership.  if we want to, this code shows how.
      additionally, make the groupList above editable 
    dojo.connect(groupList, "onDelete", function (item) {
        var group = new dmws.HostGroup({initialData : { name : item.displayName() },
                                    updateList : [] }); 
         group.delete_direct_member(host.fullName()); 
    });
    */ 

      hostInspector = new coreui.ItemInspector({
        item: host,
        changeAnimFn: coreui.base.changeHighlightFn,
        model: [
            pinfo_util.get_name_row("Host Name", is_editable), 
            pinfo_util.get_directory_row("host",host.directoryName(), is_editable), 
            {name: "status", header: "Status", attr: "statusNode"},
            {name: "osFingerprint", header: "Detected Operating System", 
              get: function(item) {
                var prints = item.getValue('fingerprints');
                if(prints == null) 
                  return null;
                var ret = "";  
                for (ip in prints) {
                  var str = prints[ip]; 
                  if (num_ifaces > 1) { 
                      str += " (" + ip + ")"; 
                  }
                  if(ret != "")
                    ret += " and "
                  ret += str; 
                }
                if(ret != "") 
                  return ret; 
                return null;  
              }
            }, 
            {name: "lastSeen", header: "Last Seen", attr: "lastSeen"},
            pinfo_util.get_attr_row("description", "Description",is_editable),
            {name: "groups", header: "Group Membership", 
             noupdate: true, editable: true, 
             dialogEditor: true, editor: dmws.PrincipalModifyDialog,
             editorProps: { principal: host, type: "add_to_group", title: "Add to Host Group",
                            group_ctor : dmws.HostGroup, principal_type: "host",
                            ctor : dmws.Host },
             get: function (item) {
                 return groupList.domNode;
             }},
            {name: "users", header: "Active Users", noupdate: true,
             get: function (item) {
                 return userList.domNode;
             }}
          ]
      });
      dojo.byId("host-info").appendChild(hostInspector.domNode);

    bindingStore = host.bindingStore({
        autoUpdate: { 
            errorHandlers: dojo.mixin(default_error_handlers,
                 { 500: function (response, ioArgs) { 
                        coreui.UpdateErrorHandler.showError(response.responseText, 
                        { header_msg: "Error Retreiving Host Interfaces:" }); 
                  }
                 })  
        } 
    });

    // FIXME: we should extract this into its own class
    // Also, the grid needs to be aware of whether this host is in
    // an editable directory or not.
      var smode = (is_editable) ? 'single' : 'none';  
      bindingTable = new dojox.grid.DataGrid({
        store: bindingStore,
        selectionMode: smode, 
        query: {}, 
        canEdit: function(inCell, inRowIndex){
            var item = this.getItem(inRowIndex);
            if(!item){ return false; }

            /*
            if(inCell.index == 0){
                 var v = this.store.getValue(item, "nwaddr", null);
                 if (v != null && v != ""){
                     return false;
                 }
                 v = this.store.getValue(item, "location", null);
                 if (v != null && v != ""){
                     return false;
                 }
                 return true;
            }else if(inCell.index == 1){
                 var v = this.store.getValue(item, "dladdr", null);
                 if (v != null && v != ""){
                     return false;
                 }
                 v = this.store.getValue(item, "location", null);
                 if (v != null && v != ""){
                     return false;
                 }
                 return true;
            }else */
            // only allow editing the Type
            if(inCell.index == 2){
                 var v = this.store.getValue(item, "dladdr", null);
                 if (v == null || v == ""){
                     return false;
                 }
                 return true;
                 
            }
            return false; 
          
        },
        doApplyCellEdit: function(inValue, inRowIndex, inAttrName) {
            var cell = null;
            for (var i = 0; i < this.layout.cells.length; i++) {
                if (this.layout.cells[i].field == inAttrName) {
                    cell = this.layout.cells[i];
                    break;
                }
            }
            
            if (!cell) { return; }
            
            var widget = this.layout.cells[i].widget;
            if (widget && widget.isValid && !widget.isValid(inValue)) {
                this.doCancelEdit(inRowIndex);
                return;
            }
            
            // Can't use inheritance here due to Dojo limitations.
            this.store.fetchItemByIdentity({
		identity: this._by_idx[inRowIndex].idty,
                onItem: dojo.hitch(this, function(item){
                    this.store.setValue(item, inAttrName, inValue);
                    this.onApplyCellEdit(inValue, inRowIndex, 
                                         inAttrName);
                })
            });
        }, 
        autoHeight: true,
        structure: {
            defaultCell: { editable: true, type: snackmon.ValidationCell },
            cells: [
                {
                    name: "MAC Address",
                    field: "dladdr",
                    width: "auto" /*, 
                    promptMessage: "Enter address as colon-separated hex digits",
                    invalidMessage: "Address does not contain colon separated hex digits",
                    regExp: "([0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}",
                    formatter: edit_fmt */ 
                },
                {
                    name: "IP Address",
                    field: "nwaddr",
                    width: "auto" /*,  
                    formatter: edit_fmt,
                    promptMessage: "Enter address in dotted decimal form.",
                     invalidMessage: "Address is not in dotted decimal form.",
                    regExp: "((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){3}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"*/
                },
//                {name: "dpid", header: "DPID", attr: "dpid"},
//                {name: "port", header: "Port Number", attr: "port"},
                {
                    name: "Type",
                    field: "intfType",
                    width: "auto" ,   
                    type: dojox.grid.cells.ComboBox,
                    options: [ "End-Host", "Router" ],
                    formatter: edit_fmt
                }
            ]
        }
      });
      dojo.byId("static-bindings-table").appendChild(bindingTable.domNode);
      bindingTable.startup();
      //dojo.connect(bindingStore, "onNew", saveAlways);
      //dojo.connect(bindingStore, "onSet", saveIfDirty);
      //dojo.connect(bindingStore, "onDelete", saveAlways);
      // when user clicks away from static bindings grid, cancel any changes
      dojo.connect(bindingTable, "onBlur", function() {
          // Canceling the edit actually makes mistakes less 
          // clear.  Need to talk to sitepen about this.   
          //bindingTable.edit.cancel(); 
      }); 
      dojo.connect(bindingTable, "onApplyCellEdit", function(e) {
              bindingStore.save();
      });

      dojo.connect(bindingTable.selection, "onChanged", function(){
          var selected = bindingTable.selection.getSelectedCount();
          delete_selected_binding.attr('disabled', !(selected > 0));
      });

      /* Note, since dojox.grid.DataGrid can't queue multiple updates
      * while editing a cell, we manage Grid's rowCount manually in our
      * application code to override the corrupted value in the Grid
      * once editing finishes.  The ultimate cause for multiple updates
      * due to a single cell edit is the underlying store: since the
      * identity of the item changes, it first deletes and then re-adds
      * the modified item.  This eventually corrupts its rowCount. 
      */
      dojo.connect(bindingTable, "onStartEdit", function() {
        grid_row_count_hack = bindingTable.rowCount;
      });
      dojo.connect(bindingTable, "onApplyCellEdit", function() {
        bindingTable.updateRowCount(grid_row_count_hack);
      });

    interfaceStore = host.interfaceStore({
        hostObj: host,
        itemParameters: {
            updateList: [ "info" ]
        },
        autoUpdate: {
            errorHandlers: default_error_handlers, 
            onComplete: function() {
                  interfaceStore.fetch({ 
                    query: {}, 
                    onBegin: function(size) { 
                        num_ifaces = size; // cache for OS fingerprints
                      }
                    });
            }
        }
    });
    interfaceTable = new dojox.grid.DataGrid({
        store: interfaceStore,
        query: {},
        selectionMode: 'none', 
        autoHeight: true,
        structure: [
            {name: "MAC Address", field: "dladdr", width: "20%"},
            {name: "IP Address", field: "nwaddr", width: "16%"},
            {name: "Location", field: "uiLocationMonitorLinkText", width: "16%"},
            {name: "Switch", width: "16%", get: function (index, item) {
				if(item != null && item.switchObj != null) 
                    return item.switchObj.uiMonitorLinkText();
                return null; 
            }},
            {name: "Switch Port", width: "16%", get: function (index, item) {
				if(item != null && item.switchPortObj != null)
                    return item["switchPortObj"].uiMonitorLinkText();
                return null; 
            }} /*,
            {name: "Status", field: "status", width: "16%"} */ 
        ]
    });
    dojo.byId("active-bindings-table").appendChild(interfaceTable.domNode);
    interfaceTable.startup();
    
    host_update = coreui.getUpdateMgr().userFnCall({
        purpose: "Updating host information",
        fn: function () {
            host.update({
                onComplete: function () {
                    if (notFoundError != true) {
                        show_monitor_content();
                        hostInspector.update();

                        // also update the iframe containing flow info.
                        // use hidden input field to avoid double loading
                        // the iframe on startup
                        var iframe = dojo.byId("listframe");
                        var first_load_node = dojo.byId("first_load");
                        if(iframe != null && first_load_node != null && 
                            first_load_node.value != "true"){ 
                          iframe.src =  iframe.src;
                        }else {
                          first_load_node.value = "false"  
                        }
                    }
                    notFoundError = false;
                },
                errorHandlers: { 
                  404: function (err, ioArgs, item, update_type) {
                          if(update_type != "info") { 
                              // this is an error on a subquery, so we should 
                              // still display the rest of the page
                              return; 
                          } 
                          notFoundError = true;
                          show_invalid_error();
                          var fn = dmws.getPrincipalUtil().get_principal_not_found_fn(
                            "host",host.getValue("name"));  
                          fn.call(err,ioArgs); 
                       }
                }
            });
        },
        recur: true
    });
    
    netevent_log = new nox.netapps.user_event_log.networkevents.NetEventsTable( 
                   dojo.byId("netevents-table"), 10, 
                   "host=" + encodeURIComponent(host.getValue("name")));
}

dojo.addOnLoad(init_page);
