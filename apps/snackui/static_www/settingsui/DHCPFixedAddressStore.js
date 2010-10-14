/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DHCPFixedAddressStore");

dojo.require("nox.ext.apps.coreui.coreui._UpdatingStore");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPFixedAddress");

/* A special storage to access DHCP fixed address configuration
 * information stored into the Properties table. */
dojo.declare("nox.ext.apps.snackui.settingsui.DHCPFixedAddressStore", 
             [ nox.ext.apps.coreui.coreui._UpdatingStore ], {

    constructor: function (kwarg) {
        this.itemConstructor = 
            nox.ext.apps.snackui.settingsui.DHCPFixedAddress;
    },

    _packData: function() {
        // return a list of contents, with special fixed address encoding
        var itemData = {};
        dojo.forEach(this._items, function (i) {
                if (! i.hasFlag("deleted")) {
                    var attrs = i.getAttributes();
                    var name = i.getValue('name');
                    
                    for (var j in attrs) {
                        var attr = attrs[j];
                        if (attr == 'name') continue;
                        if (attr == 'displayName') continue;

                        itemData['fixed_address-' + name + '-' + attr] = 
                            i.getValue(attr);
                    }
                } else {
                    var attrs = i.getAttributes();
                    var name = i.getValue('name');
                    
                    for (var j in attrs) {
                        var attr = attrs[j];
                        if (attr == 'name') continue;                        
                        if (attr == 'displayName') continue;

                        itemData['fixed_address-' + name + '-' + attr] = [];
                    }
                }
                
            }, this);
        
        return itemData;
    },

    _unpackData: function(data_obj) {
        // Return a list of fixed addresses, decode the fixed address encoding
        var bindings = {};

        for (key in data_obj) {
            if (key.indexOf('fixed_address-') == 0) {
                var i = key.indexOf('-');
                var j = key.indexOf('-', i + 1);
                var name = key.slice(i + 1, j);
                var ckey = key.slice(j + 1);
                var value = data_obj[key][0];
                
                if (!bindings[name]) {
                    bindings[name] = new Array();
                    bindings[name]['name'] = name;
                }
                
                bindings[name][ckey] = value;
            }
        }

        var r = [];
        for (var name in bindings) {
            r.push(bindings[name]);
        }

        return r;
    }

});
// Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.ext.apps.snackui.settingsui.DHCPFixedAddressStore,
            dojo.data.util.simpleFetch);
