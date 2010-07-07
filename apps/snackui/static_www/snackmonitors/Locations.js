dojo.provide("nox.ext.apps.snackui.snackmonitors.Locations");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws.LocationStore");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.apps.coreui.coreui;

var locationStore = null;
var locationTable = null;

dojo.addOnLoad(function () {
    locationStore = new nox.apps.directory.directorymanagerws.LocationStore({
        url: "/ws.v1/location",
        itemConstructor: nox.apps.directory.directorymanagerws.Location,
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
            { name: "Status", width: "14%", field: "statusMarkup"}
        ]
    });
    monitor_content.addChild(locationTable);
    locationTable.startup();
	  dojo.connect(locationTable, "onBlur", function(){
		  locationTable.selection.deselectAll();
	  });
});
