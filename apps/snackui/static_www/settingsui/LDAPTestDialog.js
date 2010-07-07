/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.LDAPTestDialog");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws.HostStore");

var coreui = nox.apps.coreui.coreui;
var dmws = nox.apps.directory.directorymanagerws;
var type = 'host';

dojo.declare("nox.ext.apps.snackui.settingsui.LDAPTestDialog", 
             [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.settingsui", "templates/LDAPTestDialog.html"),
    widgetsInTemplate: true,

    directory : null,
    title : 'Directory Connectivity Test',

    _done: function () {
        this.main_dialog.hide();
    },

    show: function() { 
        this.main_dialog.show();  
    },

    _get_error: function(error, ioArgs) { 
        dojo.style(dojo.byId("waiting"), {display: "none"});
        dojo.style(dojo.byId("found"), {display: "none"});
        dojo.style(dojo.byId("error"), {display: "block"});

        var e = dojo.byId("error");
        var t = document.createElement("code");
        t.innerHTML = error.responseText;

        while (e.firstChild) {
            e.removeChild(e.firstChild);
        }
        e.appendChild(document.createElement("br"));
        e.appendChild(t);
    }, 

    postCreate: function() {
        dojo.style(dojo.byId("waiting"), {display: "none"});
        dojo.style(dojo.byId("found"), {display: "none"});
        dojo.style(dojo.byId("error"), {display: "none"});

        dojo.connect(this.select, "onChange", this, "_typeSelected");
        dojo.connect(this.okBtn, "onClick", this, "_test");
        dojo.connect(this.cancelBtn, "onClick", this, "_done");
    },

    _typeSelected: function(value) {
        type = value.toLowerCase();
    },

    _test: function(value) {
        dojo.style(dojo.byId("waiting"), {display: "block"});
        dojo.style(dojo.byId("found"), {display: "none"});
        dojo.style(dojo.byId("error"), {display: "none"});

        coreui.getUpdateMgr().xhrGet({
            url : "/ws.v1/" + type + "/" + encodeURIComponent(this.name),
            load: dojo.hitch(this, function(response) {
                dojo.style(dojo.byId("waiting"), {display: "none"});
                dojo.style(dojo.byId("found"), {display: "block"});
                dojo.style(dojo.byId("error"), {display: "none"});
          
                var e = dojo.byId("found");
                var t = document.createTextNode("Search found " + 
                                                response.length + " " +
                                                type + 
                                                " entries.");
                while (e.firstChild) {
                    e.removeChild(e.firstChild);
                }
                e.appendChild(document.createElement("br"));
                e.appendChild(t);
            }),
            timeout: 30000,
            handleAs: "json",
            recur: false,
            error: this._get_error
        });
    }
});
