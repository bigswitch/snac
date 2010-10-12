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

dojo.provide("nox.apps.directory.directorymanagerws.PrincipalListFilter");

dojo.require("nox.apps.coreui.coreui.ListTableHelper"); 
dojo.require("nox.apps.directory.directorymanagerws.Host");
dojo.require("nox.apps.directory.directorymanagerws.Switch");
dojo.require("nox.apps.directory.directorymanagerws.User");
dojo.require("nox.apps.directory.directorymanagerws.Location");

(function () {

var dmws = nox.apps.directory.directorymanagerws; 
var coreui = nox.apps.coreui.coreui; 

var u = nox.apps.directory.directorymanagerws.PrincipalListFilter;

var ctor_map = { "host" : dmws.Host, 
                 "user" : dmws.User, 
                 "switch" : dmws.Switch,
                 "location" : dmws.Location };                  

u.init_principal_list_page = function(ptype) {
  var ctor = ctor_map[ptype];
  u.setup_simple_listpage_edit_hooks(ptype,ctor); 

  //to simplify, any filter that can be on any list page page is included.
  return new nox.apps.coreui.coreui.ListTableHelper({ 
      filters : [
          { id : "filter_name", urlParam : "name_glob"} ,
          { id : "filter_directory", urlParam : "directory"} ,
          { id : "filter_active", urlParam : "active"}, 
          { id : "filter_start", urlParam : "start"},  
          { id : "filter_count", urlParam : "count"},
          { id : "filter_sort_attr", urlParam : "sort_attr"}, 
          { id : "filter_sort_desc", urlParam : "sort_desc"}, 
          // host specific 
          { id : "filter_ip", urlParam : "nwaddr_glob"} ,
          { id : "filter_mac", urlParam : "dladdr_glob"} ,
          { id : "filter_loc", urlParam : "location_name_glob"}, 
          // location specific  
          { id : "filter_switch_name", urlParam : "switch_name"} ,
          { id : "filter_port_name", urlParam : "port_name"} 
        ], 
     dir_boxes : [ 
        {  id : "filter_directory", query : "read_" + ptype + "_enabled" } 
        ]
    }); 
}


function get_selected_names() { 
  // for some reason, dojo.query with 'checked' attr doesn't work
  var selected_names = []; 
  var selected_boxes = dojo.query(".select-box");
  selected_boxes.forEach(function(box) { 
      if(box.checked)
          selected_names.push(box.id); 
  }); 
  return selected_names; 
} 

u.setup_simple_listpage_edit_hooks = function(ptype, ctor) {
        var add_btn = dijit.byId("add_principal_button"); 
        if(add_btn != null) { 
          dojo.connect(add_btn, "onClick", function() {
            var title = "Add " + ptype.substring(0,1).toUpperCase() + 
                                  ptype.substring(1) + " Principal"; 
            var dialog = dmws.getPrincipalUtil().show_modify_dialog(ptype, 
                                                        null,title, ctor);
          });
        } 
        var del_btn = dijit.byId("remove_principal_button"); 
        if(del_btn != null) {

          dojo.connect(del_btn, "onClick", function() {
              var selected_names = get_selected_names(); 
              for(var i = 0; i < selected_names.length; i++) { 
                var full_name = selected_names[i]; 
                var dir_name = full_name.split(";")[0]; 
                var q = { name : dir_name }; 
                q["write_" + ptype + "_enabled"] = true; 
                var match_found = false;
                var is_last = i == (selected_names.length - 1); 
                var after_dir_query = dojo.hitch(this, 
                    function(call_update) {
                      if(match_found) { 
                          var p = new ctor({ initialData : { name: full_name}});
                          p.deleteOnServer({ 
                              onComplete : function() {
                                    if(call_update) {
                                        // document.location.reload()
                                        // tries to keep old checkboxes 
                                        document.location = document.location;  
                                    }
                              } 
                          }); 
                      } else {
                           
                           coreui.UpdateErrorHandler.showError(
                                "Cannot remove a " + ptype + 
                                " from read-only directory '" + dir_name + "'",
                                    { header_msg : "Removal Failed:", 
                                      hide_retry : true,
                                      validation_error: true });

                      } 

                }, is_last); // end dojo.hitch
               
                 
                dmws.Directories.datastore.fetch({
                            query : q,  
                            onItem : function (ignore) { 
                              match_found = true; 
                            },  // end onItem
                            onComplete : after_dir_query 
              }); // end fetch 

            }
          });
          //FIXME: enable/disable delete button based on whether anything is checked
          //del_btn.setAttribute('disabled', true);
        }
    
}

u.setup_simple_listpage_button_action = function(button_id, ctor, fn_name, 
                                              onComplete) {
        var btn = dijit.byId(button_id); 
        if (btn != null) { 
            dojo.connect(btn, "onClick", function() {
              var selected_names = get_selected_names();
              for(var i = 0; i < selected_names.length; i++) { 
                var is_last = i == (selected_names.length - 1); 
                var p = new ctor({ initialData : { name: selected_names[i]}});
                p[fn_name](dojo.hitch(this,function(do_oncomplete, response) {
                                    if(do_oncomplete && onComplete != null) {
                                        onComplete();  
                                    }
                              }, is_last)); // end dojo.hitch
              }
          });
          // FIXME: disable button until a checkbox is selected
          //btn.setAttribute('disabled', true);
        }
        
}
 

u.setup_simple_listpage_deauth_hooks = function(ctor) { 
  u.setup_simple_listpage_button_action("deauth_principal_button", ctor, 
                  "delete_binding", 
                  function() { 
                    // document.location.reload() tries to keep old checkboxes 
                    document.location = document.location;   
                  }
  ); 
}

u.setup_switch_registration_hooks = function() { 
  var regSwitchButton = dijit.byId("regSwitchButton"); 
  dojo.connect(regSwitchButton, "onClick", function() { 
                var selected_names = get_selected_names();
                var selected_items = []; 
                for(var i =0; i < selected_names.length; i++) { 
                  var s = new dmws.Switch({ 
                            initialData : { name : selected_names[i] }, 
                            updateList: [ "approval" ]
                      }); 
                  selected_items.push(s); 
                }  
                dmws.getSwitchUtil().register_switch(selected_items, function() { 
                    document.location = document.location; 
                  }); 
              }); 

  var deregSwitchButton = dijit.byId("deregSwitchButton"); 
  dojo.connect(deregSwitchButton, "onClick", function() {
              var selected_names = get_selected_names(); 
              for(var i = 0; i < selected_names.length; i++) { 
                var is_last = i == (selected_names.length - 1); 
                var p = new dmws.Switch({ 
                            initialData : { name : selected_names[i] }, 
                            updateList: [ "approval" ]
                      });
                p.update({ onComplete: function() { 
                  p.set_approval(false, 
                              dojo.hitch(this,function(do_oncomplete, response) {
                                    if(do_oncomplete) {
                                        document.location = document.location;   
                                    }
                              }, is_last)); // end dojo.hitch
                }
              }); 
          } // end for-loop
 });
}
 
})();

