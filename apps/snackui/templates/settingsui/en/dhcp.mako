## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">DHCP Server Settings</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/ext/apps/snackui/settingsui/dhcp.css";
  @import "/static/nox/ext/apps/coreui/coreui/EditableGrid.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.snackui.settingsui.dhcp");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.Dialog"); 
  dojo.require("dijit.TitlePane");
</%def>

<%def name="module_header()">
  ${parent.module_header()}
  <div class="buttonContainer">
    <button dojoType="dijit.form.Button" jsid="commit_button">
      Commit Changes
      <script type="dojo/method" event="onClick">validate();</script>
    </button>
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="rollback_button">
      Reset Values
      <script type="dojo/method" event="onClick">rollback();</script>
    </button>
    <p>Please note: No changes are sent to the server until 
        &ldquo;Commit Changes&rdquo; is clicked.</p>
  </div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="settings_content" region="center">

     <div dojoType="dijit.TitlePane" title="General Options">
        <div id="general_settings"></div>
     </div>

     <div dojoType="dijit.TitlePane" title="Subnets">
        <div class="buttonContainer">
           <button dojoType="dijit.form.Button">
             Add New Subnet
             <script type="dojo/method" event="onClick">add_subnet();</script>
          </button>
          <span class="buttonDivider"></span>
          <button dojoType="dijit.form.Button" jsid="delete_selected_subnet" disabled="true">
             Delete Selected
             <script type="dojo/method" event="onClick">delete_subnet();</script>
          </button>
        </div>
        <div id="subnets_table"></div>
     </div>

     <div dojoType="dijit.TitlePane" title="Fixed Addresses">
        <div class="buttonContainer">
           <button dojoType="dijit.form.Button">
             Add New Fixed Address
             <script type="dojo/method" event="onClick">add_fixed_address();</script>
          </button>
          <span class="buttonDivider"></span>
          <button dojoType="dijit.form.Button" jsid="delete_selected_fixed_address" disabled="true">
             Delete Selected
             <script type="dojo/method" event="onClick">delete_fixed_address();</script>
          </button>
        </div>
        <div id="fixed_addresses_table"></div>
     </div>

</div>
