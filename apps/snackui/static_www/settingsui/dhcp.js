/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.dhcp");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.ext.apps.coreui.coreui.simple_config");
dojo.require("nox.ext.apps.directory.directorymanagerws.HostStore");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPFixedAddressStore");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPSubnetStore");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPAddFixed");
dojo.require("nox.ext.apps.snackui.settingsui.DHCPError");
dojo.require("nox.ext.apps.coreui.coreui.EditableGridUtil"); 

dojo.require("dijit.form.Button");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");

var coreui = nox.ext.apps.coreui.coreui;
var sui = nox.ext.apps.snackui.settingsui;

var edit_fmt = coreui.getEditableGridUtil().editable_item_formatter; 

var settingsInspector = null;
var generalSettings = new Array();

var default_error_handlers =  {
                404: function (response, ioArgs) {
                    show_invalid_error();
                }
            };

var subnetsTable = null;
var subnetsStore = null;
var fixedAddressesTable = null;
var fixedAddressesStore = null;
var hostStore = null;

dojo.declare("nox.ext.apps.snackui.settingsui.ValidationCell",
             dojox.grid.cells._Widget, {
    widgetClass: "dijit.form.ValidationTextBox",
    getWidgetProps: function(inDatum) {
        return dojo.mixin({}, this.widgetProps||{}, {
            constraints: dojo.mixin({}, this.constraint) || {},
                                      //TODO: really just for ValidationTextBoxes
            regExp: this.regExp || dijit.form.ValidationTextBox.prototype.regExp,
            promptMessage: this.promptMessage ||
                    dijit.form.ValidationTextBox.prototype.promptMessage,
            invalidMessage: this.promptMessage ||
                    dijit.form.ValidationTextBox.prototype.invalidMessage,
            value: inDatum
        });
    }
});

dojo.declare("nox.ext.apps.snackui.settingsui.FilteringSelect",
             dojox.grid.cells._Widget, {
    widgetClass: "dijit.form.FilteringSelect",
    getWidgetProps: function(inDatum) {
        return dojo.mixin({}, this.widgetProps||{}, {
            constraints: dojo.mixin({}, this.constraint) || {},
            store: hostStore,
            value: inDatum
        });
    },
    getValue: function(inRowIndex) {
        var item = fixedAddressesTable.getItem(inRowIndex);
        var e = this.widget;

        // make sure to apply the displayed value
        e.attr('displayedValue', e.attr('displayedValue'));

        var host = hostStore.fetchItemByIdentity(e.attr('value'));
        var d = host.updateInfo();
        d.addCallback(function () {
                item.setValue('hostname', host.getValue('principalName'));
                item.setValue('directory', host.getValue('directoryName'));
                item.setValue('hwaddr', host.getValue('netinfos').dladdr);
        });

        return host.getValue('principalName');
    }
});

function validate() {
    subnetsStore.fetch({
        query: {},
        onComplete: function(items) {
            validate_subnets({ items: items, onComplete: function() { commit(); } });
        }
    });
}

function parse_ip(s) {
    // Note the string is already validated by a regular expression to be an IP.
    var octets = s.split(".");
    var ip = (parseInt(octets[0]) * 16777216) + (parseInt(octets[1]) << 16) + 
        (parseInt(octets[2]) << 8) + (parseInt(octets[3]) << 0);
    return ip;
}

function validate_subnets(args) {
    var items = args.items;
    var onComplete = args.onComplete;

    dojo.forEach(items, function(item) {
        // Subnet should not be 0.0.0.0/8 (default)
        var subnet = parse_ip(item.getValue('subnet'));
        var min_subnet = parse_ip('0.255.255.255');
        if (subnet <= min_subnet) {
            coreui.UpdateErrorHandler.showError(item.getValue('subnet') + 
                                                ' is an invalid subnet address.',
                                                { header_msg : "Commit Failed:",
                                                  hide_retry : true, 
                                                  validation_error: true });
            return;
        }
        
        // Netmask should be of structure 1*0*
        var netmask = parse_ip(item.getValue('netmask'));
        var in_mask = true;
        for (var i = 31; i >= 0; i--) {
            var bit = (netmask >> i) & 0x1;
            if (in_mask && bit == 1) { continue; }
            if (in_mask && bit == 0) { in_mask = false; continue; }
            if (!in_mask && bit == 1) {
                coreui.UpdateErrorHandler.showError(item.getValue('netmask') + 
                                                    ' is an invalid netmask.',
                                                    { header_msg : "Commit Failed:",
                                                      hide_retry : true, 
                                                      validation_error: true });
                return;
            }
        }

        // Subnet address should not have bits beyond netmask
        if ((subnet & (~netmask)) != 0) {
            coreui.UpdateErrorHandler.showError(item.getValue('subnet') + 
                                                ' subnet address does ' + 
                                                'not match its netmask.',
                                                { header_msg : "Commit Failed:",
                                                        hide_retry : true, 
                                                        validation_error: true });
            return;
        }
        
        // range-start and end should be within subnet 
        var range_start = parse_ip(item.getValue('range-start'));
        var range_end = parse_ip(item.getValue('range-end'));
        
        if ((range_start & netmask) != (subnet & netmask)) {
            coreui.UpdateErrorHandler.showError(item.getValue('range-start') + 
                                                ' is out of the subnet.',
                                                { header_msg : "Commit Failed:",
                                                  hide_retry : true, 
                                                  validation_error: true });
            return;
        }
        
        if ((range_end & netmask) != (subnet & netmask)) {
            coreui.UpdateErrorHandler.showError(item.getValue('range-end') + 
                                                ' is out of the subnet.',
                                                { header_msg : "Commit Failed:",
                                                  hide_retry : true, 
                                                  validation_error: true });
            return;
        }
        
        // Check range-start is < range-end
        if (range_start >= range_end) {
            coreui.UpdateErrorHandler.showError(item.getValue('range-start') + 
                                                ' and ' + 
                                                item.getValue('range-end') + 
                                                ' form an invalid range.',
                                                { header_msg : "Commit Failed:",
                                                  hide_retry : true, 
                                                  validation_error: true });
            return;
        }
    });

    // Check for overlapping address pools
    for (var j = 0; j < items.length; j++) {
        var item = items[j];
        var range_start = parse_ip(item.getValue('range-start'));
        var range_end = parse_ip(item.getValue('range-end'));

        for (var k = 0; k < items.length; k++) {
            if (k == j) { continue; }

            var i = items[k];
            var start = parse_ip(i.getValue('range-start'));
            var end = parse_ip(i.getValue('range-end'));

            if ((start >= range_start && start <= range_end) ||
                (end >= range_start && end <= range_end)) {
                coreui.UpdateErrorHandler.showError('Pools ' + 
                                                    item.getValue('range-start')
                                                    + ' - ' + 
                                                    item.getValue('range-end') + 
                                                    ' and ' +
                                                    i.getValue('range-start')
                                                    + ' - ' + 
                                                    i.getValue('range-end') + 
                                                    ' overlap.',
                                                { header_msg : "Commit Failed:",
                                                  hide_retry : true, 
                                                  validation_error: true });
                return;
            }
        }
    }

    onComplete();
}

function commit() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    /* Push the changes to the server */
    var config = {};
    //config["log-facility"] = generalSettings.log_facility;
    config["default-lease-time"] = generalSettings.default_lease_time;
    config["max-lease-time"] = generalSettings.max_lease_time;
    config["option_domain-name-servers"] =
        generalSettings.option_domain_name_servers;

    coreui.getSimpleConfig().submit_config("dhcp_config", config);

    subnetsStore.save();
    fixedAddressesStore.save();
}

function rollback() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    /* Reload the values form the server */
    coreui.getSimpleConfig().get_config_as_object("dhcp_config",
                                                  function (response) {
        //generalSettings.log_facility = response["log-facility"][0];
        generalSettings.default_lease_time = response["default-lease-time"][0];
        generalSettings.max_lease_time = response["max-lease-time"][0];
        generalSettings.option_domain_name_servers =
            response["option_domain-name-servers"][0];

        settingsInspector.update();
    });

    /* Stores support rollback internally */
    subnetsStore.revert();
    fixedAddressesStore.revert();
}

function add_subnet(e) {
    subnetsStore.newItem({
            'name' : Math.ceil(999999999999*Math.random()),
            'subnet' : '0.0.0.0',
            'netmask' : '255.255.255.255',
            'range-start' : '0.0.0.0',
            'range-end' : '0.0.0.0',
            'option_routers' : '0.0.0.1',
            'option_domain-name' : '',
            'option_domain-name-servers' : ''
                });

    enable_buttons();
}

function delete_subnet(e) {
    var selected = subnetsTable.selection.getSelected();
    for (var i in selected) {
        var item = selected[i];
        if (item != null) {
            subnetsStore.deleteItem(item);
        }
    }

    enable_buttons();
}

function add_fixed_address(e) {
    var appr = dijit.byId("add_fixed"); 
    if( appr ) {
        // must destroy to avoid duplicate id error 
        appr.destroy(); 
    }
    var props = { 
        id : "add_fixed",
        onAdd: function(name, hwaddr, nwaddr) {
            if (hwaddr == '' || hwaddr == undefined) { 
                hwaddr = '00:00:00:00:00:00';
            }
            if (nwaddr == '' || nwaddr == undefined) { 
                nwaddr = "0.0.0.0"; 
            }
            fixedAddressesStore.newItem({
                    'name' : Math.ceil(999999999999*Math.random()),
                    'hostname' : name.split(";", 2)[1],
                    'directory' : name.split(";", 2)[0],
                    'hwaddr' : hwaddr,
                    'ip4addr' : nwaddr
            });

            enable_buttons();
        }
    };

    appr = new sui.DHCPAddFixed(props);
    dojo.body().appendChild(appr.domNode);
    appr.startup();
    appr.show();
}

function delete_fixed_address(e) {
    var selected = fixedAddressesTable.selection.getSelected();
    for (var i in selected) {
        var item = selected[i];
        fixedAddressesStore.deleteItem(item);
    }

    enable_buttons();
}

function enable_buttons() {
    commit_button.attr('disabled', false);
    rollback_button.attr('disabled', false);
}

function init_page() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    settingsInspector = new coreui.ItemInspector({
        item: generalSettings,
            model: [
    {
        name: "status", header: "Status",
        get: function (item) {
            var s = document.createElement("span");
            var txt = "unknown";
            s.className = "errormsg"; 
            var stat = item != null && item.status != null ? item.status[0] : 'inactive';
            var success = false;
            if (stat) {
                txt = stat;
                if (txt == "active") {
                    success = true;
                    s.className = "successmsg";
                }
            }
            var t;
            if (success) {
                t = document.createTextNode(txt);
            } else {
                t = document.createElement("a");
                t.innerHTML = txt;
                t.onclick = function() {
                    var msg = item.status[1];
                    if (msg == '') {
                        msg = 'Nothing configured.';
                    }
                    var props = {
                        id : "error_msg",
                        error : msg
                    };

                    var appr = dijit.byId("error_msg"); 
                    if (appr) {
                        // must destroy to avoid duplicate id error 
                        appr.destroy(); 
                    }

                    appr = new sui.DHCPError(props);
                    dojo.body().appendChild(appr.domNode);
                    appr.startup();
                    appr.show();
                };
            }

            s.appendChild(t);
            return s;
        }
    },
    {
        name: "default-lease-time", header: "Default Lease Time (seconds)",
        get: function (item) {
            return item.default_lease_time;
        },
        getEdit : function (item) {
            return item.default_lease_time;
        },
        editAttr: "default_lease_time",
        editSet: function (item, value) {
            item.default_lease_time = parseInt(value);

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter lease time in seconds as a positive number.",
            invalidMessage: "Number is not a valid lease time.",
            regExp: "([1-9])([0-9]*)"
        }
    },
    {
        name: "max-lease-time", header: "Max Lease Time (seconds)",
        get: function (item) {
            return item.max_lease_time;
        },
        getEdit : function (item) {
            return item.max_lease_time;
        },
        editAttr: "max_lease_time",
        editSet: function (item, value) {
            item.max_lease_time = parseInt(value);

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter maximum lease time in seconds as a positive number.",
            invalidMessage: "Number is not a valid lease time.",
            regExp: "([1-9])([0-9]*)"
        }
    },
    {
        name: "option_domain-name-servers", header: "DNS Server Address(es)", attr: "option_domain-name-servers",
        get: function (item) {
            return item.option_domain_name_servers;
        },
        getEdit : function (item) {
            return item.option_domain_name_servers;
        },
        editAttr: "option_domain-name-servers",
        editSet: function (item, value) {
            item.option_domain_name_servers = value.replace(/\s*\,\s*/g, ", ");

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter DNS server addresses in dotted decimal form, separated by a comma.",
            invalidMessage: "Address is not in dotted decimal form.",
            regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))(( )*\,( )*((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5])))*"
        }
    }
    /*{
        name: "log-facility", header: "System Log Facility",
        get: function (item) {
            return item.log_facility;
        },
        getEdit : function (item) {
            return item.log_facility;
        },
        editAttr: "log_facility",
        editSet: function (item, value) {
            item.log_facility = value;

            enable_buttons();
        },
        editor: dijit.form.TextBox
    }*/
                    ],
        changeAnimFn: coreui.base.changeHighlightFn
        });

    dojo.byId("general_settings").appendChild(settingsInspector.domNode);

    updatemgr = nox.ext.apps.coreui.coreui.getUpdateMgr();
    //updatemgr.recurrence_period = 2;

    updatemgr.xhrGet({
        url: "/ws.v1/nox/dhcp",
        load: function (response, ioArgs) {
                generalSettings.status = response;
                settingsInspector.update();
        },
        error: nox.ext.apps.coreui.coreui.UpdateErrorHandler.create(),
        timeout: 30000,
        handleAs: "json",
        recur: true
    });

    coreui.getSimpleConfig().get_config_as_object("dhcp_config",
                                                  function (response) {
        //generalSettings.log_facility = response["log-facility"][0];
        generalSettings.default_lease_time = response["default-lease-time"][0];
        generalSettings.max_lease_time = response["max-lease-time"][0];
        generalSettings.option_domain_name_servers =
            response["option_domain-name-servers"][0];

        settingsInspector.update();
    });

    subnetsStore =
        new sui.DHCPSubnetStore({
                "url": "/ws.v1/config/dhcp_config",
                itemParameters: {
                    updateList: [ "info" ]
                }
                //autoUpdate: {
                //    errorHandlers: default_error_handlers
                //}
    });
    subnetsStore.update({
            onComplete: function() {
    subnetsTable = new dojox.grid.DataGrid({
            store: subnetsStore,
            query: {},
            selectionMode: 'single', 
            autoHeight: true,
            doApplyCellEdit: function(inValue, inRowIndex, inAttrName) {
                var cell = null;
                for (var i = 0; i < this.layout.cells.length; i++) {
                    if (this.layout.cells[i].field == inAttrName) {
                        cell = this.layout.cells[i];
                        break;
                    }
                }

                if (!cell) { return; }

                var widget = this.layout.cells[i].widget;
                if (widget && widget.isValid && !widget.isValid(inValue)) {
                    this.doCancelEdit(inRowIndex);
                    return;
                }

                // Can't use inheritance here due to Dojo limitations.
                this.store.fetchItemByIdentity({
		    identity: this._by_idx[inRowIndex].idty,
                    onItem: dojo.hitch(this, function(item){
                        // A trick to guarantee store detects a value
                        // change and grid subsequently redraws the
                        // cell.
                        this.store.setValue(item, inAttrName, '');
                        this.store.setValue(item, inAttrName, inValue);
                        this.onApplyCellEdit(inValue, inRowIndex, 
                                             inAttrName);
                    })
                });
            },
            structure: {
                defaultCell: {
                    editable: true,
                    type: sui.ValidationCell
                },
                cells: [
    {field: "subnet", name: "Subnet Address", width: "auto",
     promptMessage: "Enter subnet address in dotted decimal form.",
     invalidMessage: "Address is not in a dotted subnet address form.",
     formatter: edit_fmt,
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {field: "netmask", name: "Netmask", width: "auto",
     promptMessage: "Enter netmask in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt,
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {field: "range-start", name: "Address Range Start", width: "auto",
     promptMessage: "Enter range start address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {field: "range-end", name: "Address Range End", width: "auto",
     promptMessage: "Enter range end address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {field: "option_routers", name: "Router Address", width: "auto",
     promptMessage: "Enter router address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {field: "option_domain-name", name: "Domain Name", width: "auto",
     promptMessage: "Enter fully qualified domain name.",
     invalidMessage: "Domain name not in dotted form.",
     formatter: edit_fmt, 
     regExp: "" // XXX: FQDN validation
    }
    /*    {field: "option_domain-name-servers", name: "DNS Server Address(es)", width: "auto",
     promptMessage: "Enter DNS server addresses in dotted decimal form, separated by a comma.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "(^$)|(((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))(\,((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5])))*)"
     }*/
                        ]
            }
        });

    dojo.byId("subnets_table").appendChild(subnetsTable.domNode);
    subnetsTable.startup();

    dojo.connect(subnetsTable.selection, "onChanged", function(){
        var selected = subnetsTable.selection.getSelectedCount();
        delete_selected_subnet.attr('disabled', !(selected > 0));
    });
    // when user clicks away from grid, cancel changes
    dojo.connect(subnetsTable, "onBlur", function() { 
        subnetsTable.edit.cancel(); 
    } ); 
    dojo.connect(subnetsTable, "onApplyCellEdit", function() {
        enable_buttons();
    });
            }
        });

    fixedAddressesStore =
        new sui.DHCPFixedAddressStore({
                "url": "/ws.v1/config/dhcp_config",
                itemParameters: {
                    updateList: [ "info" ]
                }
                //autoUpdate: {
                //    errorHandlers: default_error_handlers
                // }
            });
    fixedAddressesStore.update({
            onComplete: function() {
    hostStore = new nox.ext.apps.directory.directorymanagerws.HostStore({
        url: "/ws.v1/host",
        itemParameters: {
            updateList: [ ]
        },
        autoUpdate: {
            errorHandlers: {}
        }
    });

    fixedAddressesTable = new dojox.grid.DataGrid({
            store: fixedAddressesStore,
            query: {},
            selectionMode: 'single', 
            autoHeight: true,
            canEdit: function(inCell, inRowIndex){
                var item = this.getItem(inRowIndex);
                if(!item) { return false; }

                if (inCell.index == 1) { return false; }

                return true;
            },
            doApplyCellEdit: function(inValue, inRowIndex, inAttrName) {
                var cell = null;
                for (var i = 0; i < this.layout.cells.length; i++) {
                    if (this.layout.cells[i].field == inAttrName) {
                        cell = this.layout.cells[i];
                        break;
                    }
                }

                if (!cell) { return; }

                var widget = this.layout.cells[i].widget;
                if (widget && widget.isValid && !widget.isValid(inValue)) {
                    this.doCancelEdit(inRowIndex);
                    return;
                }

                // Can't use inheritance here due to Dojo limitations.
                this.store.fetchItemByIdentity({
		    identity: this._by_idx[inRowIndex].idty,
                    onItem: dojo.hitch(this, function(item){
                        // A trick to guarantee store detects a value
                        // change and grid subsequently redraws the
                        // cell.
                        this.store.setValue(item, inAttrName, '');
                        this.store.setValue(item, inAttrName, inValue);
                        this.onApplyCellEdit(inValue, inRowIndex, 
                                             inAttrName);
                    })
                });
            },
            structure: {
                defaultCell: {
                    editable: true,
                    type: sui.ValidationCell
                },
                cells: [
    {field: "hostname", name: "Hostname", width: "auto", editable: false },
    {field: "directory", name: "Directory", width: "auto", editable: false },
    {field: "hwaddr", name: "Hardware Address", width: "auto",
     promptMessage: "Enter address as colon separated hex digits",
     invalidMessage: "Address does not contain colon separated hex digits",
     formatter: edit_fmt, 
     regExp: "([0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}"
    },
    {field: "ip4addr", name: "IP Address(es)", width: "auto",
     promptMessage: "Enter IP address in dotted decimal form, using comma to separate addresses.",
     invalidMessage: "Address is not in a dotted address form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))(\,((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5])))*",
     getEdit : function (item) { return item.ip4addr; },
     editAttr: "ip4addr",
     editSet: function (item, value) {
         item.ip4addr = value;
         enable_buttons();
     }
    }
                        ]
            }
    });

    dojo.byId("fixed_addresses_table").appendChild(fixedAddressesTable.domNode);
    fixedAddressesTable.startup();

    dojo.connect(fixedAddressesTable.selection, "onChanged", function(){
        var selected = fixedAddressesTable.selection.getSelectedCount();
        delete_selected_fixed_address.attr('disabled', !(selected > 0));
    });
    // when user clicks away from grid, cancel changes
    dojo.connect(fixedAddressesTable, "onBlur", function() { 
        fixedAddressesTable.edit.cancel(); 
    } ); 
    dojo.connect(fixedAddressesTable, "onApplyCellEdit", function() {
        enable_buttons();
    });
            }
        });
}

dojo.addOnLoad(init_page);
