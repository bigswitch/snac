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

dojo.provide("nox.ext.apps.directory.directorymanagerws._Principal");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui._NamedEntity");
dojo.require("nox.ext.apps.directory.directorymanagerws.PrincipalModifyDialog");

    
dojo.declare("nox.apps.directory.directorymanagerws._Principal",
             [ nox.ext.apps.coreui.coreui._NamedEntity ], {

    coreui: nox.ext.apps.coreui.coreui,
    dmws: nox.ext.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        dojo.mixin(this.derivedAttributes, {
            fullName: {
                get: dojo.hitch(this, "fullName"),
                set: dojo.hitch(this, "fullNameSet"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            directoryName: {
                get: dojo.hitch(this, "directoryName"),
                set: dojo.hitch(this, "directoryNameSet"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            principalName: {
                get: dojo.hitch(this, "principalName"),
                set: dojo.hitch(this, "principalNameSet"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            wsv1Path: {
                get: dojo.hitch(this, "wsv1Path"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorPath: {
                get: dojo.hitch(this, "uiMonitorPath"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorLink: {
                get: dojo.hitch(this, "uiMonitorLink"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorLinkText : {
                get: dojo.hitch(this, "uiMonitorLinkText"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            statusNode : {
                get: dojo.hitch(this, "statusNode"),
                hasChanged: dojo.hitch(this, "statusHasChanged")
            },
            statusMarkup : {
                get: dojo.hitch(this, "statusMarkup"),
                hasChanged: dojo.hitch(this, "statusHasChanged")
            }
        });

        dojo.mixin(this.updateTypes, {
            "status": {
                load: dojo.hitch(this, "updateStatus")
            }
        });
    },

    isNull: function () {
        return (this._data.name == null)
    },

    fullName: function () {
        return this._data.name;
    },

    fullNameSet: function (v) {
        this.setValue("name", v);
    },

    directoryName: function () {
        try {
            return this._data.name.split(";", 2)[0]
        } catch (e) {
            return null;
        }
    },

    directoryNameSet: function (v) {
        var pname = this.principalName();
        this.setValue("name", v + ";" + pname);
    },

    principalName: function () {
        try {
            return  this._data.name.split(";", 2)[1]
        } catch (e) {
            return null;
        }
    },

    principalNameSet: function (v) {
        var dname = this.directoryName();
        this.setValue("name", dname + ";" + v);
    },

    displayName: function () {
        return this.getValue("name");
    },

    statusHasChanged: function (l) {
        return dojo.some(l, "return item.attribute == 'status';");
    },

    statusNode: function() {
        var s = document.createElement("span");
        var txt = "unknown";
        s.className = "errormsg"; 
        var stat = this.getValue("status"); 
        if (stat) {
            txt = this.getValue("status");
            if (txt == "active")
                s.className = "successmsg";
        }
        s.appendChild(document.createTextNode(txt));
        return s;
    },

    statusMarkup: function() {
        var cl = "errormsg";
        var txt = "unknown";
        var stat = this.getValue("status"); 
        if(stat){
            txt = stat;
            if(stat == "active"){
                cl = "successmsg";
            }
        }
        return "<span class='" + cl + "'>" + txt + "</span>";
    },

    wsv1Path: function () {
        throw Error("Method must be overridden by subclass");
    },

    uiMonitorPath: function () {
        throw Error("Method must be overridden by subclass");
    },

    uiMonitorLink: function ( /*optional*/use_mangled) {
        var name = ((use_mangled == true)
                    ? this.getValue("name") : this.principalName());
        var p = this.uiMonitorPath();
        if (p == null)
            return document.createTextNode(name);
        else
            return nox.ext.apps.coreui.coreui.base.createLink(p, name);
    },

    uiMonitorLinkText: function(/*optional*/use_mangled) {
        var name = ((use_mangled == true)
                    ? this.getValue("name") : this.principalName());
        return "<a href='" + this.uiMonitorPath() + "'>" + name + "</a>";
    },

    updateStatus: function (kwarg) {
        return this._xhrGetMixin("status", this.wsv1Path() + "/active", function (r) {
            return { "status" : r ? "active" : "inactive" };
        });
    },

    deleteOnServer : function(kwarg) {
        this._do_modify_request(this.wsv1Path(), "DELETE", kwarg.onComplete);
    },

    create : function(onComplete) {
        onExisting = dojo.hitch(this, function () {
                                coreui.UpdateErrorHandler.showError(
                                "Principal '" + this.principalName() +"' already exists" +
                                " in directory " + this.directoryName(),
                                { header_msg : "Create Failed:",
                                  hide_retry : true,
                                  validation_error: true });
                                // onComplete only called on success
        }); 
        onNonexisting = dojo.hitch(this, function () {
                            this._do_modify_request(this.wsv1Path(), 
                                "PUT", onComplete);
                      });
        this.check_exist(onExisting, onNonexisting);
    },

    check_exist : function(onComplete, onNonexisting) {
        cb = function(exists) {
            if (exists)
                onComplete.call(dojo.global);
            else
                onNonexisting.call(dojo.global);
        };
        this.exists(dojo.hitch(this, cb));
    },

    exists : function(onComplete) {
        nox.ext.apps.coreui.coreui.getUpdateMgr().xhrGet({
            url: this.wsv1Path(),
            headers: { "content-type": "application/json"},
            load: function (response, ioArgs) {
                onComplete.call(dojo.global, true);
            },
            error : function(response, ioArgs) {
                onComplete.call(dojo.global, false);
            },
            timeout: 30000
        });
    },

    change_directory: function (arg) {
        // stupid name swapping so I don't need to change all of the
        // existing calls
        arg.directory = arg.name;
        arg.name = this.principalName();
        this.full_rename(arg);
    },

    rename: function (arg) {
      arg.directory = this.directoryName();
      this.full_rename(arg);
    },

    full_rename : function (arg) {
         if(this.check_name(arg.name) == false) {
          coreui.UpdateErrorHandler.showError(
                      "'" + arg.name +"' is an invalid name",
                      { header_msg : "Rename Failed:",
                        hide_retry : true, validation_error: true });
          return;
        }
        if(this.check_name(arg.directory) == false) {
          coreui.UpdateErrorHandler.showError(
                      "'" + arg.directory +"' is an invalid directory name",
                      { header_msg : "Rename Failed:",
                        hide_retry : true, validation_error: true });
          return;
        }
        var newName =  arg.directory + ";" + arg.name;
        if (newName == this._data.name) {
            if (arg.onComplete != null) {
                arg.onComplete.call(dojo.global, this);
            }
            return;
        }
        var newItem = new this.constructor();
        newItem.setValue("name", newName);
        onExisting = dojo.hitch(coreui.UpdateErrorHandler, "showError",
                                "Principal '" + arg.name +"' already exists.",
                                { header_msg : "Rename Failed:",
                                  hide_retry : true,
                                  validation_error: true });
        onNonexisting = function () {
            nox.ext.apps.coreui.coreui.getUpdateMgr().rawXhrPut({
                  url: this.wsv1Path(),
                  headers: { "content-type": "application/json" },
                  putData: dojo.toJson({ name: newName }),
                  load: dojo.hitch(newItem, function (response, ioArgs) {
                          if (arg.onComplete != null) {
                              arg.onComplete.call(dojo.global, newItem);
                          }
                  }),
                  timeout: 30000,
                  errorHandlers: {
                      400: function(response, ioArgs, item, itemType) {
                            coreui.UpdateErrorHandler.showError(response.responseText,
                            { auto_show : true ,
                              header_msg : "Rename Failed:"
                            });
                      }
                  }
                });
        };
        newItem.check_exist(onExisting, dojo.hitch(this, onNonexisting));
    },

    _do_modify_request : function(path, method, onComplete) {
        var coreui = nox.ext.apps.coreui.coreui;
        coreui.getUpdateMgr().xhr(method, {
            url: path,
            headers: { "content-type": "application/json" },
            putData: dojo.toJson({}),
            load: function (response, ioArgs) {
                if (onComplete != null) {
                    onComplete.call(dojo.global);
                }
            },
            error: function(response, ioArgs) { 
                coreui.UpdateErrorHandler.showError(
                      "Failed to modify/remove " + ptype + " " + 
                      this.principalName() + " from directory " + 
                      this.directoryName(), 
                      { header_msg : "Modify Failed:" }
                );

            }, 
            timeout: 30000
        });
    }, 

    delete_binding : function(onComplete) { 
          var p_name = this.getValue("principalName"); 
          var dir_name = this.getValue("directoryName"); 
          
          coreui.getUpdateMgr().xhr("DELETE", {
              url : this.wsv1Path() + "/binding",
              headers: { "content-type" : "application/json" },
              load: function(response) {
                if(onComplete != null)
                  onComplete(response); 
              },
              putData: dojo.toJson({}),
              timeout: 30000,
              handleAs: "json",
              recur: false,
              error: nox.ext.apps.coreui.coreui.UpdateErrorHandler.create()
          });
    }

});

dojo.declare("nox.ext.apps.directory.directorymanagerws.PrincipalUtil", [], {

    dmws: nox.ext.apps.directory.directorymanagerws,

    show_modify_dialog : function(ptype, principal, title, ctor) {
        var appr = dijit.byId("modify_principal_id");
        if( appr ) {
          // must destroy to avoid duplicate id error
          appr.destroy();
        }
        var props = { principal : principal,
                      title: title, ctor : ctor, principal_type : ptype, 
                      type: "add_principal" };
        appr = new dmws.PrincipalModifyDialog(props);
        dojo.body().appendChild(appr.domNode);
        appr.startup();
        appr.show(); 
        return appr;
    },

    // these edit hooks assume the list pages use grids and principal stores
    // setup_simple_listpage_edit_hooks in PrincipalListFilter.js 
    // handles the simple mako-based list pages.  
    setup_listpage_edit_hooks : function(ptype, principal_store, ctor, grid) {
        var add_btn = dijit.byId("add_principal_button"); 
        if(add_btn != null) { 
          dojo.connect(add_btn, "onClick", function() {
            var title = "Add " + ptype.substring(0,1).toUpperCase() + 
                                  ptype.substring(1) + " Principal"; 
            var dialog = dmws.getPrincipalUtil().show_modify_dialog(ptype, 
                                                        null,title, ctor);
            dojo.connect(dialog, "onChange", principal_store, "update");
          });
        } 
        var del_btn = dijit.byId("remove_principal_button"); 
        if(del_btn != null) { 
          dojo.connect(del_btn, "onClick", function() {
            var selected = grid.selection.getSelected();
            for (var i in selected) {
                var item = selected[i];

                var dir_name = item.getValue("directoryName"); 
                var q = { name : dir_name }; 
                q["write_" + ptype + "_enabled"] = true; 
                var match_found = false; 
                dmws.Directories.datastore.fetch({
                            query : q,  
                            onItem : function (ignore) { 
                              if(match_found) 
                                return; 
                              match_found = true; 
                              principal_store.deleteItem(item);
                              principal_store.save();
                          },  // end onItem
                          onComplete : function() { 
                              if(!match_found) { 
                                    coreui.UpdateErrorHandler.showError(
                                    "Cannot remove a " + ptype + 
                                    " from read-only directory '" + dir_name + "'",
                                    { header_msg : "Removal Failed:", 
                                      hide_retry : true,
                                      validation_error: true });
                              } 
                          } 
              }); // end fetch 


            }
          });
          del_btn.setAttribute('disabled', true);
          dojo.connect(grid.selection, "onChanged", function(){
              var selected = grid.selection.getSelectedCount();
              del_btn.setAttribute('disabled', !(selected > 0));
          });
        }
    },

    setup_listpage_deauth_hooks : function(ptype, grid) {
        var deauth_btn = dijit.byId("deauth_principal_button"); 
        if (deauth_btn != null) { 
            dojo.connect(deauth_btn, "onClick", function() {
                var selected = grid.selection.getSelected();
                for (var i in selected) {
                    var item = selected[i];
                    item.delete_binding(function () { 
                        coreui.getUpdateMgr().updateNow(); 
                    });                     
                }
            });
            deauth_btn.setAttribute('disabled', true);
            dojo.connect(grid.selection, "onChanged", function() {
                var selected = grid.selection.getSelectedCount();
                deauth_btn.setAttribute('disabled', !(selected > 0));
            });
        }
    },

    // this returns a function suitable for the onError 
    // parameter of the auto_update parameter of a 
    // principal store.  This essentially ignores errors for subqueries
    get_listpage_store_error_handler : function(type_plural) { 
      return  function(error, ioArgs, item, update_type) {
              var ueh = nox.ext.apps.coreui.coreui.UpdateErrorHandler; 
              if(item == undefined || item == null) {
                var error_type = ueh.get_error_type(error); 
                if(error_type == 404 && update_type != null) {
                  // update_type is null if an error occured on the main
                  // query to get the list of names.  Since it is not null, 
                  // this means we got a 404 for a per-principal query,
                  // which we can just ignore. 
                } else if(error_type != 500 
                    && error_type != 400 
                    && error_type != 404
                    && ueh.defaultHandlers[error_type] != null) {
                    // need this in case it is unauthorized or another
                    // corner case were we want the default behavior  
                    ueh.defaultHandlers[error_type].apply(dojo.global,[error,ioArgs]); 
                } else {
                    ueh.showError("Unable to retrieve list of " + type_plural, 
                        { header_msg : "Server Error:" }); 
                } 
                return true; 
              }
            }; 
    }, 

    get_principal_not_found_fn : function(type, principal_name) {
      var first = type.substring(0,1).toUpperCase();
      var cap_type = first + type.substring(1);
      return function(error, ioArgs) {
                          coreui.UpdateErrorHandler.showError(
                              "No " + type + " named " +
                              principal_name + " exists.",
                              { hide_dismiss : true,
                                header_msg : cap_type + " Not Found:"
                              });
                   };
    }
});

(function () {
    var dmws = nox.ext.apps.directory.directorymanagerws;
    var principal_util = null;
    dmws.getPrincipalUtil = function () {
        if (principal_util == null) {
            principal_util = new dmws.PrincipalUtil();
        }
        return principal_util;
    }
})();
