/*
 Copyright 2008 (C) Nicira, Inc.

 This file is part of NOX.

 NOX is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 NOX is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

dojo.provide("nox.apps.directory.directorymanagerws.PrincipalModifyDialog");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("nox.apps.directory.directorymanagerws.Directories");

var coreui = nox.apps.coreui.coreui; 

dojo.declare("nox.apps.directory.directorymanagerws.PrincipalModifyDialog", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.apps.directory.directorymanagerws", "templates/PrincipalModifyDialog.html"),
    widgetsInTemplate: true,

    principal : null,
    ctor : null,
    principal_type : null,
    title: null,
    type: null, 
    group_ctor : null, // only needed if type is 'add_to_group' 

    // called whenever this dialog is used to submit changes to
    // the server.
    onChange: function() {},

    _set_widget_values: function () {
        if(!this.principal) return;

        var dir = this.principal.directoryName();
        if(dir != "discovered")
          this.directory.setDisplayedValue(dir);
    },

    _cancel: function () {
          this.main_dialog.hide();
    },

    _done: function () {
        var g = new this.ctor({});
        if (!g.check_name(this.name.getValue())) {
            coreui.UpdateErrorHandler.showError("'" + this.name.getValue() +
                                                "' is an invalid name",
                                                { 
                                                    header_msg : "Operation Failed:",
                                                    hide_retry : true,
                                                    validation_error: true
                                                });
            return;
        }
        if (!g.check_name(this.directory.getValue())) {
            coreui.UpdateErrorHandler.showError("'" + this.directory.getValue()+
                                                "' is an invalid directory " + 
                                                "name",
                                                {
                                                    header_msg : "Operation Failed:",
                                                    hide_retry : true,
                                                    validation_error: true
                                                });
            return;
        }

        if(!this.directory.validate()) {
          // not the 'polite' way to do things, but i can't
          // get access to the form object, so i am replicating
          // the dijit.form.Form.validate() method manually.
          this.directory._hasBeenBlurred = true;
          this.directory.focus();
          return;
        }

        this.main_dialog.hide();
        this.principal_name = this.name.getValue();
        this.principal_directory = this.directory.getValue();

        if(this.type == "add_principal") { 
          var ptype = this.principal_type;
          var name = this.directory.getValue() + ";" + this.name.getValue();
          this.principal = new this.ctor({ initialData : { name: name}});
          this.principal.create(function(e) {
            var p = ptype.substring(0, 1).toUpperCase() + ptype.substring(1);
            // this may be called from within an iframe, so use 'top' to 
            // refer to the outermost window
            top.location.pathname =
              "/Monitors/" + p + 's/' + p + 'Info?name=' + 
                       encodeURIComponent(name);
            });
        }else if(this.type == "add_to_group") {
          var group_name = this.directory.getValue() +";"+ this.name.getValue();
          var p_name = this.principal.getValue("name");

          var group = new this.group_ctor({ 
            initialData: { name: group_name }, 
            updateList: []
          }); 

          var args = {  name : this.principal.principalName(), 
                  directory : this.principal.directoryName(), 
                  ctor : this.ctor,
                  principal_type : this.principal_type
          };
          group.modify_direct_member("PUT", args); 
        }else { 
          console_log("unknown principal modify type: " + this.type); 
        }
        this.onChange(this.principal);
    },

    _name_keypress: function (event) {
        switch (event.keyCode) {
        case dojo.keys.ENTER:
            this._done();
            break;
        }
    },

    show: function() {
        this.main_dialog.show();  
        this.name.focus();
    }, 

    postCreate: function() {
        this.main_dialog.closeButtonNode.style.display='none';
	      dojo.connect(this.name.domNode, "onkeypress", this, "_name_keypress");
        dojo.connect(this.addBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
        
        query = {};
        query["write_" + this.principal_type + "_enabled"] = true;
        this.directory = new dijit.form.FilteringSelect({ 
                store : dmws.Directories.datastore, 
                searchAttr : "name", query : query});
        
        this.dir_div.domNode.appendChild(this.directory.domNode);  

        var d = this.directory;
        dmws.Directories.datastore.fetch({
            onComplete: function(items) {
                if (items.length == 2) { 
                    dojo.forEach(items, function(item) {
                        if (item.displayName() != "discovered")  {
                            d.setDisplayedValue(item.displayName()); 
                        }
                    });
                }
            }
        });
        this._set_widget_values();
    }
});
