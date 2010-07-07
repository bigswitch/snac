## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">Directories Settings</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/settingsui/directories.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.snackui.settingsui.directories");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.Dialog"); 
</%def>

<%def name="module_header()">
  ${parent.module_header()}
  <div class="buttonContainer">
    <button dojoType="dijit.form.Button">
      Add New Directory
      <script type="dojo/method" event="onClick">
    	show_add(); 
      </script>
    </button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="configure_selected" id="configure_selected" disabled="true">
    	Configure Selected
    	<script type="dojo/connect" event="onClick">
    		var selected = dirGrid.selection.getSelected();
                var name = selected[0].getValue('name');
                window.location.pathname = '/Settings/Directories/DirectoryInfo?name=' + encodeURIComponent(name);
    	</script>
    </button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="delete_selected" id="delete_selected" disabled="true">
    	Delete Selected
    	<script type="dojo/connect" event="onClick">
    		var selected = dirGrid.selection.getSelected();

                for (var i in selected) {
                    var name = selected[i].getValue('name');
                    if (name == 'Built-in') {   
                        coreui.UpdateErrorHandler.showError("Can't delete 'Built-in' directory.",
                        { header_msg: "Can't Delete:",
                          hide_retry: true, 
                          validation_error: true
                        });
                        return;
                    }
                }

                for (var i in selected) {
                    var name = selected[i].getValue('name');
                    remove(name);
                }
                dirGrid.selection.deselectAll();
    	</script>
    </button>
  </div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="settings_content" region="center">

## popup to add a new directory -----------------------------------
 
  <div id="new_dir_dialog" dojoType="dijit.Dialog" title="Add A New Directory"> 
        <table> 
        <tr> <td> Directory Name:
        <input dojoType="dijit.form.TextBox" id="new_dir_name" type="text"/>
        </td> </tr> 
        <tr> <td> Directory Type: 
        <select id="new_dir_type">
        </select>
        </td></tr> 
        <tr><td> 
        <button dojoType="dijit.form.Button" id="submit_add">
          Add Directory
          <script type="dojo/method" event="onClick">
            add_directory();
          </script>
        </button>
        </td></tr>
        </table> 
  </div>
  
## Popup if no directories exist to add a new directory 
  <div id="no_dir_dialog" dojoType="dijit.Dialog"> 
      No currently running directory types support adding new directories. 
  </div>

## pop-up to configure a dialog -----------------------------------
  
<!-- <div id="configure_dialog"  dojoType="dijit.Dialog"> 
  <h2 id="configure_name"> </h2> 
  <h3><b> Principals Enabled: </b></h3> 
  <form id="enabled_principals" >  
  <table id="principals_settings" > 
  <tr></tr> 
  </table>
  </form> 

  <h3> <b> Authentication Types Enabled:</b> </h3>
  <form id="enabled_authtypes" >  
  <table id="auth_type_settings"> 
  <tr></tr> 
  </table> 
  </form> 

## below we place separate div's that correspond to type-specific
## configuration.  Whenever this pop-up dialog is shown, only one
## such div will be visible at any time.

  <form id="LDAP_config" style="display: none" > 
  <h3> <b> LDAP Server Config </b></h3> 
  <table> 
  <tr><td class="required">Server URI:</td><td> <input name="ldap_uri" type="text" size="40"> </td></tr>
  <tr><td class="required">Ldap Version: </td><td><input name="ldap_version" type="text" size="2"> </td></tr> 
  <tr><td>Use SSL: </td><td> <input type="checkbox" name="use_ssl"> </td></tr> 
  <tr><td>Search Subtree: </td><td> <input type="checkbox" name="search_subtree"> </td></tr> 
  <tr><td>Follow Referrals: </td><td> <input type="checkbox" name="follow_referrals"> </td></tr> 
  <tr><td class="required">User Base DN: </td><td><input name="base_dn" type="text" size="40"> </td></tr> 
  <tr><td>Browser User DN: </td><td><input name="browser_user_bind_dn" type="text" size="40"> </td></tr> 
  <tr><td>Browser User Password: </td><td><input name="browser_user_bind_pw" type="text" size="18"> </td></tr> 
  <tr><td>User Search Filter: </td><td><input name="search_filter" type="text" size="40"> </td></tr> 
  <tr><td class="required">Username Field: </td><td><input name="username_field" type="text" size="18"> </td></tr> 
  <tr><td>Real Name Field: </td><td><input name="name_field" type="text" size="18"> </td></tr> 
  <tr><td>UID Field: </td><td><input name="uid_field" type="text" size="18"> </td></tr> 
  <tr><td>Phone Field: </td><td><input name="phone_field" type="text" size="18"> </td></tr> 
  <tr><td>Email Field: </td><td><input name="email_field" type="text" size="18"> </td></tr> 
  <tr><td>Location Field: </td><td><input name="loc_field" type="text" size="18"> </td></tr> 
  <tr><td>Description Field: </td><td><input name="desc_field" type="text" size="18"> </td></tr> 
  <tr><td>User Group Attribute: </td><td><input name="user_obj_groups_attr" type="text" size="18"> </td></tr> 
  <tr><td colspan="2"><hr></td></tr>

  <tr><td>Group Search Filter: </td><td><input name="group_filter" type="text" size="40"> </td></tr> 
  <tr><td>Group Base DN: </td><td><input name="group_base_dn" type="text" size="40"> </td></tr> 
  <tr><td>Group Name Field: </td><td><input name="groupname_field" type="text" size="18"> </td></tr> 
  <tr><td>Group Description Field: </td><td><input name="ugroup_desc_field" type="text" size="18"> </td></tr> 
  <tr><td>Group Member Field: </td><td><input name="ugroup_member_field" type="text" size="18"> </td></tr> 
  <tr><td>Group Subgroup Field: </td><td><input name="ugroup_subgroup_field" type="text" size="18"> </td></tr> 
  <tr><td>Group Posix Mode: </td><td> <input type="checkbox" name="group_posix_mode"> </td></tr> 
  </table> 
  </form> 

  <br/>
  <button dojoType="dijit.form.Button" id="submit_modify">
          Finish
          <script type="dojo/method" event="onClick">
            submit_modify();
          </script>
  </button>
</div>-->

  <div id="directories_container"></div>
</div>
