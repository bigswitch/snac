dojo.provide("nox.ext.apps.snackui.snackmonitors.Users");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.netapps.directory.directorymanagerws.Directories");
dojo.require("nox.netapps.directory.directorymanagerws.UserStore");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.webapps.coreui.coreui
var dmws = nox.netapps.directory.directorymanagerws;

var userStore = null;
var userTable = null;

dojo.addOnLoad(function () {
    userStore = new nox.netapps.directory.directorymanagerws.UserStore({
        url: "/ws.v1/user?active_ext=true",
        itemParameters: {
            updateList: [ "status" ]
        },
        autoUpdate: {
            onError : dmws.getPrincipalUtil().get_listpage_store_error_handler("Users")
        }
    });
    userTable = new dojox.grid.DataGrid({
        store: userStore,
        query: {},
        selectionMode: 'single', 
        structure: [
            { name: "Name", field: "name", width: "25%", get: function(index, item){
                if(!item){ return null; }
                return item.uiMonitorLinkText();
            } },
            { name: "Directory", width: "20%", get: function(index, item){
                if(!item){ return null; }
                return item.directoryName();
            } },
 /* 
  *  Temporarily removing table entries that are not completed yet
  *
            { name: "Host", width: "20%", get: function(index, item){
                return null;
            } },
            { name: "Location", width: "20%", get: function(index, item){
                return null;
            } },
  */
            { name: "Status", width: "20%", field: "statusMarkup" }
        ]
    });
    monitor_content.addChild(userTable);
    userTable.startup();
    dmws.getPrincipalUtil().setup_listpage_edit_hooks("user", userStore, 
                                                      dmws.User, userTable);
    // setup the deauth button
    dmws.getPrincipalUtil().setup_listpage_deauth_hooks("user", userTable);
});
