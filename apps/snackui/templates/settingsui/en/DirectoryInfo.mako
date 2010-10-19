## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">Directory Settings</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/ext/apps/snackui/settingsui/DirectoryInfo.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Button");
  dojo.require("dijit.form.CheckBox");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.FilteringSelect");
  dojo.require("dijit.Dialog"); 
  dojo.require("nox.ext.apps.snackui.settingsui.DirectoryInfo"); 
</%def>

<%def name="module_header()">
  ${parent.module_header()}
  <div class="buttonContainer">
    <button dojoType="dijit.form.Button" jsid="commit_button">
      Make Changes
      <script type="dojo/method" event="onClick">commit();</script>
    </button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="rollback_button">
      Reset Values
      <script type="dojo/method" event="onClick">rollback();</script>
    </button>
    <p>Please note: No changes are sent to the server until 
        &ldquo;Make Changes&rdquo; is clicked.</p>
  </div>
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_directory = "${request.args.get('name', [''])[-1].replace(r'\\', r'\\\\')}";
</%def>

## ---------------------------------------------------------------------------

<div id="settings_content" region="center">
    <div style="display: none" id="invalid-name-error">
      <b> No record found for the specified directory. </b>  
    </div>
     
    <div id="directory-info"></div>
</div>

<div id="ldap_version" style="display: none"
    <input dojoType="dijit.form.RadioButton" id="ldap_version_2_radiobutton" 
           name="ldap_version" type="radio" value="2" />
    <label for="ldap_version_2">2</label>
    <input dojoType="dijit.form.RadioButton" id="ldap_version_3_radiobutton" 
           name="ldap_version" type="radio" value="3" checked="checked" />
    <label for="ldap_version_3">3</label>
</div>

<div id="use_ssl" style="display: none"
    <input dojoType="dijit.form.CheckBox" id="use_ssl_checkbox" 
           name="use_ssl" type="checkbox" value="1" />
</div>

<div id="search_subtree" style="display: none"
    <input dojoType="dijit.form.CheckBox" id="search_subtree_checkbox" 
           name="search_subtree" type="checkbox" value="1" />
</div>

<div id="follow_referrals" style="display: none"
    <input dojoType="dijit.form.CheckBox" id="follow_referrals_checkbox" 
           name="follow_referrals" type="checkbox" value="1" />
</div>

<div id="group_posix_mode" style="display: none"
    <input dojoType="dijit.form.CheckBox" id="group_posix_mode_checkbox" 
           name="group_posix_mode" type="checkbox" value="1" />
</div>

