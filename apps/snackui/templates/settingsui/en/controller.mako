## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">Policy Controller Settings</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/webapps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/webapps/coreui/coreui/EditableGrid.css";
  @import "/static/nox/ext/apps/snackui/settingsui/controller.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("nox.ext.apps.snackui.settingsui.controller");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.form.Form");
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
    <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="reset_button">
      Shutdown Controller
      <script type="dojo/method" event="onClick">shutdown_system();</script>
    </button>
    <!-- <span class="buttonDivider"></span>
    <button dojoType="dijit.form.Button" jsid="reset_button">
      Shutdown Controller Processes
      <script type="dojo/method" event="onClick">shutdown_process();</script>
    </button> -->
    <p>Please note: No changes are sent to the server until 
        &ldquo;Commit Changes&rdquo; is clicked.</p>
  </div>
</%def>

## ---------------------------------------------------------------------------

<!-- <div dojoType="dijit.layout.BorderContainer" design="headline" region="center" id="settings_content" /> -->
<div dojoType="dijit.layout.ContentPane" id="settings_content" region="center">

     <div dojoType="dijit.TitlePane" title="Platform Settings">
        <div id="platform_settings"></div>
     </div>

     <div dojoType="dijit.TitlePane" title="Web Interface Settings">
        <div id="general_settings"></div>
     </div>

     <div dojoType="dijit.TitlePane" title="Network Interfaces">
        <div id="network_interfaces_table"></div>
     </div>
</div>

## popup to confirm the changes ----------------------------------------------

<div id="confirmation_dialog" dojoType="dijit.Dialog"> 
<div align="left"> 
     <p> 
     Warning: Committing incorrect settings may render the Policy <br>
     Manager web interface unreachable.  Changing web settings may <br>
     require you to refresh the page and reauthenticate. 
     </p> 

     <p> Are you sure you want to proceed?  </p>

     <br/>
</div> 
     <div id="confirmation_buttons">

         <button dojoType="dijit.form.Button" id="confirm_yes">
             Yes
             <script type="dojo/method" event="onClick">
                 dijit.byId("confirmation_dialog").hide();
                 commit();
             </script>
         </button>

         <button dojoType="dijit.form.Button" id="confirm_no">
              No
              <script type="dojo/method" event="onClick">
                  dijit.byId("confirmation_dialog").hide();
              </script>
         </button>
     </div>
</div>

<div id="certificate_warning_dialog" dojoType="dijit.Dialog"> 

     <p> 

     SSL/TLS Certificate and Private Key files must both be provided
     before committing your changes.

     </p>

     <br/>

     <div id="done_button">
         <button dojoType="dijit.form.Button" id="confirm_ok">
             Ok
             <script type="dojo/method" event="onClick">
                 dijit.byId("certificate_warning_dialog").hide();
             </script>
         </button>
     </div>
</div>

## controller shutdown confirmation dialog

<div id="shutdown_system_confirmation_dialog" dojoType="dijit.Dialog"
     title="Confirmation"> 
  <table> 
    <tr> <td> Are you sure you want to shutdown the controller? </td></tr> 
    <tr><td> 
        <button dojoType="dijit.form.Button">
          OK
          <script type="dojo/method" event="onClick">
            shutdown("system");
          </script>
        </button>
        <button dojoType="dijit.form.Button">
          Cancel
          <script type="dojo/method" event="onClick">
             dijit.byId("shutdown_system_confirmation_dialog").hide();
          </script>
        </button>
    </td></tr>
  </table> 
</div>

## process shutdown confirmation dialog

<div id="shutdown_process_confirmation_dialog" dojoType="dijit.Dialog"
     title="Confirmation"> 
  <table> 
    <tr> <td> Are you sure you want to shutdown the controller process? </td></tr> 
    <tr><td> 
        <button dojoType="dijit.form.Button">
          OK
          <script type="dojo/method" event="onClick">
            shutdown("process");
          </script>
        </button>
        <button dojoType="dijit.form.Button">
          Cancel
          <script type="dojo/method" event="onClick">
             dijit.byId("shutdown_process_confirmation_dialog").hide();
          </script>
        </button>
    </td></tr>
  </table> 
</div>