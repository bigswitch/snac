/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DHCPAddFixed");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws.HostStore");

var dmws = nox.apps.directory.directorymanagerws;
var hostStore = null;
var bindingStore = null;

dojo.declare("nox.ext.apps.snackui.settingsui.DHCPAddFixed", 
             [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.settingsui", "templates/DHCPAddFixed.html"),
    widgetsInTemplate: true,

    title : 'Add New Fixed Address',

    // called whenever this dialog is used to submit changes to
    // the server. 
    onChange: function() {}, 

    _cancel: function () {
          if (hostStore) {
              hostStore.destroy();
          }
          if (bindingStore) {
              bindingStore.destroy();
          }
          this.main_dialog.hide();
    },

    _done: function () {
        this.main_dialog.hide();
        
        var name = this.name.getValue();
        var host = hostStore.fetchItemByIdentity(name);

        bindingStore = host.bindingStore({});

        if (hostStore) {
            hostStore.destroy();
        }

        var t = this.onAdd;
        var n = this.name.getValue();

        bindingStore.update({
            onComplete: function() {
                    var dladdr = null;
                    var nwaddr = null;
                    bindingStore.fetch({
                       onItem: function(item) {
                           if (dladdr == null || dladdr == undefined) {
                               dladdr = item.getValue('dladdr');
                           }
                           if (nwaddr == null || nwaddr == undefined) {
                               nwaddr = item.getValue('nwaddr');
                           }
                       },
                       onComplete: function() {
                           t(n, dladdr, nwaddr);                           
                       }         
                    });
            }
        });


    },

    show: function() { 
        this.main_dialog.show();  
    },

    postCreate: function() {
        this.inherited(arguments);
        this.main_dialog.closeButtonNode.style.display='none';

        this.directory = new dijit.form.FilteringSelect({ 
            store : dmws.Directories.datastore,
            searchAttr : "name", 
            query: { write_host_enabled: true }
        });
        dojo.connect(this.directory, "onChange", this, "_directorySelected");
        this.right.domNode.appendChild(this.directory.domNode);  
        
        hostStore = new dmws.HostStore({
            url: "/ws.v1/host",
            itemParameters: { },
            autoUpdate: {
                errorHandlers: {}
            }
        });

        this.name = new dijit.form.FilteringSelect({
            store : hostStore,
            searchAttr : "name",
            disabled : true,
            query : { } 
        });
        this.low.domNode.appendChild(this.name.domNode);  

	dojo.connect(this.low.domNode, "onkeypress", this, "_name_keypress");
        dojo.connect(this.addBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");

        this.addBtn.attr('disabled', true);
    },

    _name_keypress: function (event) {
        switch (event.keyCode) {
        case dojo.keys.ENTER:
            this._done();
            break;
        }
    },

    _directorySelected: function() {
        this.addBtn.attr('disabled', true);

        var directorySelected = this.directory.getValue();

        if (hostStore) {
            hostStore.destroy();
        }
        hostStore = new dmws.HostStore({
            url: "/ws.v1/host",
            itemParameters: { },
            autoUpdate: {
                errorHandlers: {}
            },
            preQuery: function (item) {
                return item.directoryName() == directorySelected;
            }
        });

        while (this.low.domNode.firstChild) {
            this.low.domNode.removeChild(this.low.domNode.firstChild);
        }
        this.name = new dijit.form.FilteringSelect({ 
            store : hostStore,
            searchAttr : "principalName",
            query : { }
        });

        this.low.domNode.appendChild(this.name.domNode);  

        dojo.connect(this.name, "onChange", this, "_hostSelected");

    },

    _hostSelected: function() {
        if (this.name.getValue() == undefined) {
            this.addBtn.attr('disabled', true);
        } else {
            this.addBtn.attr('disabled', false);
        }
    }
});
