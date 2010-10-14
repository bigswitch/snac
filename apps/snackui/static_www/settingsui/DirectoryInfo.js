/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DirectoryInfo");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.ext.apps.coreui.coreui.simple_config");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directory");
dojo.require("nox.ext.apps.directory.directorymanagerws.DirectoryStore");

dojo.require("dojo.data.ItemFileWriteStore");

var coreui = nox.ext.apps.coreui.coreui;
var dmws = nox.ext.apps.directory.directorymanagerws;

var directory = null;
var notFoundError = false;
var settingsInspector = null;

// holds the list of all directory types, which is fetched on page load
var g_dir_type_list = [];
var g_principals = ["switch","host","location","user"];
var g_access_short = [ "RW", "RO", "NO"] ;
var g_access_long = [ "Read-Write", "Read-Only", "Disabled" ];

function show_invalid_error() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "block"});
    dojo.style(dojo.byId("directory-info"), {display: "none"});
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "none"});
    dojo.style(dojo.byId("directory-info"), {display: "block"});
}

function get_config_value(item, key) {
    if (item.getValue('config_params')) {
        return item.getValue('config_params')[key];
    } else {
        return '';
    }
}

function set_config_value(item, key, value) {
    enable_buttons();

    return item.getValue('config_params')[key] = value;
}

function rollback() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    directory.revert();

    if (settingsInspector)
        settingsInspector.update();
}

function commit() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    directory.save();

    window.location.pathname = '/Settings/Directories';
}

function get_dir_type_by_name(dir_type_name) {
    var singleton = dojo.filter(g_dir_type_list, function(item) {
        return (item.type_name == dir_type_name);
    });
    return singleton[0];
}

function create_edit_select(supported,enabled, principal_type) {
    var supported_index = dojo.indexOf(g_access_short,supported[principal_type]);
    if(supported_index == g_access_short.length - 1) {
        return undefined;
    }
    var sbox = document.createElement("select");
    sbox.id = principal_type;
    for( i = supported_index; i < g_access_short.length; i++) {
        var x = g_access_short[i];
        var o = document.createElement("option");
        o.innerHTML = g_access_long[i];
        if (enabled[principal_type] == x){
            o.selected = "yes";
        }
        sbox.appendChild(o);
    }
    return sbox;
}

function enable_buttons() {
    commit_button.attr('disabled', false);
    rollback_button.attr('disabled', false);
}

function init_page() {
    commit_button.attr('disabled', true);
    rollback_button.attr('disabled', true);

    coreui.base.update_page_title("Directory Settings for " + selected_directory);
    var updatemgr = coreui.getUpdateMgr();

    updatemgr.xhrGet({
        url: "/ws.v1/directory/type",
        load: function (response, ioArgs) {
            g_dir_type_list = response.items;
        },
        timeout: 30000,
        handleAs: "json"
    });

    directory = new dmws.Directory({
        initialData: {
            name: selected_directory,
            enabled_principals: [], 
            enabled_groups: []
        },
       updateList: [ "info" ]
    });


    var getBasicModel = function() {
        return [
    { name: "enabled_principals", header: "Principals Enabled",
      get: function(item) {
            if (!item.getValue('type')) { return ''; }

            var dir_type = get_dir_type_by_name(item.getValue('type'));
            var supported = dir_type.supported_principals;
            var enabled = item.getValue('enabled_principals');

            var table = document.createElement("table");
            dojo.forEach(g_principals, function(x) {
                var r = table.insertRow(-1);
                var supported_index = dojo.indexOf(g_access_short,supported[x]);
                if(supported_index == g_access_short.length - 1) {
                    /* Don't add unsupported ones */
                } else {
                    var cell1 = document.createElement("td");
                    cell1.innerHTML = x.substring(0, 1).toUpperCase() +
                        x.substring(1);

                    var cell2 = document.createElement("td");
                    var options = new dojo.data.ItemFileWriteStore({
                            data: { identifier: 'name', items: [] }
                        });
                    if (dijit.byId(x + "_select")) { 
                        dijit.byId(x + "_select").destroy();
                    }
                    var sbox = new dijit.form.FilteringSelect({
                        id: x + "_select",
                        name: x + "_select",
                        store: options
                    }, cell2);

                    sbox.startup();
                    cell2.appendChild(sbox.domNode);

                    var supported_index = dojo.indexOf(g_access_short,supported[x]);
                    for(var i = supported_index; i < g_access_short.length;i++){
                        var s = g_access_short[i];
                        options.newItem({ name: g_access_long[i] });
                        if (enabled[x] == s) { sbox.setValue(g_access_long[i]);}
                    }

                    r.appendChild(cell1);
                    r.appendChild(cell2);

                    dojo.connect(sbox, 'onChange', function (e) {
                        var enabled = item.getValue('enabled_principals');
                        var j = dojo.indexOf(g_access_long, sbox.getValue());
                        enabled[x] = g_access_short[j];
                        item.setValue('enabled_principals', enabled);

                        enable_buttons();
                    });
                }
            });

            return table;
      },
      editable: true
    },
    { name: "enabled_auth_types", header: "Authentication Types Enabled",
      get: function(item) {
            if (!item.getValue('type')) { return ''; }

            var dir_type = get_dir_type_by_name(item.getValue('type'));
            var supported = dir_type.supported_auth_types;
            var enabled = item.getValues('enabled_auth_types');
            var div = document.createElement("div");

            dojo.forEach(supported, function(x) {
                if (dijit.byId(x + "_checkbox")) { 
                    dijit.byId(x + "_checkbox").destroy();
                }

                var box = new dijit.form.CheckBox({
                    id: x + "_checkbox",
                    type: "checkbox",
                    checked: null
                });
                box.startup();
                box.setChecked(dojo.indexOf(enabled, x) != -1);

                div.appendChild(box.domNode);

                var l = document.createElement("label");
                l.innerHTML = x;
                l.htmlFor = x + "_checkbox";
                div.appendChild(l);
                var br = document.createElement("br");
                div.appendChild(br);

                dojo.connect(box, "onClick", function(event) {
                    var o = item.getValues('enabled_auth_types');
                    var n = dojo.filter(o, function(i) { return i != x; });

                    if (box.getValue() == false) {
                        /* Value will be removed */
                    } else {
                        n.push(x);
                    }
                    item.setValues('enabled_auth_types', n);

                    enable_buttons();
                });
            });

            return div;
      },
      editable: true
    } 
                ]};

    var getLDAPModel = function() {
        return [
    { name: "ldap_uri", header: "Server URI",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'ldap_uri'); },
      getEdit: function(item) { return get_config_value(item, 'ldap_uri'); },
      editSet: function(item, value) { set_config_value(item, 'ldap_uri', value); },
      editable: true
    },
    { name: "ldap_version", header: "LDAP Version",
      get: function(item) {

            var box2 = dijit.byId("ldap_version_2_radiobutton");
            dojo.connect(box2, "onClick", function(event) {
                    if (box2.getValue() == '2') {
                        set_config_value(item, 'ldap_version', 2);
                    } else {
                        set_config_value(item, 'ldap_version', 3);
                    }
            });

            var box3 = dijit.byId("ldap_version_3_radiobutton");
            dojo.connect(box3, "onClick", function(event) {
                    if (box3.getValue() == '3') {
                        set_config_value(item, 'ldap_version', 3);
                    } else {
                        set_config_value(item, 'ldap_version', 2);
                    }
            });
            if (get_config_value(item, 'ldap_version') == 3) {
                box2.setChecked(false);
                box3.setChecked(true);
            } else {
                box2.setChecked(true);
                box3.setChecked(false);
            }

            dojo.style(dojo.byId("ldap_version"), { display: "block" });
            return dojo.byId("ldap_version");
        }
      //getEdit: function(item) { return get_config_value(item, 'ldap_version');},
      //editSet: function(item, value) { set_config_value(item, 'ldap_version',
      //                                               value); },
      //editable: true,
    },
    { name: "use_ssl", header: "Use SSL/TLS",
      get: function(item) {
            var box = dijit.byId("use_ssl_checkbox");
            dojo.connect(box, "onClick", function(event) {
                    if (box.getValue() == false) {
                        set_config_value(item, 'use_ssl', 0);
                    } else {
                        set_config_value(item, 'use_ssl', 1);
                    }
            });
            box.setChecked(get_config_value(item, 'use_ssl') == 1);

            dojo.style(dojo.byId("use_ssl"), {display: "block"});
            return dojo.byId("use_ssl");
      }
      //editable: true,
    },
    { name: "search_subtree", header: "Search Subtree",
      get: function(item) {
            var box = dijit.byId("search_subtree_checkbox");
            dojo.connect(box, "onClick", function(event) {
                    if (box.getValue() == false) {
                        set_config_value(item, 'search_subtree', 0);
                    } else {
                        set_config_value(item, 'search_subtree', 1);
                    }
            });
            box.setChecked(get_config_value(item, 'search_subtree') == 1);

            dojo.style(dojo.byId("search_subtree"), {display: "block"});
            return dojo.byId("search_subtree");
      }
      //editable: true,
    },
    { name: "follow_referrals", header: "Follow Referrals",
      get: function(item) {
            var box = dijit.byId("follow_referrals_checkbox");
            dojo.connect(box, "onClick", function(event) {
                    if (box.getValue() == false) {
                        set_config_value(item, 'follow_referrals', 0);
                    } else {
                        set_config_value(item, 'follow_referrals', 1);
                    }
            });
            box.setChecked(get_config_value(item, 'follow_referrals') == 1);

            dojo.style(dojo.byId("follow_referrals"), {display: "block"});
            return dojo.byId("follow_referrals");
      }
      //editable: true,
    },
    { name: "browser_user_bind_dn", header: "Browser User DN",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'browser_user_bind_dn'); },
      getEdit: function(item) { return get_config_value(item, 'browser_user_bind_dn'); },
      editSet: function(item, value) { set_config_value(item, 'browser_user_bind_dn', value); },
      editable: true
    },
    { name: "browser_user_bind_pw", header: "Browser User Password",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'browser_user_bind_pw'); },
      getEdit: function(item) { return get_config_value(item, 'browser_user_bind_pw'); },
      editSet: function(item, value) { set_config_value(item, 'browser_user_bind_pw', value); },
      editable: true
    },
    {name: "user-sep", separator: true},
    { name: "base_dn", header: "User Base DN",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'base_dn'); },
      getEdit: function(item) { return get_config_value(item, 'base_dn'); },
      editSet: function(item, value) { set_config_value(item, 'base_dn', value); },
      editable: true
    },
    { name: "user_lookup_filter", header: "User Lookup Filter",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'user_lookup_filter'); },
      getEdit: function(item) { return get_config_value(item, 'user_lookup_filter'); },
      editSet: function(item, value) { set_config_value(item, 'user_lookup_filter', value); },
      editable: true
    },
    { name: "search_filter", header: "User Search Filter",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'search_filter'); },
      getEdit: function(item) { return get_config_value(item, 'search_filter'); },
      editSet: function(item, value) { set_config_value(item, 'search_filter', value); },
      editable: true
    },
    { name: "username_field", header: "Username Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'username_field'); },
      getEdit: function(item) { return get_config_value(item, 'username_field'); },
      editSet: function(item, value) { set_config_value(item, 'username_field', value); },
      editable: true
    },
    { name: "name_field", header: "Real Name Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'name_field'); },
      getEdit: function(item) { return get_config_value(item, 'name_field'); },
      editSet: function(item, value) { set_config_value(item, 'name_field', value); },
      editable: true
    },
    { name: "uid_field", header: "UID Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'uid_field'); },
      getEdit: function(item) { return get_config_value(item, 'uid_field'); },
      editSet: function(item, value) { set_config_value(item, 'uid_field', value); },
      editable: true
    },
    { name: "phone_field", header: "Phone Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'phone_field'); },
      getEdit: function(item) { return get_config_value(item, 'phone_field'); },
      editSet: function(item, value) { set_config_value(item, 'phone_field', value); },
      editable: true
    },
    { name: "email_field", header: "Email Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'email_field'); },
      getEdit: function(item) { return get_config_value(item, 'email_field'); },
      editSet: function(item, value) { set_config_value(item, 'email_field', value); },
      editable: true
    },
    { name: "loc_field", header: "Location Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'loc_field'); },
      getEdit: function(item) { return get_config_value(item, 'loc_field'); },
      editSet: function(item, value) { set_config_value(item, 'loc_field', value); },
      editable: true
    },
    { name: "desc_field", header: "Description Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'desc_field'); },
      getEdit: function(item) { return get_config_value(item, 'desc_field'); },
      editSet: function(item, value) { set_config_value(item, 'desc_field', value); },
      editable: true
    },
    {name: "group-sep", separator: true},
    { name: "user_obj_groups_attr", header: "User Entity Group Attribute",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'user_obj_groups_attr'); },
      getEdit: function(item) { return get_config_value(item, 'user_obj_groups_attr'); },
      editSet: function(item, value) { set_config_value(item, 'user_obj_groups_attr', value); },
      editable: true
    },
    { name: "group_base_dn", header: "Group Base DN",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'group_base_dn'); },
      getEdit: function(item) { return get_config_value(item, 'group_base_dn'); },
      editSet: function(item, value) { set_config_value(item, 'group_base_dn', value); },
      editable: true
    },
    { name: "group_filter", header: "Group Search Filter",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'group_filter'); },
      getEdit: function(item) { return get_config_value(item, 'group_filter'); },
      editSet: function(item, value) { set_config_value(item, 'group_filter', value); },
      editable: true
    },
    { name: "groupname_field", header: "Group Name Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'groupname_field'); },
      getEdit: function(item) { return get_config_value(item, 'groupname_field'); },
      editSet: function(item, value) { set_config_value(item, 'groupname_field', value); },
      editable: true
    },
    { name: "ugroup_desc_field", header: "Group Description Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'ugroup_desc_field'); },
      getEdit: function(item) { return get_config_value(item, 'ugroup_desc_field'); },
      editSet: function(item, value) { set_config_value(item, 'ugroup_desc_field', value); },
      editable: true
    },
    { name: "ugroup_member_field", header: "Group Member Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'ugroup_member_field'); },
      getEdit: function(item) { return get_config_value(item, 'ugroup_member_field'); },
      editSet: function(item, value) { set_config_value(item, 'ugroup_member_field', value); },
      editable: true
    },
    { name: "ugroup_subgroup_field", header: "Group Subgroup Field",
      editor: dijit.form.TextBox,
      get: function(item) { return get_config_value(item, 'ugroup_subgroup_field'); },
      getEdit: function(item) { return get_config_value(item, 'ugroup_subgroup_field'); },
      editSet: function(item, value) { set_config_value(item, 'ugroup_subgroup_field', value); },
      editable: true

    },
    { name: "group_posix_mode", header: "Group POSIX Mode",
      get: function(item) {
            var box = dijit.byId("group_posix_mode_checkbox");
            dojo.connect(box, "onClick", function(event) {
                    if (box.getValue() == false) {
                        set_config_value(item, 'group_posix_mode', 0);
                    } else {
                        set_config_value(item, 'group_posix_mode', 1);
                    }
            });
            box.setChecked(get_config_value(item, 'group_posix_mode') == 1);

            dojo.style(dojo.byId("group_posix_mode"), {display: "block"});
            return dojo.byId("group_posix_mode");
      }
      //editable: true,
    }
                ]};

    directory.update({
        onComplete: function () {
            if (notFoundError != true) {
                if (directory.getValue('type') == 'LDAP') {
                    settingsInspector = new coreui.ItemInspector({
                        item: directory,
                        model: Array.concat(getBasicModel(), getLDAPModel())
                    });
                } else {
                    settingsInspector = new coreui.ItemInspector({
                        item: directory,
                        model: getBasicModel()
                    });
                }                                

                dojo.byId("directory-info").appendChild(settingsInspector.domNode);

                settingsInspector.update();
                show_monitor_content();
            }
            notFoundError = false;
        },
        errorHandlers: {
            404: function (err, ioArgs) {
                notFoundError = true;
                show_invalid_error();
            }
        }
    });
}

dojo.addOnLoad(init_page);
