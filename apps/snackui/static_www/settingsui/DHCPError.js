/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DHCPError");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");

dojo.declare("nox.ext.apps.snackui.settingsui.DHCPError", 
             [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.settingsui", 
                                 "templates/DHCPError.html"),
    widgetsInTemplate: true,

    title : 'Status Details',
    error : '',

    _cancel: function () {
        this.main_dialog.hide();
    },

    show: function() { 
        this.main_dialog.show();  
    },

    postCreate: function() {
        this.inherited(arguments);

        var t = document.createElement("code");
        t.innerHTML = this.error;

        this.right.domNode.appendChild(t);

        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
    }
});
