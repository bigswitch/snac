/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.directories");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.webapps.coreui.coreui.UpdateMgr");
dojo.require("nox.webapps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.webapps.coreui.coreui.simple_config");
dojo.require("nox.netapps.directory.directorymanagerws.Directories");
dojo.require("nox.netapps.directory.directorymanagerws.Directory");
dojo.require("nox.ext.apps.snackui.settingsui.LDAPTestDialog");

dojo.require("dojox.grid.DataGrid");

var coreui = nox.webapps.coreui.coreui
var dmws = nox.netapps.directory.directorymanagerws;
var sui = nox.ext.apps.snackui.settingsui;

var updatemgr = null;

var dirGrid = null;

// holds the list of all directory types, which is fetched on page load
var g_dir_type_list = [];

var g_types = ["principals"];
var g_principals = ["switch","host","location","user"];

var g_access_short = [ "RW", "RO", "NO"] ;
var g_access_long = [ "Read-Write", "Read-Only", "Disabled" ];

// directories with their name in this list do not appear anywhere in the UI
var g_blacklist = [ "discovered" ];

function get_dir_type_by_name(dir_type_name) {
    var singleton = dojo.filter(g_dir_type_list, function(item) {
        return (item.type_name == dir_type_name);
    });

    return singleton[0];
}

function add_directory() {
    var name_elem  = dojo.byId("new_dir_name");
    var type_elem  = dojo.byId("new_dir_type");
    dijit.byId("new_dir_dialog").hide();

    var cur_add_dir_name = name_elem.value;
    var dir_type = get_dir_type_by_name(type_elem.value);
    var cur_add_dir_node = {
        "name" : name_elem.value,
        "type" : type_elem.value,
        "enabled_principals" : dojo.clone(dir_type.supported_principals),
        "enabled_auth_types" : dojo.clone(dir_type.supported_auth_types),
        "config_params"      : dojo.clone(dir_type.default_config)
    };

    updatemgr.rawXhrPut({
        handleAs: 'json',
        url: "/ws.v1/directory/instance/" + encodeURI(cur_add_dir_name) + "?add=true",
        headers: { "content-type": "application/json" },
        putData: dojo.toJson(cur_add_dir_node),
        timeout: 30000,
        load: function(response, ioArgs)  {
            window.location.pathname =
                '/Settings/Directories/DirectoryInfo?name=' + 
                        encodeURIComponent(cur_add_dir_name);
        }
    });

    name_elem.value = "";
    type_elem.value = "";
}

function show_add() {
    var sbox = dojo.byId("new_dir_type");
    sbox.options.length = 0;
    dojo.forEach(g_dir_type_list, function(type_obj) {
        if (type_obj.supports_multiple_instances) {
            var o = document.createElement("option");
            o.innerHTML = type_obj.type_name;
            sbox.options.add(o);
        }
    });
    if(sbox.options.length > 0)
      dijit.byId("new_dir_dialog").show();
    else
      dijit.byId("no_dir_dialog").show();
}

function move(index, diff) {
    var old = dirGrid.getItem(index - diff).getValue('search_order');
    var new_ = dirGrid.getItem(index).getValue('search_order');
    dirGrid.getItem(index - diff).setValue('search_order', new_);
    dirGrid.getItem(index).setValue('search_order', old);

    search_order = [];

    var i = 0;
    while (true) {
        var item = dirGrid.getItem(i);
        if (item == null) { break; }

        i++;

        /* For whatever reason, the grid returns items originally
         * filtered out */
        var name = item.getValue('name');
        if (dojo.indexOf(g_blacklist, name) != -1) { continue; }

        search_order[item.getValue('search_order')] = name;
    }

    updatemgr.rawXhrPut({
        handleAs: 'json',
        url: "/ws.v1/directory/search_order",
        headers: { "content-type": "application/json" },
        putData: dojo.toJson(search_order),
        timeout: 5000,
        load: change_ok
    });
}

function change_ok(response, ioArgs) {
  dmws.Directories.datastore.update({
      onComplete: function() { 
        dirGrid._refresh(); 
      }
  });

  return null;
}

function remove(dir_name) {
    updatemgr.xhr("DELETE", {
        handleAs: 'json',
        url: "/ws.v1/directory/instance/" + dir_name,
        headers: { "content-type": "application/json" },
        putData: "{}",
        timeout: 5000,
        load: function() { 
            // delete with this store is broken.
            // since removing a directory is so rare, just
            // refresh the damn page.
            document.location = document.location; 
        }
    });
}

function init_page() {
    updatemgr = coreui.getUpdateMgr();
    updatemgr.xhrGet({
        url: "/ws.v1/directory/type",
        load: function (response, ioArgs) {
            g_dir_type_list = response.items;
        },
        timeout: 30000,
        handleAs: "json"
    });

    dirGrid = new dojox.grid.DataGrid({
            store: dmws.Directories.datastore,
            query: { 
                name: function(n) {
                    return dojo.indexOf(g_blacklist, n) == -1;
                }
            },
            selectionMode: 'single', 
            autoHeight: true,
            canSort: function() {
                return false;
            },
            sort: [ { attribute: "search_order" } ],
            structure: [
    { name: "Name", field: "name", relWidth: 4 },
    { name: "Directory Type", field: "type", relWidth: 4 },
    { name: "Search Order", relWidth: 1, get: function(index) {
        var fd = (index == 0) ? " disabled='true'" : "";
        var ld = (index == this.grid.rowCount-1) ? " disabled='true'" : "";

        var up = '';
        if (index != 0) {
            up = "<button class='moveUp'" + fd + 
                "><div class='moveUpIcon'></div></button>";
        }
        var down = '';
        if (index != this.grid.rowCount-1) {
            if (index == 0) {
                down = "<button class='moveDown'" + ld + 
                    " style='margin: 0 8px 0 46px;'><div class='moveDownIcon'></div></button>";
            } else {
                down = "<button class='moveDown'" + ld + 
                    "><div class='moveDownIcon'></div></button>";
            }
        }

        return up + down;
    } },
    { name: 'Test Directory Access',
      get: function (inRowIndex) { 
            return "<center><button dojoType='dijit.form.Button'" + 
              "class='testButton'>Start Test</button></center>";
      },
      relWidth: 2
    }
                        ]
	});

  dojo.byId("directories_container").appendChild(dirGrid.domNode);
	dirGrid.startup();

	dojo.connect(dirGrid.selection, "onChanged", function(){
		var selected = dirGrid.selection.getSelectedCount();
		configure_selected.attr('disabled', !(selected == 1));
		delete_selected.attr('disabled', !(selected > 0));
	});
	dojo.connect(dirGrid, "onCellClick", function(e){
		if (e.cellIndex != 2 && e.cellIndex != 3) { return; }
		if (e.target.tagName && 
                    e.target.tagName.toLowerCase() != "button") { return; }

		var item = dirGrid.getItem(e.rowIndex);
		if (!item){ return; }

		if (dojo.hasClass(e.target, "moveUp")){
			move(e.rowIndex, 1);
			dirGrid._refresh(true);
                        dirGrid.selection.deselectAll();
		} else if(dojo.hasClass(e.target, "moveDown")){
			move(e.rowIndex, -1);
			dirGrid._refresh(true);
                        dirGrid.selection.deselectAll();
		} else if (dojo.hasClass(e.target, "testButton")) {
                    var props = { 
                        id : "ldap_test",
                        name : item.getValue('name')
                    };

                    if (dijit.byId(props.id)) {
                        dijit.byId(props.id).destroy();
                    }

                    appr = new sui.LDAPTestDialog(props);
                    dojo.body().appendChild(appr.domNode);
                    appr.startup();
                    appr.show();
                }
	});
}

dojo.addOnLoad(init_page);
