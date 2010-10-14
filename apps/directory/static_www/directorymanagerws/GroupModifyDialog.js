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

dojo.provide("nox.ext.apps.directory.directorymanagerws.GroupModifyDialog");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");

var coreui = nox.ext.apps.coreui.coreui; 
var dmws = nox.ext.apps.directory.directorymanagerws; 

dojo.declare("nox.ext.apps.directory.directorymanagerws.GroupModifyDialog", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.directory.directorymanagerws", "templates/GroupModifyDialog.html"),
    widgetsInTemplate: true,

    group : null,
    type : null,
    title : null,
    ctor : null, 
    principal_type : null,

    // called whenever this dialog is used to submit changes to
    // the server. 
    onChange: function() {}, 

    _set_widget_values: function () {
        if(!this.group) return; 

        var dir = this.group.directoryName(); 
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
                                                    validation_error : true
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
                                                    validation_error : true
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
        this.group_name = this.name.getValue();
        this.group_directory = this.directory.getValue(); 
        args = {  name : this.group_name, 
                  directory : this.group_directory, 
                  ctor : this.ctor,
                  principal_type : this.principal_type
        }; 

        if(this.type == "parent") { 
          this.group.modify_parent("PUT", args); 
        } else if(this.type == "subgroup") { 
          this.group.modify_subgroup("PUT", args); 
        } else if(this.type == "member") { 
          this.group.modify_direct_member("PUT", args); 
        } else if(this.type == "group") {
          var name = this.group_directory + ";" + this.group_name; 
          this.group = new this.ctor({ initialData : { name: name}});
          this.group.create(function(e) {
                  window.location.pathname = 
                      window.location.pathname.replace(/Groups$/, 
                                                       'GroupInfo?name=' +
                                                       encodeURIComponent(name));
          }); 
        } else {
          throw "unknown group modify type '" + type + "'"; 
        }
        this.onChange(this.group); 
    },

    show: function() { 

        this.main_dialog.show();  
        this.name.focus();
    }, 

    _name_keypress: function (event) {
        switch (event.keyCode) {
        case dojo.keys.ENTER:
            this._done();
            break;
        }
    },

    postCreate: function() {
        this.inherited(arguments);
        this.main_dialog.closeButtonNode.style.display='none';
        
        // The directories we want to show in the drop-down depend
        // on what type of dialog we have.  To add a group, or add
        // a parent, the specified group must be in a writable 
        // directory.  The name of a subgroup or memeber that we are
        // adding, however, can be in a read-only directory. 
        if(this.type == "parent" || this.type == "group")  
          var filter_key = "write_" + this.principal_type + "_enabled"; 
        else   // "member", "subgroup"
          var filter_key = "read_" + this.principal_type + "_enabled"; 

        var query = {}; 
        query[filter_key] = true;
        this.directory = new dijit.form.FilteringSelect({ 
                store : dmws.Directories.datastore, 
                searchAttr : "name", query : query});
        this.dir_div.domNode.appendChild(this.directory.domNode);  

        this._set_widget_values();

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
	dojo.connect(this.name.domNode, "onkeypress", this, "_name_keypress");
        dojo.connect(this.addBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
    }

});
