
dojo.provide("nox.apps.directory.directorymanagerws.PrincipalInfoEditUtils");

dojo.require("nox.apps.directory.directorymanagerws.Directories"); 

(function () {

var u = nox.apps.directory.directorymanagerws.PrincipalInfoEditUtils;

u.get_attr_row = function(att, hdr, is_editable) {
    if (is_editable) {
        return {name: att,
                header: hdr,
                attr: att,
                editor: dijit.form.TextBox,
                editAttr: att,
                editSet: function (item, value) {
                    item.setValue(att, value);
                    item.save();
                }
        };
    } else {
        return {
            name: att,
            header: hdr,
            attr: att
        };
    }
}   
  
// changing name is different from changing most attrs, since 
// we must change to a new URL. 
u.get_name_row = function(hdr,is_editable) {
        if (is_editable) {
            return {name: "name", header: hdr, attr: "principalName",
                    editor: dijit.form.TextBox,
                    editAttr: "principalName",
                    editSet: function (item, value) {
                    item.rename({ 
                            name: value,
                            onComplete: function (item) {
                                document.location = item.uiMonitorPath();
                            }, 
                            onError: function (item) {
                              console_log("Error occurred during rename.");
                            }
                        });
                }
            }
        } else {
            return {name: "name", header: hdr, attr: "principalName" };
        }
}

u.get_directory_row = function(ptype, dirname,is_editable) {
 
  // this is called in the context of the filtering select 
  // UGLY: we can't query the store asynchronously within a
  // validation function, so we peak at a 'private' member.
  var validate_dir_fn = function() { 
    var v = this.getDisplayedValue();
    var store = nox.apps.directory.directorymanagerws.Directories.datastore;  
    if(v == dirname) 
      return true; 
    if(store._items == null) 
      return false; // no way to validate
    for(var i = 0; i < store._items.length; i++) { 
      if (v == store._items[i]._data['name'])
        return true; 
    }  
    return false; 
  }
  
  var n = "directory"; 
  var hdr = "Directory Name"; 
  var attr = "directoryName";
  // discovered should appear RO, expect that you can move
  // objects out of it.   
  if (is_editable || dirname == "discovered") {
    query = {}; 
    query["write_" + ptype + "_enabled"] = true; 
    return {
      name: n, 
      header: hdr, 
      attr: attr,
      editor: dijit.form.FilteringSelect,
      editorProps: {
          store: nox.apps.directory.directorymanagerws.Directories.datastore,
          query: query, 
          isValid : validate_dir_fn 
      }, 
      editAttr: "directoryName",
      editSet: function (item, value) {
          item.change_directory({
              name: value,
              onComplete: function (item) {
                  document.location = item.uiMonitorPath();
              }
          });
        }
    };
  } else { 
      return {name: n, header: hdr, attr: attr };
  }   
}

u.get_groups_row = function(groupsStore,allGroupsStore,is_editable) {
      var groupList = new coreui.ItemList({
            store: groupsStore,
            labelAttr: "uiMonitorLink",
            sort: {
                decreasing: false,
                attr: "displayName"
            },
            changeAnimFn: coreui.base.changeHighlightFn,
            ignoreNull: true
        });


        if (false) {
        //FIXME: Once we are ready to use sitepen's nice group dialog,
        // this is how we should do it. 
        //if (is_editable) {
            return {name: "groups", header: "Group Membership", noupdate: true, 
                    editable: true, 
                    dialogEditor: true,
                    editor: coreui.ItemListEditor,
                    editorProps: { title: "Group Membership", 
                                   selectedStore: groupsStore, 
                                   allStore: allGroupsStore },
                    get: function (item) {
                    return groupList.domNode;
                }
            };
        } else {
            // Should block delete here somehow, but since ItemList
            // delete is broken anyway, nothing done yet.
            return {name: "groups", header: "Group Membership", noupdate: true, 
                    editor: coreui.ItemListEditor,
                    get: function (item) {
                    return groupList.domNode;
                }
            };
        }
}

})();
