/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.NWAddrGroupInfo");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.directory.directorymanagerws.NWAddrGroupStore");
dojo.require("nox.apps.directory.directorymanagerws.GroupModifyDialog"); 
dojo.require("nox.apps.directory.directorymanagerws.Directories"); 
dojo.require("nox.apps.coreui.coreui.ItemList");
dojo.require("nox.apps.coreui.coreui.ItemInspector");
dojo.require("dijit.form.FilteringSelect");

dojo.require("dojox.grid.DataGrid");

var dmws = nox.apps.directory.directorymanagerws; 
var coreui = nox.apps.coreui.coreui;
var notFoundError = false;
var default_error_handlers =  {
                404: function (response, ioArgs) {
                    show_invalid_name_error();
                }
            }; 
var principal_group_editable = false;
var group = null;

function show_invalid_name_error() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "block"});
    dojo.style(dojo.byId("monitor_content"), {display: "none"});
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display: "block"});
}

function get_editable_attr(att, hdr) {
    if (principal_group_editable) {
        return {name: att,
                header: hdr,
                attr: att,
                editor: dijit.form.TextBox,
                editAttr: att,
                editSet: function (item, value) {
                    item.setValue(att, value);
                    item.saveGroup();
                }
        }
    } else {
        return {name: att, header: hdr, attr: att };        
    }
}

//NOTE: the normal group info page edit hooks don't work here, b/c we
// special case the dialog that we want to show.  
function setup_edit_hooks(grid, membersStore) { 
      if (principal_group_editable) {
          var add_link = dojo.byId("add_direct_member_link"); 
          if(add_link != null) { 
              dojo.connect(add_link,"onclick", add_address_dialog, "show"); 
          } 
          var delete_link = dijit.byId("delete_direct_member_link"); 
          if (delete_link != null) { 
              dojo.connect(delete_link, "onClick", function() {
                      var selected = grid.selection.getSelected();
                      for (var i in selected) {
                          var item = selected[i];
                          group.modify_direct_member("DELETE", 
                            { addr_str : item.getValue("ip_str") } );  
                          membersStore.deleteItem(item);
                      }
                  });   
          }
      } else {
          dijit.byId("add_direct_member_link").attr('disabled', true);
          dijit.byId("delete_direct_member_link").attr('disabled', true);
      }
}

function try_to_add_address() { 
  var addr = address_to_add.getValue(); 
  if(!address_to_add.isValid() || addr == "") 
    return; 
  group.modify_direct_member("PUT", { addr_str : addr}); 
  address_to_add.setValue("");  
  add_address_dialog.hide();
} 

function init_page() {
    var parentsStore = group.parentGroupStore({
        autoUpdate: {
            errorHandlers: default_error_handlers
        },
        itemParameters: { force_use_mangled: true }
    });

    var subgroupsStore = group.subgroupMemberStore({
        autoUpdate: {
            errorHandlers: default_error_handlers
        },
        itemParameters: { force_use_mangled: true }
    });

    var membersStore = group.principalMemberStore({
        itemParameters: {
            updateList: [ ]
        },
        autoUpdate: {
            errorHandlers: {
                404: function (response, ioArgs, item, itemType) {}
            }
        }

    });

    var parentsList = new coreui.ItemList({
        store: parentsStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "groupName"
        },
        editable : true,
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });
    dojo.connect(parentsList, "onDelete", function (item) {
        group.delete_parent(dmws.NWAddrGroup, item.displayName());
    });

    var subgroupsList = new coreui.ItemList({
        store: subgroupsStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "groupName"
        },
        editable : principal_group_editable,
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });
    dojo.connect(subgroupsList, "onDelete", function (item) {
        group.delete_subgroup(dmws.NWAddrGroup, item.displayName());
    });

    var get_editable_group_name = function() {
        if (principal_group_editable) {
            return {name: "name", header: "Name", attr: "groupName", width: "20%",
                    editor: dijit.form.TextBox,
                    editAttr: "groupName",
                    editSet: function (item, value) {
                    item.rename({ 
                            name: value,
                            onComplete: function (item) {
                                document.location = item.uiMonitorPath();
                            }
                        });
                }
            };
        } else {
            return {name: "name", header: "Name", attr: "groupName",  width: "20%" };
        }
    }

    var get_editable_directory_name = function() {
        if (principal_group_editable) {
            return {name: "directory", header: "Directory Name", attr: "directoryName", width: "20%",
                    editor: dijit.form.FilteringSelect,
                    editorProps: {
                    store: nox.apps.directory.directorymanagerws.Directories.datastore,
                    query: { write_nwaddrgroup_enabled: true }
                },
                    editAttr: "directoryName",
                    editSet: function (item, value) {
                    item.change_directory({
                            name: value,
                            onComplete: function (item) {
                                document.location = item.uiMonitorPath();
                            }
                        });
                }
            };
        } else {
            return {name: "directory", header: "Directory Name", attr: "directoryName", width: "20%",
                    store: nox.apps.directory.directorymanagerws.Directories.datastore,
                    query: { write_user_enabled: true }
            };
        }
    }

    var get_editable_subgroups = function() {
        if (principal_group_editable) {
            return { name: "subgroups", header: "Subgroups", 
                     noupdate: true, editable: true, 
                     dialogEditor: true, editor: dmws.GroupModifyDialog,
                     editorProps: { group: group, type: "subgroup", title: "Add Subgroup",
                                    ctor : dmws.NWAddrGroup, principal_type: "nwaddrgroup" },
                     get: function (item) {return subgroupsList.domNode;}
            };
        } else {
            return { name: "subgroups", header: "Subgroups", noupdate: true, 
                     editable: false, 
                     get: function (item) {return subgroupsList.domNode;}
            };
        }
    };
  
    groupInspector = new coreui.ItemInspector({
        item: group,
        model: [
            get_editable_group_name(),
            get_editable_directory_name(),
            get_editable_attr("description", "Description", "description"),
            { name: "parents", header: "Parent Groups", noupdate: true, 
              editable: true, 
              dialogEditor: true, editor: dmws.GroupModifyDialog,
              editorProps: { group: group, type: "parent", title: "Add Parent Group",
                             ctor : dmws.NWAddrGroup, principal_type: "nwaddrgroup" },
              get: function (item) {return parentsList.domNode;}
            },
            get_editable_subgroups()
        ],
        changeAnimFn: coreui.base.changeHighlightFn
        });
    dojo.byId("group-inspector").appendChild(groupInspector.domNode);

    membersTable = new dojox.grid.DataGrid({
        store: membersStore,
        query: {},
        autoHeight: true,
        selectionMode: 'single', 
        region: "center",
        structure: [
            { name: "Address", field: "ip_str", width: "100%" }
        ]
    });
    dojo.byId('member_content').appendChild(membersTable.domNode);
    membersTable.startup();

    setup_edit_hooks(membersTable, membersStore);
    
    var grp_update = coreui.getUpdateMgr().userFnCall({
        purpose: "Updating group information",
        fn: function () {
            group.update({
                onComplete: function () {
                    if (notFoundError != true) {
                        show_monitor_content();
                        groupInspector.update();
                    }
                    notFoundError = false;
                },
                errorHandlers : { 
                    404: function (error, ioArgs) {
                            notFoundError = true;
                            show_invalid_name_error();
                         }
                }
            });
        },
        recur: true
    });
}


function init_directory() {
    coreui.base.update_page_title("Network Address Group Information");

    group = new nox.apps.directory.directorymanagerws.NWAddrGroup({
        initialData: { name: selected_group },
        updateList: ["info" ]
    });

    if (group.isNull()) {
        show_invalid_name_error();
        return;
    }

    coreui.base.set_nav_title([
        {
            title_text: "",
            nav_text: "Groups",
            nav_url: "/Monitors/Groups"
        },
        {
            title_text: "Network Address Group:",
            nav_text: "Network Addresses",
            nav_url: "/Monitors/Groups/NWAddrGroups"
        },
        {
            title_text: group.directoryName() + " -",
            nav_text: group.directoryName(),
            // TBD: Replace with link to list of host groups filtered by directory
            nav_url: null
        },
        {
            title_text: group.groupName(),
            nav_text: group.groupName(),
            nav_url: group.uiMonitorPath()
        }
    ]);

    init_page();
}

function fetch_directory() {
    var g = new nox.apps.directory.directorymanagerws.NWAddrGroup({
        initialData: { name: selected_group },
        updateList: ["info" ]
    });

    var q = { name : g.directoryName() }; 
    // FIXME: need to actually test if nwaddrs are supported
    //    q["write_host_enabled"] = true; 
    var match_found = false; 

    var store = new dmws.DirectoryStore({
        url : "/ws.v1/directory/instance"
    });

    store.update({
        onComplete: function () {
            store.fetch({
                    query : q,  
                    onItem : function (ignore) { 
                        principal_group_editable = true;
                    },
                    onComplete : function(items) {
                        init_directory(); 
                    }
                });
        }
        // TBD: - error handlers need to go here.
    });
}

dojo.addOnLoad(fetch_directory);
