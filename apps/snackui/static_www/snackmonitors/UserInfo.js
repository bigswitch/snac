/*
 * Copyright 2008 (C) Nicira
 */

dojo.provide("nox.ext.apps.snackui.snackmonitors.UserInfo");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.netapps.directory.directorymanagerws.UserStore");
dojo.require("nox.webapps.coreui.coreui.ItemList");
dojo.require("nox.webapps.coreui.coreui.ItemListEditor");
dojo.require("nox.webapps.coreui.coreui.ItemInspector");
dojo.require("dijit.form.FilteringSelect");
dojo.require("nox.netapps.user_event_log.networkevents.NetEvents");
dojo.require("nox.netapps.directory.directorymanagerws.Directories"); 
dojo.require("nox.netapps.directory.directorymanagerws.PrincipalInfoEditUtils"); 
dojo.require("nox.netapps.directory.directorymanagerws.PrincipalModifyDialog"); 

var coreui = nox.webapps.coreui.coreui;
var dmws = nox.netapps.directory.directorymanagerws; 
var pinfo_util = nox.netapps.directory.directorymanagerws.PrincipalInfoEditUtils;

var user = null; 
var userInspector = null;
var netevent_log = null;
var notFoundError = false;
var default_error_handlers =  {
    404: function (response, ioArgs) {
        show_invalid_error();
    }
};

hostStore = null; 

var is_editable = false; // default. this value is set below

function show_invalid_error() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "block"});
    dojo.style(dojo.byId("monitor_content"), {display: "none"});
    dojo.style(dojo.byId("change-password-button"), {display: "none"});
}

function show_monitor_content() {
    dojo.style(dojo.byId("invalid-name-error"), {display: "none"});
    dojo.style(dojo.byId("monitor_content"), {display: "block"});
    dojo.style(dojo.byId("change-password-button"), {display: "block"});
}


function show_change_cred() {
    dijit.byId("change_cred_dialog").show(); 
}

function change_cred() {
    var new_passwd = dojo.byId("new_cred");
    var conf_passwd = dojo.byId("confirm_cred");
    dijit.byId("change_cred_dialog").hide();

    if (new_passwd.value != conf_passwd.value) {
        new_passwd.value = "";
        conf_passwd.value = "";
        coreui.UpdateErrorHandler.showError("Passwords don't match.",
                                            { header_msg: "Invalid Password",
                                              hide_retry: true,
                                              validation_error: true
                                            });
        return;
    } else if (new_passwd.value == "") {
        coreui.UpdateErrorHandler.showError("Cannot set to empty string.",
                                            { header_msg: "Invalid Password",
                                              hide_retry: true,
                                              validation_error: true
                                            });
        return;
    }

    var pass = new_passwd.value;
    new_passwd.value = "";
    conf_passwd.value = "";

    if (userInspector == null || userInspector.item == null) {
        coreui.UpdateErrorHandler.showError("No user to set password on.",
                                            { header_msg: "Empty User",
                                              hide_retry: true,
                                              validation_error: true
                                            });
        return;
    }

    userInspector.item.saveCred(pass);
    userInspector.update();
}

function clear_cred() {
    dojo.byId("new_cred").value = "";
    dojo.byId("confirm_cred").value = "";
    dijit.byId("change_cred_dialog").hide();

    if(user.getValue("user_id") == "0") { 
        coreui.UpdateErrorHandler.showError(
              "Clearing the main administrator password is not allowed.",
                                            { header_msg: "Invalid Operation: ",
                                              hide_retry: true,
                                              validation_error: true
                                            });
        return;
    }

    if (userInspector == null || userInspector.item == null) {
        coreui.UpdateErrorHandler.showError("No user to set password on.",
                                            { header_msg: "Unknown User: ",
                                              hide_retry: true,
                                              validation_error: true
                                            });
        return;
    }

    userInspector.item.saveCred(null);
    userInspector.update();    
}

function cancel_cred() {
    dojo.byId("new_cred").value = "";
    dojo.byId("confirm_cred").value = "";
    dijit.byId("change_cred_dialog").hide();
}

function init_page() {
    coreui.base.update_page_title("User Information");

    user = new nox.netapps.directory.directorymanagerws.User({
        initialData: { name: selected_user },
        updateList: [ "status", "info", "cred" ]
    });

    if (user.isNull()) {
        show_invalid_error();
        return;
    }
    dmws.Directories.datastore.update({ 
      onComplete: function () { 
        dmws.Directories.datastore.fetch({ 
            query : { name: user.directoryName() }, 
            onItem: function (directory) {
              if (notFoundError != true) {
                is_editable = 
                    directory.getValue('enabled_principals')['user'] == 'RW';
                change_cred_button.attr('disabled', !is_editable);
                if (is_editable) {
                    var auth_types = directory._data.enabled_auth_types;
                    var pw_editable = (dojo.indexOf(auth_types, "simple_auth") != -1);
                    change_cred_button.attr('disabled', !pw_editable);
                }
              }
              notFoundError = false;
              build_page(); 
            }
        });
      }
    }); 

}

function build_page() { 
    coreui.base.set_nav_title([
        {
            title_text: "User:",
            nav_text: "Users",
            nav_url: "/Monitors/Users"
        },
        {
            title_text: user.directoryName() + " -",
            nav_text: user.directoryName(),
            nav_url: "/Monitors/Users?directory=" + user.directoryName()
        },
        {
            title_text: user.principalName() + " -",
            nav_text: user.principalName(),
            nav_url: user.uiMonitorPath()
        }
    ]);

    var notFoundError = false;

    hostsStore = user.hostStore({
        userObj: this,
        autoUpdate: {
            errorHandlers: default_error_handlers
        }
    });

    var allGroupsStore = new dmws.UserGroupStore({
        url: "/ws.v1/group/user",
        autoUpdate: {
            errorHandlers: default_error_handlers
        }
    });

    var groupsStore = user.groupStore({
        userObj: this,
        autoUpdate: {
            errorHandlers: default_error_handlers
        }
    });

    var hostList = new coreui.ItemList({
        store: hostsStore,
        labelAttr: "uiMonitorLink",
        sort: {
            decreasing: false,
            attr: "principalName"
        },
        changeAnimFn: coreui.base.changeHighlightFn,
        ignoreNull: true
    });
    
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

      var get_editable_name = function () {
        if (principal_editable) {
            return {name: "name", header: "User Name", attr: "principalName",
                    editor: dijit.form.TextBox,
                    editAttr: "principalName",
                    editSet: function (item, value) {
                    item.rename({ 
                            name: value,
                            onComplete: function (item) {
                                document.location = item.uiMonitorPath();
                            }
                        });
                }
            }
        } else {
            return {name: "name", header: "User Name", attr: "principalName" };
        }
      }

      userInspector = new coreui.ItemInspector({
                item: user,
                changeAnimFn: coreui.base.changeHighlightFn,
                model: [
      pinfo_util.get_name_row("User Name",is_editable),
      pinfo_util.get_directory_row("user", user.directoryName(),is_editable),
      {name: "status", header: "Status", attr: "statusNode"},
      {name: "user_id", header: "User ID", attr: "user_id"},
      {name: "passwd_set", header: "Password Set", attr:"passwd_set"},
      pinfo_util.get_attr_row("user_real_name", "Real Name",is_editable),
      pinfo_util.get_attr_row("description", "Description",is_editable),
      pinfo_util.get_attr_row("phone", "Phone Number",is_editable),
      pinfo_util.get_attr_row("user_email", "Email",is_editable),
      pinfo_util.get_attr_row("location", "Location",is_editable), 
      {name: "groups", header: "Group Membership", noupdate: true, 
                    dialogEditor: true, editor: dmws.PrincipalModifyDialog,
                    editorProps: {  principal: user, type: "add_to_group", 
                                    title: "Add to User Group",
                                    group_ctor : dmws.UserGroup, 
                                    principal_type: "user",
                                    ctor : dmws.User },
                    get: function (item) {
                        return groupList.domNode;
                      }
      },  
      { name: "hosts", header: "On Host(s)",
        get: function (item) {
         return hostList.domNode;
      }, noupdate: true } 
      ] // end of model
     }); // end of ItemInspector 
     dojo.byId("user-info").appendChild(userInspector.domNode);
    
    user_update = coreui.getUpdateMgr().userFnCall({
        purpose: "Updating user information",
        fn: function () {
            user.update({
                onComplete: function () {
                    if(notFoundError != true) {
                        show_monitor_content();
                        userInspector.update();
                    }
                    notFoundError = false;
                },
                errorHandlers: { 
                  404: function (err, ioArgs) {
                          notFoundError = true;
                          show_invalid_error();
                          var fn = dmws.getPrincipalUtil().get_principal_not_found_fn(
                            "user",user.getValue("name"));  
                          fn.call(err,ioArgs); 
                       }
                }
            });
        },
        recur: true
    });
    
    netevent_log = new nox.netapps.user_event_log.networkevents.NetEventsTable(
                    dojo.byId("netevents-table"), 10,
                    "user=" + encodeURIComponent(user.getValue("name")));
}

dojo.addOnLoad(init_page);
