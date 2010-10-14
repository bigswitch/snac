dojo.provide("nox.ext.apps.default_switch_approval.switch_approval.SwitchApprover");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.Textarea");
dojo.require("dijit.form.SimpleTextarea");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");

dmws = nox.ext.apps.directory.directorymanagerws; 


dojo.declare("nox.ext.apps.default_switch_approval.switch_approval.SwitchApprover", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.default_switch_approval.switch_approval", "templates/SwitchApprover.html"),
    widgetsInTemplate: true,

    onComplete : null,  
    load_new_switch_page : false, 
    switch_obj : null,

    _set_widget_values: function () {
        var fp = this.switch_obj.get_fingerprint(); 
        if (fp == "")
          msg = "Warning: No SSL fingerprint known for this switch. Register insecure switch?"; 
        else 
          msg = "Register switch with SSL fingerprint '" + fp + "' ?";
        this.register_msg.innerHTML = msg;     
        this.name.setValue(this.switch_obj.principalName());
        var dir = this.switch_obj.directoryName(); 
        if(dir != "discovered")
          this.directory.setDisplayedValue(dir); 
    },

    _cancel: function () {
          this.main_dialog.hide();
    },

    _done: function () {
        if(!this.directory.validate()) {
          // not the 'polite' way to do things, but i can't
          // get access to the form object, so i am replicating
          // the dijit.form.Form.validate() method manually.  
          this.directory._hasBeenBlurred = true; 
          this.directory.focus(); 
          return; 
        }

        this.main_dialog.hide();
        this.switch_name = this.name.getValue();
        this.switch_directory = this.directory.getValue(); 

        var set_approval_cb = dojo.hitch(this, function() {
              var mangled = this.switch_directory + ";" + this.switch_name; 
              var new_sw = new dmws.Switch({ initialData: { name: mangled} });
              var cb = dojo.hitch(this, function(sw) { 
                            if(this.onComplete != null) { 
                                this.onComplete(); 
                            }
                            if(this.load_new_switch_page) { 
                                document.location = sw.uiMonitorPath(); 
                            }
                      }); 
              new_sw.set_approval(true,cb);
        });   

        this.switch_obj.full_rename(
            { directory : this.switch_directory, 
              name : this.switch_name,
              onComplete : set_approval_cb
            }); 
            
    },

    startup: function () {
        this.inherited("startup", arguments);

        this.directory = new dijit.form.FilteringSelect({ 
                store : dmws.Directories.datastore, 
                searchAttr : "name", 
                query : { write_switch_enabled : true }
        });
        this.dir_div.domNode.appendChild(this.directory.domNode);  
        this._set_widget_values();
        
        this.main_dialog.closeButtonNode.style.display='none';
        this.main_dialog.show();  
        this.directory.focus();
        dojo.connect(this.registerBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
    }

});
