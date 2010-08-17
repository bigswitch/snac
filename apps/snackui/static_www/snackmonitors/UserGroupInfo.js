/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.UserGroupInfo");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.webapps.coreui.coreui.UpdateMgr");
dojo.require("nox.netapps.directory.directorymanagerws.UserGroupStore");
dojo.require("nox.netapps.directory.directorymanagerws.GroupModifyDialog"); 
dojo.require("nox.netapps.directory.directorymanagerws.Directories"); 
dojo.require("nox.webapps.coreui.coreui.ItemList");
dojo.require("nox.webapps.coreui.coreui.ItemListEditor");
dojo.require("nox.webapps.coreui.coreui.ItemInspector");
dojo.require("dijit.form.FilteringSelect");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.webapps.coreui.coreui;
var dmws = nox.netapps.directory.directorymanagerws; 

var notFoundError = false;
var default_error_handlers =  {
                404: function (response, ioArgs) {
                    show_invalid_name_error();
                }
            }; 
var principal_group_editable = false;

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
        itemParameters: { updateList: [ "status" ] },
        autoUpdate: {
            errorHandlers: {
                404: function (response, ioArgs, item, itemType) {}
            }
        }
    });

    var subgroupsList = new coreui.ItemList({
        store: subgroupsStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "displayName"
        },
        editable : principal_group_editable, 
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });
    dojo.connect(subgroupsList, "onDelete", function (item) {
        group.delete_subgroup(dmws.UserGroup, item.displayName());
    });
    
    var parentsList = new coreui.ItemList({
        store: parentsStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "displayName"
        },
        editable : true,
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });
    dojo.connect(parentsList, "onDelete", function (item) {
        group.delete_parent(dmws.UserGroup, item.displayName());
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
                    store: nox.netapps.directory.directorymanagerws.Directories.datastore,
                    query: { write_user_enabled: true }
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
                    store: nox.netapps.directory.directorymanagerws.Directories.datastore,
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
                                    ctor : dmws.UserGroup, principal_type: "user" },
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
            { name: "parents", header: "Parent Groups", noupdate: true, editable: true, 
              dialogEditor: true, editor: dmws.GroupModifyDialog,
              editorProps: { group: group, type: "parent", title: "Add Parent Group",
                             ctor : dmws.UserGroup, principal_type: "user" },
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
            { name: "User Name", field: "uiMonitorLinkText", width: "33%"},
            { name: "Directory", field: "directoryName", width: "33%"},
            { name: "Status", field: "statusMarkup", width: "33%"}
        ]
    });
    dojo.byId('member_content').appendChild(membersTable.domNode);
    membersTable.startup();

    var group_util = dmws.getPrincipalGroupUtil(); 
    group_util.setup_infopage_edit_hooks("user",group,dmws.UserGroup,
                                         membersTable, membersStore);
    
    var usergrp_update = coreui.getUpdateMgr().userFnCall({
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
                            //var fn = group_util.get_group_not_found_fn(
                            //            "user",group.getValue("name") ); 
                            //fn.call(error,ioArgs); 
                         }
                }
            });
        },
        recur: true
    });
}

var group = null;

function init_directory() {
    group = new nox.netapps.directory.directorymanagerws.UserGroup({
        initialData: { name: selected_group},
        updateList: [ "info" ]
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
            title_text: "User Group:",
            nav_text: "Users",
            nav_url: "/Monitors/Groups/UserGroups"
        },
        {
            title_text: group.directoryName() + " -",
            nav_text: group.directoryName(),
            // TBD: Replace with link to list of user groups filtered by directory
            nav_url: null
        },
        {
            title_text: group.displayName(),
            nav_text: group.groupName(),
            nav_url: group.uiMonitorPath()
        }
    ]);

    init_page();
}

function fetch_directory() {
    var g = new nox.netapps.directory.directorymanagerws.UserGroup({
        initialData: { name: selected_group },
        updateList: ["info" ]
    });

    var q = { name : g.directoryName() }; 
    q["write_user_enabled"] = true; 
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
