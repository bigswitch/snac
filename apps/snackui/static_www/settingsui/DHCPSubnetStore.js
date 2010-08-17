/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DHCPSubnetStore");

dojo.require("nox.webapps.coreui.coreui._UpdatingStore");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPSubnet");

/* A special storage to access DHCP subnet configuration information
 * stored into the Properties table. */
dojo.declare("nox.ext.apps.snackui.settingsui.DHCPSubnetStore", 
             [ nox.webapps.coreui.coreui._UpdatingStore ], {

    constructor: function (kwarg) {
        this.itemConstructor = 
            nox.ext.apps.snackui.settingsui.DHCPSubnet;
    },

    _packData: function() {
        // return a list of contents, with special subnet encoding
        var itemData = {};
        dojo.forEach(this._items, function (i) {
                if (! i.hasFlag("deleted")) {
                    var attrs = i.getAttributes();
                    var name = i.getValue('name');
                    
                    for (var j in attrs) {
                        var attr = attrs[j];
                        if (attr == 'name') continue;
                        if (attr == 'displayName') continue;

                        itemData['subnet-' + name + '-' + attr] = 
                            i.getValue(attr);
                    }
                } else {
                    var attrs = i.getAttributes();
                    var name = i.getValue('name');
                    
                    for (var j in attrs) {
                        var attr = attrs[j];
                        if (attr == 'name') continue;
                        if (attr == 'displayName') continue;

                        itemData['subnet-' + name + '-' + attr] = [];
                    }
                }
                
            }, this);
        
        return itemData;
    },

    _unpackData: function(data_obj) {
        // Return a list of subnets, decode the subnet id encoding
        var subnets = {};

        for (key in data_obj) {
            if (key.indexOf('subnet-') == 0) {
                var i = key.indexOf('-');
                var j = key.indexOf('-', i + 1);
                var subnet_id = key.slice(i + 1, j);
                var ckey = key.slice(j + 1);
                var value = data_obj[key][0];
                
                if (!subnets[subnet_id]) {
                    subnets[subnet_id] = new Array();
                    subnets[subnet_id]['name'] = subnet_id;
                }
                
                subnets[subnet_id][ckey] = value;
            }
        }

        var r = [];
        for (var subnet_id in subnets) {
            r.push(subnets[subnet_id]);
        }

        return r;
    }

});
// Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.ext.apps.snackui.settingsui.DHCPSubnetStore,
            dojo.data.util.simpleFetch);
