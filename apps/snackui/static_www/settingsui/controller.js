/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.controller");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.apps.coreui.coreui.simple_config");
dojo.require("nox.ext.apps.snackui.settingsui.ControllerInterfaceStore");
dojo.require("nox.apps.coreui.coreui.EditableGridUtil"); 
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");

var coreui = nox.apps.coreui.coreui;

var default_error_handlers =  {
                404: function (response, ioArgs) {
                    show_invalid_error();
                }
            };

//var edit_fmt = coreui.getEditableGridUtil().editable_item_formatter; 
var edit_fmt = function(x) { return x; }

var interfaceStore = null;
var platformSettings = new Array();
var platformInspector = null;
var uiSettings = new Array();
var settingsInspector = null;

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

function shutdown_system() {
    dijit.byId("shutdown_system_confirmation_dialog").show();
}

function shutdown_process() {
    dijit.byId("shutdown_process_confirmation_dialog").show();
}

function shutdown(name) {
    dijit.byId("shutdown_process_confirmation_dialog").hide();
    dijit.byId("shutdown_system_confirmation_dialog").hide();

    coreui.getUpdateMgr().xhr("PUT", {
        url : "/ws.v1/nox/local_config/shutdown",
        headers: { "content-type" : "application/json" },
        load: dojo.hitch(this, function(response) {
            // Nothing to do here.
        }),
        putData: dojo.toJson(name),
        timeout: 30000,
        handleAs: "json",
        recur: false,
        error: nox.apps.coreui.coreui.UpdateErrorHandler.create()
    });
}

function validate() {
    /* Perform rudimentary validations for the SSL configuration and
     * confirm the user knows what she/he is about to do. */

    /* Check both of the forms have a valid file, if either one
     * has. */
    var cert = dojo.byId('ssl_certificate_form').ssl_certificate.value;
    var pkey = dojo.byId('ssl_privatekey_form').ssl_privatekey.value;

    if (!(cert == '' && pkey == '') && (cert == '' || pkey == '')) {
        dijit.byId("certificate_warning_dialog").show();
        return;
    } 

    dijit.byId("confirmation_dialog").show();
}

function commit() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    /* Push the changes to the server */
    var config = {};
    config["network_name"] = platformSettings.network_name;
    config["port"] = uiSettings.port;
    config["ssl_port"] = uiSettings.ssl_port;

    coreui.getSimpleConfig().submit_config("authenticator_config", 
                { "internal_subnets" : platformSettings.internal_subnets });

    coreui.getSimpleConfig().submit_config("notifier_config", {
        "destination.1.name" : platformSettings.destination_name,
        "destination.1.type" : platformSettings.destination_type,
        "destination.1.facility" : platformSettings.destination_facility,
        "destination.1.priority" : platformSettings.destination_priority,
        "destination.1.host" : platformSettings.destination_host,
        //"destination.1.port" : platformSettings.destination_port,
        "rule.1.destination" : platformSettings.rule_destination
        //"rule.1.condition" : platformSettings.rule_condition,
        //"rule.1.expr" : platformSettings.rule_expr
    });

    /* Upload the SSL/TLS certificate and private key files, if
     * necessary. */
    if (dojo.byId('ssl_certificate_form').ssl_certificate.value != '') {
        dojo.io.iframe.send({
            url: "/ws.v1/config_base64/nox_config",
            method : 'post',
            handleAs : "html",
            form : dojo.byId('ssl_certificate_form'),
            contentType : "multipart/form-data",

            // FIXME: unfortunately, load is called even when we fail.
            load : function(response, ioArgs) {
                dojo.byId('ssl_certificate_form').reset();
                return response;
            },
            errorHandlers: default_error_handlers
        }); 
        dojo.io.iframe.send({
            url: "/ws.v1/config_base64/nox_config",
            method : 'post',
            handleAs : "html",
            form : dojo.byId('ssl_privatekey_form'),
            contentType : "multipart/form-data",

            // FIXME: unfortunately, load is called even when we fail.
            load : function(response, ioArgs) {
                dojo.byId('ssl_privatekey_form').reset();
                return response;
            },
            errorHandlers: default_error_handlers
        });
    }

    dojo.forEach(interfaceStore._items, function (item) {
            if (item.isDirty()) {
                item.save();
            }
        }, this);

    coreui.getSimpleConfig().submit_config("nox_config", config, function() {
        var current_port = window.location.port;

        if (window.location.protocol == "https:") {
            if (current_port == '' || current_port == undefined) {
                current_port = 443;
            }
            if (config["ssl_port"] != current_port) {
                window.location.port = config["ssl_port"];
            }
        } else {
            if (current_port == '' || current_port == undefined) {
                current_port = 80;
            }
            if (config["port"] != current_port) {
                window.location.port = config["port"];
            }
        }
    });
}

function rollback() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    /* Reload the values form the server */
    coreui.getSimpleConfig().get_config_as_object("nox_config",
                                                  function (response) {
        platformSettings.network_name = response["network_name"][0];
        uiSettings.port = response["port"][0];
        uiSettings.ssl_port = response["ssl_port"][0];

        platformInspector.update();
        settingsInspector.update();
    });
    coreui.getSimpleConfig().get_config_as_object("authenticator_config",
                                                  function (response) {
        platformSettings.network_name = response["internal_subnets"][0];
        platformInspector.update();
    });
    coreui.getSimpleConfig().get_config_as_object("notifier_config",
                                                  function (response) {
        platformSettings.destination_name = response["destination.1.name"][0];
        platformSettings.destination_type = response["destination.1.type"][0];
        platformSettings.destination_facility =
            response["destination.1.facility"][0];
        platformSettings.destination_priority = 
            response["destination.1.priority"][0];
        platformSettings.destination_host = response["destination.1.host"][0];
        //platformSettings.destination_port = response["destination.1.port"][0];
        platformSettings.rule_destination = response["rule.1.destination"][0];
        //platformSettings.rule_condition = response["rule.1.condition"][0];
        //platformSettings.rule_expr = response["rule.1.expr"][0];

        platformInspector.update();
    });

    /* Reset the forms */
    dojo.byId('ssl_certificate_form').reset();    
    dojo.byId('ssl_privatekey_form').reset();

    /* Stores support rollback internally */
    interfaceStore.revert();
}

function enable_buttons() {
    commit_button.attr('disabled', false);
    rollback_button.attr('disabled', false);
}

function init_page() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    dijit.byId("confirmation_dialog").hide();
    dijit.byId("shutdown_process_confirmation_dialog").hide();
    dijit.byId("shutdown_system_confirmation_dialog").hide();

    platformInspector = new coreui.ItemInspector({
            item: platformSettings,
            model: [
    {
        name: "network_name", header: "Network Name",
        get: function (item) {
            return item.network_name;
        },
        getEdit : function (item) {
            return item.network_name;
        },
        editAttr: "network_name",
        editSet: function (item, value) {
            item.network_name = value;

            enable_buttons();
        },
        editor: dijit.form.TextBox
    },
    {
        name: "internal_subnets", header: "External Policy Subnets",
        get: function (item) {
            return item.internal_subnets;
        },
        getEdit : function (item) {
            return item.internal_subnets;
        },
        editAttr: "internal_subnets",
        editSet: function (item, value) {
            item.internal_subnets = value.replace(/\s*\,\s*/g, ", ");
            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter a comma separated list of network addresses.",
            invalidMessage: "Address list is not valid.",
            regExp: "(((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5])))\/(([0-9])|([1-2][0-9])|(3[0-2]))((( )*\,( )*)(((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5])))\/(([0-9])|([1-2][0-9])|(3[0-2])))*"
        }
    },
    {
        name: "destination_host", header: "Syslog Host",
        get: function (item) {
            return item.destination_host;
        },
        getEdit : function (item) {
            return item.destination_host;
        },
        editAttr: "destination_host",
        editSet: function (item, value) {
            item.destination_host = value;

            enable_buttons();
        },
        editor: dijit.form.TextBox
    }
    /*    {
        name: "destination_port", header: "Syslog Port",
        get: function (item) {
            return item.destination_port;
        },
        getEdit : function (item) {
            return item.destination_port;
        },
        editAttr: "destination_port",
        editSet: function (item, value) {
            item.destination_port = value;

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter a UDP port number (1 - 65535).",
            invalidMessage: "Port is not a valid UDP port (1 - 65535).",
            regExp: "(\s*)|([1-9])|([1-9][0-9])|([1-9][0-9]{2})|([1-9][0-9]{3})|(6[0-9]{4})"
        }
        }*/
                    ],
            changeAnimFn: coreui.base.changeHighlightFn
        });

    dojo.byId("platform_settings").appendChild(platformInspector.domNode);

    coreui.getSimpleConfig().get_config_as_object("nox_config",
                                                  function (response) {
        platformSettings.network_name = response["network_name"][0];
        platformInspector.update();
    });
    coreui.getSimpleConfig().get_config_as_object("authenticator_config",
                                                  function (response) {
        platformSettings.internal_subnets = response["internal_subnets"][0];
        platformInspector.update();
    });

    // Defaults for the notifier
    platformSettings.destination_name = "Syslog";
    platformSettings.destination_type = "Syslog";
    platformSettings.destination_facility = "LOCAL7";
    platformSettings.destination_priority = "INFO";
    platformSettings.destination_host = "";
    //platformSettings.destination_port = "";
    platformSettings.rule_destination = "Syslog";
    //platformSettings.rule_condition = "";
    //platformSettings.rule_expr = "";

    coreui.getSimpleConfig().get_config_as_object("notifier_config",
                                                  function (response) {
        if(response["destination.1.name"] == null) 
          return; // no config set
        platformSettings.destination_name = response["destination.1.name"][0];
        platformSettings.destination_type = response["destination.1.type"][0];
        platformSettings.destination_facility =
            response["destination.1.facility"][0];
        platformSettings.destination_priority = 
            response["destination.1.priority"][0];
        platformSettings.destination_host = response["destination.1.host"][0];
        //platformSettings.destination_port = response["destination.1.port"][0];
        platformSettings.rule_destination = response["rule.1.destination"][0];
        //platformSettings.rule_condition = response["rule.1.condition"][0];
        //platformSettings.rule_expr = response["rule.1.expr"][0];
        platformInspector.update();
    });

    settingsInspector = new coreui.ItemInspector({
            item: uiSettings,
            model: [
    {
        name: "port", header: "Web Port",
        get: function (item) {
            return item.port;
        },
        getEdit : function (item) {
            return item.port;
        },
        editAttr: "port",
        editSet: function (item, value) {
            item.port = parseInt(value);

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter a TCP port number (1 - 65535).",
            invalidMessage: "Port is not a valid TCP port (1 - 65535).",
            regExp: "([1-9])|([1-9][0-9])|([1-9][0-9]{2})|([1-9][0-9]{3})|(6[0-9]{4})"
        }
    },
    {
        name: "ssl_port", header: "Secure Web Port",
        get: function (item) {
            return item.ssl_port;
        },
        getEdit : function (item) {
            return item.ssl_port;
        },
        editAttr: "ssl_port",
        editSet: function (item, value) {
            item.ssl_port = parseInt(value);

            enable_buttons();
        },
        editor: dijit.form.ValidationTextBox,
        editorProps: {
            promptMessage: "Enter a TCP port number (1 - 65535) or 0 disable.",
            invalidMessage: "Port is not a valid TCP port (1 - 65535).",
            regExp: "([0-9])|([0-9]{2})|([0-9]{3})|([0-9]{4})|(6[0-9]{4})"
        }
    },
    {
        name: "ssl_certificate", header: "SSL/TLS Certificate File (X.509v3, PEM)",
        get: function (item) {
            var form = document.createElement("form");
            form.setAttribute('id', 'ssl_certificate_form');
            form.setAttribute('method', 'post');
            form.setAttribute('enctype', 'multipart/form-data');

            var input = document.createElement("input");
            input.setAttribute('type', 'file');
            input.setAttribute('name', 'ssl_certificate');

            form.appendChild(input);

            dojo.connect(form, "onchange", enable_buttons);

            return form;

        }
    },
    {
        name: "ssl_privatekey", header: "SSL/TLS Private Key File (PEM, no password)",
        get: function (item) {
            var form = document.createElement("form");
            form.setAttribute('id', 'ssl_privatekey_form');
            form.setAttribute('method', 'post');
            form.setAttribute('enctype', 'multipart/form-data');

            var input = document.createElement("input");
            input.setAttribute('type', 'file');
            input.setAttribute('name', 'ssl_privatekey');

            form.appendChild(input);

            dojo.connect(form, "onchange", enable_buttons);

            return form;
        }
    }
                    ],
            changeAnimFn: coreui.base.changeHighlightFn
        });

    dojo.byId("general_settings").appendChild(settingsInspector.domNode);

    coreui.getSimpleConfig().get_config_as_object("nox_config",
                                                  function (response) {
        uiSettings.port = response["port"][0];
        uiSettings.ssl_port = response["ssl_port"][0];

        settingsInspector.update();
    });

    interfaceStore =
        new nox.ext.apps.snackui.settingsui.ControllerInterfaceStore({
                "url": "/ws.v1/nox/local_config/active/interface",
                itemParameters: {
                    updateList: [ "info" ]
                },
                autoUpdate: {
                    errorHandlers: default_error_handlers
                }
            });

    var interfacesTable = new dojox.grid.DataGrid({
            store: interfaceStore,
            query: { },
            selectionMode: 'single', 
            canEdit: function(inCell, inRowIndex){
                /* Editing the controller's network interfaces is buggy.
                   Because this is not very important functionality, we're
                   making it read-only for now.
                   Note: when you re-enable this, also change 
                   'edit_fmt' above back to the real formatter.  
                */ 
                return false; 
                /* 
                var item = this.getItem(inRowIndex);
                if(!item) { return false; }

                if (inCell.index == 0 ||
                    inCell.index == 1) {
                    return false;
                }

                var v = this.store.getValue(item, "encap", null);
                return v != null && v == "Ethernet"; */ 
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
            autoHeight: true,
            structure: {
                defaultCell: { 
                    editable: true, 
                    type: nox.ext.apps.snackui.settingsui.ValidationCell 
                },
                cells: [
    {name: "Name", field: "name", width: "auto"},
    {name: "Type", field: "encap", width: "auto"},
    {name: "Hardware Address", field: "hwaddr", width: "auto",
     promptMessage: "Enter address as colon separated hex digits",
     invalidMessage: "Address does not contain colon separated hex digits",
     regExp: "([0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}",
     formatter: edit_fmt
    },
    {name: "IP Address", field: "ip4addr", width: "auto",
     promptMessage: "Enter address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {name: "Netmask", field: "ip4mask", width: "auto",
     promptMessage: "Enter netmask in dotted decimal form.",
     invalidMessage: "Netmask is not in dotted decimal form.",
     formatter: edit_fmt,
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {name: "Broadcast Address", field: "ip4bcast", width: "auto",
     promptMessage: "Enter address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt,
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {name: "Gateway Address", field: "ip4gw", width: "auto",
     promptMessage: "Enter address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt,
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    },
    {name: "DNS Server", field: "ip4dns", width: "auto",
     promptMessage: "Enter address in dotted decimal form.",
     invalidMessage: "Address is not in dotted decimal form.",
     formatter: edit_fmt, 
     regExp: "((([1-9])|([1-9][0-9])|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.)((([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))\\.){2}(([0-9])|([0-9]{2})|([01][0-9]{2})|(2[0-4][0-9])|(25[0-5]))"
    }
            ]
            }
        });

    dojo.byId("network_interfaces_table").appendChild(interfacesTable.domNode);
    interfacesTable.startup();

    dojo.connect(interfacesTable, "onBlur", function(){
        interfacesTable.edit.cancel(); 
    });
    dojo.connect(interfacesTable, "onApplyCellEdit", function() {
        enable_buttons();
    });
}

dojo.addOnLoad(init_page);
