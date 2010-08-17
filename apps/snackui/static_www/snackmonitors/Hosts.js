dojo.provide("nox.ext.apps.snackui.snackmonitors.Hosts");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.netapps.directory.directorymanagerws.HostStore");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.webapps.coreui.coreui;
var dmws = nox.netapps.directory.directorymanagerws;

var hostStore = null;
var hostTable = null;

// helper function used to extract an attribute
// from a host's active_interfaces store.
// This is used for ip addresses, mac addresses, and locations
// in the host list. 
function get_ifaces_attr(item, attr_name) {
  if(item == null) return null; 
  var ifaces = item.getValues('active_interfaces');
  if(ifaces.length == 0) return null; 
  
  var unique_attrs = [];  
  // find out how many unique values we have
  dojo.forEach(ifaces, function(iface) { 
    var a = iface.getValue(attr_name); 
    if(dojo.indexOf(unique_attrs,a) == -1)
      unique_attrs.push(a); 
  }); 
  var txt = ifaces[0].getValue(attr_name);
  if(unique_attrs.length > 1) 
    txt += " (+" + (ifaces.length - 1) + ")";  
  return txt; 
}


dojo.addOnLoad(function () {
    hostStore = new dmws.HostStore({
        url: "/ws.v1/host",
        itemParameters: {
            updateList: [ "status", "activeInterfaces" ]
        },
        autoUpdate: {
            onError : dmws.getPrincipalUtil().get_listpage_store_error_handler("Hosts")
        }
    });
    hostTable = new dojox.grid.DataGrid({
        store: hostStore,
        query: {},
        selectionMode: 'single', 
        region: "center",
        structure: [
            {name: "Name", field: "name", width: "20%", get: function(index, item){
                if(!item){ return null; }
                return item.uiMonitorLinkText();
            } },
            {name: "Directory", field: "directoryName", width: "10%"},
 /* 
  *  Temporarily removing table entries that will not be completed for 0.3.0
  *
            {
                name: "User", width: "10%",
                get: function (index, item) {
                    // TBD: - Return single user or quantity link if
                    // TBD:   more than one.
                    return null;
                }
            },
            {
                name: "Switch Port", width: "10%",
                get: function (index, item) {
                    // TBD: - Return single switch port or quantity link if
                    // TBD:   more than one.
                    return  null;
                }
            },
            { name: "Flows", field: "active_flows", width: "10%"}, */
            {
                name: "IP Address", width: "10%",
                get: function (index, item) {
                    var v = get_ifaces_attr(item,"nwaddr"); 
                    if (v == "0.0.0.0") return null; 
                    return v; 
                }
            },
            {
                name: "MAC Address", width: "10%",
                get: function (index, item) {
                    return get_ifaces_attr(item,"dladdr"); 
                }
            },
            {
                name: "Location", width: "20%",
                get: function (index, item) {
                    return get_ifaces_attr(item,"location_name"); 
                }
            },
            { name: "Status", field: "statusMarkup", width: "10%"}
        ]
    });
    monitor_content.addChild(hostTable);
    hostTable.startup();

    dmws.getPrincipalUtil().setup_listpage_edit_hooks("host", hostStore, 
                                                      dmws.Host, hostTable);
    // setup the deauth button
    dmws.getPrincipalUtil().setup_listpage_deauth_hooks("host", hostTable);
});
