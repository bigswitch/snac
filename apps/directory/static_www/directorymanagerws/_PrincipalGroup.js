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

dojo.provide("nox.apps.directory.directorymanagerws._PrincipalGroup");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.coreui.coreui._NamedEntity");
dojo.require("nox.apps.directory.directorymanagerws.GroupModifyDialog");

dojo.declare("nox.apps.directory.directorymanagerws._PrincipalGroup", [ nox.apps.coreui.coreui._NamedEntity ], {

    coreui: nox.apps.coreui.coreui,
    dmws: nox.apps.directory.directorymanagerws,
    
    count_subgroups: null, 
    count_members: null, 

    constructor: function (name, optArg) {
        dojo.mixin(this.derivedAttributes, {
            directoryName: {
                get: dojo.hitch(this, "directoryName"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            groupName: {
                get: dojo.hitch(this, "groupName"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorLink: {
                get: dojo.hitch(this, "uiMonitorLink")
            },
            uiMonitorPath: {
                get: dojo.hitch(this, "uiMonitorPath")
            }
        });
        dojo.mixin(this.updateTypes, {
            "info" : {
                load: this.updateInfo
            }
        });
    },

    isNull: function () {
        return this._data.name == null;
    },

    nameHasChanged: function (l) {
        return dojo.some(l, "return item.attribute == 'name';");
    },

    directoryName: function () {
        try {
            return this._data.name.split(";", 2)[0]
        } catch (e) {
            return null;
        }
    },

    groupName: function () {
        try {
            return  this._data.name.split(";", 2)[1]
        } catch (e) {
            return null;
        }
    },

    wsv1Path: function () {
        throw Error("Method must be overridden by subclass");
    },

    uiMonitorPath: function () {
        throw Error("Method must be overridden by subclass");
    },

    uiMonitorLink: function ( /*optional*/use_mangled) {
        var name = (use_mangled == true || this.force_use_mangled) ? this._data.name : this.groupName();
        return nox.apps.coreui.coreui.base.createLink(this.uiMonitorPath(),name);
    },

    uiMonitorLinkText: function(/*optional*/use_mangled) { 
        var name = (use_mangled == true || this.force_use_mangled) ? this._data.name : this.groupName();
        return "<a href='" + this.uiMonitorPath() + "'>" + name + "</a>"; 
    },

    change_directory: function (arg) {
        // stupid name swapping so I don't need to change all of the
        // existing calls
        arg.directory = arg.name;
        arg.name = this.groupName();
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
                        hide_retry : true,
                        validation_error: true 
                      });
          return;
        }
        if(this.check_name(arg.directory) == false) {
          coreui.UpdateErrorHandler.showError(
                      "'" + arg.directory +"' is an invalid directory name",
                      { header_msg : "Rename Failed:",
                        hide_retry : true,
                        validation_error: true 
                        });
          return;
        }
        var newName =  arg.directory + ";" + arg.name;
        if (newName == this._data.name) {
            return;
        }
        var newItem = new this.constructor();
        newItem.setValue("name", newName);
        onExisting = dojo.hitch(coreui.UpdateErrorHandler, "showError",
                                "Group '" + arg.name +"' already exists.",
                                { header_msg : "Rename Failed:",
                                  hide_retry : true,
                                  validation_error: true 
                                });
        onNonexisting = function () {
            nox.apps.coreui.coreui.getUpdateMgr().rawXhrPut({
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

    parentGroupStore: function () {
        throw Error("Method must be overridden by subclass");
    },

    principalMemberStore: function () {
        throw Error("Method must be overridden by subclass");
    },

    subgroupMemberStore: function () {
        throw Error("Method must be overridden by subclass");
    },
    
    updateInfo: function (kwarg) {
        return this._xhrGetMixin("info", this.wsv1Path());
    },

    direct_member_path : function (directory_name, principal_name) {
        return this.wsv1Path() + "/principal/"  
            + encodeURIComponent(directory_name) + "/"
            + encodeURIComponent(principal_name);
    },
    
    subgroup_path : function (directory_name, subgroup_name) {
        return this.wsv1Path() + "/subgroup/"  
            + encodeURIComponent(directory_name) + "/"
            + encodeURIComponent(subgroup_name);
    },


    exists : function(onComplete) { 
        nox.apps.coreui.coreui.getUpdateMgr().xhrGet( {
            url: this.wsv1Path(),
            headers: { "content-type": "application/json" },
            load: function (response, ioArgs) {
              onComplete.call(dojo.global,true);
            },
            error : function(response, ioArgs) { 
              //FIXME: should check for 404
              onComplete.call(dojo.global,false); 
            },
            timeout: 30000
        });
    },
   
    deleteOnServer : function(onComplete) { 
      this._do_modify_request(this.wsv1Path(),"DELETE",onComplete); 
    },

    create : function(onComplete) { 
      this._do_modify_request(this.wsv1Path(),"PUT",onComplete); 
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

    _patch_callback : function(args) { 
        return  function() { 
            nox.apps.coreui.coreui.getUpdateMgr().updateNow();
            if (args.onComplete != null)
              args.onComplete(arguments); 
        }; 
    }, 

    // wrap the simple delete so it can be directly called
    // from an onclick event
    delete_parent : function(ctor, mangled_name) {
        var a = mangled_name.split(";", 2);
        var args = { directory : a[0], name : a[1], ctor : ctor };
        this.modify_parent("DELETE", args); 
    },
                    
    modify_parent : function(method, args) { 
        
        var mangled_name = args.directory + ";" + args.name; 
        var parent_group = new args.ctor({ initialData: { name: mangled_name }}  ); 
        if (parent_group.isNull())
          throw "invalid parent group name";
        var path = parent_group.subgroup_path(this.directoryName(),
                                              this.groupName());
        var onComplete = this._patch_callback(args); 
        var cb = dojo.hitch(parent_group,"_do_modify_request",
                            path, method, onComplete);
        var ifNonexisting = dojo.hitch(coreui.UpdateErrorHandler, "showError",
                                       "Group '" + args.name + "' does not exist.",
                                       { header_msg: "Modify Failed:",
                                         hide_retry : true,
                                         validation_error: true
                                       });
        parent_group.check_exist(cb, ifNonexisting);
    },
    
    delete_subgroup : function(ctor,mangled_name) {
        var a = mangled_name.split(";", 2);
        var args = { directory : a[0], name : a[1], ctor : ctor};
        this.modify_subgroup("DELETE", args); 
    },
 
    modify_subgroup : function(method, args) {
        
        var mangled_name = args.directory + ";" + args.name; 
        var sub_group = new args.ctor({ initialData: { name: mangled_name }}); 
        if (sub_group.isNull())
          throw "invalid subgroup name";

        var path = this.subgroup_path(args.directory,args.name); 
        var onComplete = this._patch_callback(args); 
        var cb = dojo.hitch(this,"_do_modify_request", path,method, onComplete); 
        var ifNonexisting = dojo.hitch(coreui.UpdateErrorHandler, "showError",
                                       "Group '" + args.name + "' does not exist.",
                                       { header_msg: "Modify Failed:",
                                         hide_retry : true,
                                         validation_error: true
                                       });
        sub_group.check_exist(cb, ifNonexisting);
    },
    
    delete_direct_member : function(mangled_name) {
        var a = mangled_name.split(";", 2);
        var args = { directory : a[0], name : a[1]  };
        this.modify_direct_member("DELETE", args); 
    },

    modify_direct_member : function(method, args) {
        var path = this.direct_member_path(args.directory, args.name);
        var onComplete = this._patch_callback(args); 
        if (args.principal_type != null) {
            var ctor;
            if (args.principal_type == "switch") {
                ctor = this.dmws.Switch;
            } else if (args.principal_type == "location") {
                ctor = this.dmws.Location;            
            } else if (args.principal_type == "user") {
                ctor = this.dmws.User;                
            } else if (args.principal_type == "host") {
                ctor = this.dmws.Host;                
            } else {
                throw "unknown principal type";
            }
            
            var mangled_name = args.directory + ";" + args.name;
            var member = new ctor({ initialData: { name: mangled_name }}); 
            if (member.isNull())
                throw "invalid member name";

            var cb = dojo.hitch(this, "_do_modify_request", path, method, onComplete);
            var onNonexisting = function() {
                var ptype = args.principal_type.substring(0, 1).toUpperCase() + 
                                              args.principal_type.substring(1);
                coreui.UpdateErrorHandler.showError(ptype + " '" + args.name +
                                                    "' in directory '" + args.directory +
                                                    "' does not exist.", {
                                                      header_msg: "Modify Failed:",
                                                      hide_retry : true,
                                                      validation_error: true
                                                    });
            };
            member.check_exist(cb, onNonexisting);
        } else {
            this._do_modify_request(path, method, onComplete);
        }
    }, 

    _do_modify_request : function(path, method, onComplete) {
        nox.apps.coreui.coreui.getUpdateMgr().xhr(method, {
            url: path,
            headers: { "content-type": "application/json" },
            putData: dojo.toJson({}),
            load: function (response, ioArgs) {
                if (onComplete != null) {
                    onComplete.call(dojo.global);
                }
            },
            timeout: 30000
        });
    }, 

   track_counts : function() { 
      this.count_subgroups = this.subgroupMemberStore( { autoUpdate:  { 
                                onComplete: dojo.hitch(this, function() { 
                                      this.setValue("subgroup_cnt", 
                                      this.count_subgroups.itemCount());
                                }) }});
      this.count_members = this.principalMemberStore( { autoUpdate:  { 
                                onComplete: dojo.hitch(this, function() { 
                                      this.setValue("member_cnt", 
                                      this.count_members.itemCount());
                                      }) }});
   },

    saveGroup: function (kwarg) {
        var ginfo = { name: this._data.name };
        if (this._data.description != null) {
            ginfo["description"] = this._data.description;
        }

        var errHandlers;
        if (kwarg != null &&  kwarg["errorHandlers"] != null) {
            errHandlers = kwarg["errorHandlers"];
        } else {
            errHandlers = {
                400: function(response, ioArgs, item, itemType) {
                    nox.apps.coreui.coreui.UpdateErrorHandler.showError(
                                                response.responseText,
                     { auto_show : true, header_msg : "Save failed" });
                }
            };
        }
        
        nox.apps.coreui.coreui.getUpdateMgr().rawXhrPut({
            url: this.wsv1Path(),
            headers: { "content-type": "application/json" },
            putData: dojo.toJson(ginfo),
            timeout: 30000,
            errorHandlers: errHandlers
        });
    }
     
});

// the global PrincipalGroupUtil object provides access to code that
// is needed by all of the XXXGroupInfo XXXGroups pages, but does not
// operate on single XXXGroup objects

dojo.declare("nox.apps.directory.directorymanagerws.PrincipalGroupUtil", [], {

    dmws: nox.apps.directory.directorymanagerws,

    show_modify_dialog : function(ptype, group, type, title, ctor) {
        var appr = dijit.byId("modify_group_id"); 
        if( appr ) {
          // must destroy to avoid duplicate id error 
          appr.destroy(); 
        }
        var props = { id : "modify_group_id", group : group,
                      type: type, title: title, ctor : ctor, principal_type : ptype};
        appr = new nox.apps.directory.directorymanagerws.GroupModifyDialog(props);
        dojo.body().appendChild(appr.domNode);
        appr.startup();
        appr.show();
        return appr; 
  },


  setup_infopage_edit_hooks : function(ptype, group, ctor, grid, membersStore) { 
      if (principal_group_editable) {
          var add_link = dojo.byId("add_direct_member_link"); 
          if(add_link != null) { 
              dojo.connect(add_link,"onclick", 
                           dojo.hitch(this, "show_modify_dialog", ptype, group, "member",
                                      "Add "+ ptype.substring(0,1).toUpperCase() + ptype.substring(1) + " Member", ctor)); 
          } 
          var delete_link = dijit.byId("delete_direct_member_link"); 
          if (delete_link != null) { 
              dojo.connect(delete_link, "onClick", function() {
                      var selected = grid.selection.getSelected();
                      for (var i in selected) {
                          var item = selected[i];
                          group.delete_direct_member(item.fullName());
                          membersStore.deleteItem(item);
                      }
                  });   
          }
      } else {
          dijit.byId("add_direct_member_link").attr('disabled', true);
          dijit.byId("delete_direct_member_link").attr('disabled', true);
      }
  },
  setup_listpage_edit_hooks : function(ptype, group_store, ctor, grid, validator) { 
    dojo.connect(dijit.byId("add_group_button"), "onClick", function() { 
            var dialog = 
                dmws.getPrincipalGroupUtil().show_modify_dialog(ptype, null, "group", 
                                                  "Add "+ ptype.substring(0,1).toUpperCase() + 
                                                  ptype.substring(1) + " Group", ctor); 
            dojo.connect(dialog, "onChange", group_store, "update");
        }); 
    dojo.connect(dijit.byId("remove_group_button"), "onClick", function() {
            var selected = grid.selection.getSelected();
            for (var i in selected) {
                var item = selected[i];

                if (validator != undefined && !validator(item.groupName())) {
                    coreui.UpdateErrorHandler.showError(
                                                        "Removing '" + item.groupName() + "' not allowed",
                                                        { header_msg : "Remove Failed:",
                                                                      hide_retry : true,
                                                                      validation_error: true 
                                                              });
                    return;
                }



                // need to make sure that this group is
                // from a writeable directory 
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

                              // if this function is ever called
                              // then the directory is writable 
                              item.deleteOnServer(function() {
                                  
                                group_store.deleteItem(item);

                                if (item.count_subgroups) {
                                  item.count_subgroups.destroy();
                                }
                                if (item.count_members) {
                                  item.count_members.destroy();
                                }
                                //do update so any groups that contained
                                //this group as a subgroup have correct counts
                                coreui.getUpdateMgr().updateNow(); 
                              });
                          },  // end onItem
                          onComplete : function() { 
                              if(!match_found) { 
                                    coreui.UpdateErrorHandler.showError(
                                    "Cannot remove a group from read-only directory '" + 
                                      dir_name + "'",
                                    { header_msg : "Directory Removal Failed:", 
                                      hide_retry : true, 
                                      validation_error: true
                                    });
                              } 
                          } 
              }); // end fetch 

            } 
        });
  },

  get_group_not_found_fn : function(type, group_name) {
      return function(error, ioArgs) { 
                          coreui.UpdateErrorHandler.showError(
                              "No " + type + " group named " + 
                              group_name + " exists.", 
                              {  hide_dismiss : true, 
                                header_msg : "Group Not Found:"
                              });
                   };
  }

});


(function () {
    var dmws = nox.apps.directory.directorymanagerws;
    var group_util = null;
    dmws.getPrincipalGroupUtil = function () {
        if (group_util == null) {
            group_util = new dmws.PrincipalGroupUtil();
        }
        return group_util;
    }
})();

