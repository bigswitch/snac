dojo.provide("nox.ext.apps.snackui.snackmonitors.Groups");

dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchGroupStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.HostGroupStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.UserGroupStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.LocationGroupStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.NWAddrGroupStore");

(function () {

    var dmws = nox.ext.apps.directory.directorymanagerws;

    function update_cnt(group_type, count) {
        var n = dojo.byId(group_type + "-group-count");
        if(n == null) 
          return; 
        var t = document.createTextNode(count.toString());
        n.replaceChild(t, n.childNodes[0]);
    }

    // creates a store with the sole purpose of updating 
    // a field that counts the number of members in the group.
    // Overkill, but "oh well".  
    function _create_counter_store(ptype, ctor) { 
        var store = new ctor({
            url: "/ws.v1/group/" + ptype,
            autoUpdate: {
                onComplete: function () {
                    update_cnt(ptype, store.itemCount());
                },
                error: function () {
                    return false;  // Ignore all errors
                }
            }
        });
    }

    dojo.addOnLoad(function () {
        _create_counter_store("switch",dmws.SwitchGroupStore); 
        _create_counter_store("host",dmws.HostGroupStore); 
        _create_counter_store("user",dmws.UserGroupStore); 
        _create_counter_store("location",dmws.LocationGroupStore); 
        _create_counter_store("nwaddr",dmws.NWAddrGroupStore); 
    });

})();
