dojo.provide("nox.ext.apps.snackui.snackmonitors.LocationGroups");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");
dojo.require("nox.ext.apps.directory.directorymanagerws.LocationGroupStore");

dojo.require("dojox.grid.DataGrid");
dojo.require("dijit.form.Button");

var coreui = nox.ext.apps.coreui.coreui;
var dmws = nox.ext.apps.directory.directorymanagerws;

var groupsStore = null;
var groupsTable = null;

dojo.addOnLoad(function () {
    coreui.base.set_nav_title([
        {
            title_text: "",
            nav_text: "Groups",
            nav_url: "/Monitors/Groups"
        },
        {
            title_text: "Location Groups",
            nav_text: "Locations",
            nav_uri: "/Monitors/Groups/LocationGroups"
        }
    ]);
    groupsStore = new dmws.LocationGroupStore({
        url: "/ws.v1/group/location",
        autoUpdate: {
            errorHandlers: {}
        }
    });
    // tell group to keep track of how many members + subgroups it has.
    // b/c onNew is not called for items included in the first first response,
    // we need to do both a fetch and connect to onNew  
    groupsStore.fetch({onItem : function(item) {item.track_counts(); }});  
    dojo.connect(groupsStore, "onNew", 
                  function(newItem, parentInfo) { newItem.track_counts();}); 

    groupsTable = new dojox.grid.DataGrid({
        store: groupsStore,
        query: {},
        selectionMode: 'single', 
        region: "center",
        structure: [
            {name: "Name", field: "name", width: "25%", get: function(index, item){
                if(!item){ return null; }
                return item.uiMonitorLinkText();
            } },
            {name: "Directory", width: "25%", field: "directoryName"},
            {name: "Direct Members", width: "25%", field: "member_cnt"},
            {name: "Subgroups", width: "25%", field: "subgroup_cnt"}
        ]
    });
    monitor_content.addChild(groupsTable);
    groupsTable.startup();

    var group_util = dmws.getPrincipalGroupUtil(); 
    group_util.setup_listpage_edit_hooks("location", groupsStore,
                                         dmws.LocationGroup, groupsTable);
});
