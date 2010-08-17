dojo.provide("nox.ext.apps.snackui.snackmonitors.Locations");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.netapps.directory.directorymanagerws.Directories");
dojo.require("nox.netapps.directory.directorymanagerws.LocationStore");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.webapps.coreui.coreui;

var locationStore = null;
var locationTable = null;

dojo.addOnLoad(function () {
    locationStore = new nox.netapps.directory.directorymanagerws.LocationStore({
        url: "/ws.v1/location",
        itemConstructor: nox.netapps.directory.directorymanagerws.Location,
        itemParameters: {
            updateList: [ "status", "config" ]
        },
        autoUpdate: {
            onError : dmws.getPrincipalUtil().get_listpage_store_error_handler("Locations")
        }
    });
    locationTable = new dojox.grid.DataGrid({
        store: locationStore,
        query: {},
        selectionMode: 'single', 
        region: "center",
        structure: [
            {name: "Name", width: "14%", field: "name", get: function(index, item){
                if(!item){ return null; }
                return item.uiMonitorLinkText();
            } },
            {name: "Directory", width: "14%", field: "directoryName"},
            {name: "Switch", header: "Switch", field: "uiSwitchMonitorLinkText"},
            {name: "port", header: "Port", field: "uiSwitchPortMonitorLinkText"},
 /*
  *  Temporarily removing table entries that have not be completed
  *
            {
                name: "Port", width: "14%",
                get: function (index, item) {
					if(!item){ return null; }
                    return item.switchPortObj.uiMonitorLinkText();
                }
            },
            {
                name: "User", width: "14%",
                get: function (index, item) {
                    // TBD: - Return single user or quantity link if
                    // TBD:   more than one.
                    return  null;
                }
            },
            {
                name: "Host", width: "14%",
                get: function (index, item) {
                    // TBD: - Return single host or quantity link if
                    // TBD:   more than one.
                    return  null;
                }
            },
   */
            { name: "Status", width: "14%", field: "statusMarkup"}
        ]
    });
    monitor_content.addChild(locationTable);
    locationTable.startup();
	  dojo.connect(locationTable, "onBlur", function(){
		  locationTable.selection.deselectAll();
	  });
});
