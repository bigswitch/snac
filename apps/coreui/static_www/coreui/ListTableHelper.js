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

dojo.provide("nox.ext.apps.coreui.coreui.ListTableHelper");

/*
  This class provides basic functionality for a table 
  that employs filters, sorting and pagination. 
  For example, this is used by each of the principal list
  pages. 

*/ 


var dmws = nox.ext.apps.directory.directorymanagerws; 
var coreui = nox.ext.apps.coreui.coreui; 

dojo.require("nox.ext.apps.directory.directorymanagerws.Directories"); 

dojo.declare("nox.ext.apps.coreui.coreui.ListTableHelper",[], {

  filters : [], 
  dir_boxes : [],
  append_params : "", 
  
  /*
  args has the following parameters: 

  filters :  list of object indicating filtering fields. Field include:
                    id: the javascript id of the input node
                    urlParam: the parameter's name in the submitted URL

  dir_boxes: list of objects indicating auto-filled directory select 
              boxes.  Fields include: 
                      id: id of the input node for the select box
                      query: query string to limit the displayed directories
  append_params:  a string that will be appended to the URL before 
                  every submission
  */  
  constructor: function (args) {
        dojo.forEach(["filters","dir_boxes","append_params"], 
                  dojo.hitch(this, function(x) { 
                      if(args[x] != null)
                        this[x] = args[x]; 
                  })
        ); 
         
        // listen to apply filter for each 'onchange' 
        dojo.forEach(this.filters, dojo.hitch(this, function(f) { 
            var d = dojo.byId(f.id); 
            if(d) { 
              dojo.connect(d, "onchange", dojo.hitch(this, function() { 
                    // reset pagination and apply new filters
                    this.change_page(0); 
                  })
              );
            } 
          })
        );  
        // listen to clear filter if link is clicked
        var clear_node = dijit.byId("clear_btn");
        if(clear_node != null) 
          dojo.connect(clear_node, "onClick", dojo.hitch(this,"_clear_filter"));
        
        // have directories select box show only relevant directories
        dmws.Directories.datastore.update({ 
              onComplete: dojo.hitch(this,"_fill_dir_boxes")});  
        
  },

  _fill_dir_boxes : function() {
    dojo.forEach(this.dir_boxes, function(db) { 
      var f_node = dojo.byId(db.id);
      var cur_value = ""; 
      if (f_node.selectedIndex != null)
        cur_value = f_node[f_node.selectedIndex].value;
      f_node.length = 0; 
      var is_selected = "" == cur_value;
      f_node.options[0] = new Option("","",is_selected); 
    
      var q = {}; 
      q[db.query] = true;
      nox.ext.apps.directory.directorymanagerws.Directories.datastore.fetch({
          query : q, 
          onItem : function(x) {
              is_selected = x._data.name == cur_value;
              var o = new Option(x._data.name, x._data.name, is_selected); 
              f_node.options[f_node.length] = o; 
          }
        });
      });  // end forEach 
  }, 
 
  _apply_filter : function() {
    var url_params = "";
    dojo.forEach(this.filters, function(f) { 
            var node = dojo.byId(f.id); 
            if(node && node.value != "") { 
              url_params += f.urlParam + "=" + 
                encodeURIComponent(node.value) + "&";
            } 
          }
    ); 
    url_params += this.append_params;  
    var l = document.location; 
    var url = l.protocol + "//" + l.host + l.pathname + "?" + url_params;
    document.location = url;  
  }, 

 _clear_filter : function() {
    dojo.forEach(this.filters, function(f) {
        if(f.id == "filter_sort_attr" || f.id == "filter_sort_desc")
          return; // don't reset sorting when you clear the filter
        var d = dojo.byId(f.id);
        if(d)
          d.value = ""; 
      });
   this._apply_filter();  
 }, 

 change_page : function(start) { 
    var node = dojo.byId("filter_start");
    if(node != null)
      node.value = "" + start; 
    this._apply_filter();  
 },

 change_page_size : function(new_size) { 
    var node = dojo.byId("filter_count");
    if(node != null)
      node.value = "" + new_size; 
    this.change_page(0); // reset to page 0 and apply 
 }, 

 // called when sorting hyperlink is called for a column
 // if column is not current sort column, make it so and set
 // sort_desc to true.  If it is the current one, flip the value
 // of sort_desc. 
 sort_clicked : function(col_name) {
    var attr_node = dojo.byId("filter_sort_attr");
    var desc_node = dojo.byId("filter_sort_desc");
    if(attr_node == null || desc_node == null)
      return; 

    if(col_name == attr_node.value) { 
        desc_node.value = (desc_node.value == "true") ? "false" : "true"; 
    } else { 
        desc_node.value = "false"; 
        attr_node.value = col_name; 
    }
    // reset pagination and apply new filters
    this.change_page(0); 
 } 
 
});

