## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">Debug Log &amp; System Restore</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/settingsui/log.css";
  @import "/static/nox/ext/apps/snackui/snackmonitors/Groups.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.Dialog");
  dojo.require("dijit.TitlePane");
  dojo.require("nox.ext.apps.snackui.settingsui.log");
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="settings_content" region="center">


<div dojoType="dijit.TitlePane" title="Debug Log">
<div id="prepare">
  <table> 
  <tr>
  <td> 
   <button dojoType="dijit.form.Button">
          Prepare Debug Log
          <script type="dojo/method" event="onClick">
          prepare();
          </script>
   </button> 
  </td>
  <td> 
   <p>

   To download a diagnostics archive file of the controller and switch
   internal log files, click &ldquo;Prepare Debug Log &rdquo; and follow the
   instructions.  </p> 
  <p> Please note, the file is meant for the vendor and
   useful only for low-level system diagnostics.

   </p>
  </td> 
  </tr> 
  </table> 
</div>

<div id="download">
     <p>
     
     Process complete!  Download the archive by clicking <a href="/ws.v1/nox/dump/dump.tar.gz">here</a>.
     
     </p>

</div>

<div id="dumping">
     <p>
     
     Preparing a file to be downloaded. Please wait a moment since this may take several minutes.
     
     </p>

</div>

<div id="error">
     <p>
     
     An error occurred and the downloadable file couldn't be prepared.
     
     </p>

</div>
</div>

<div dojoType="dijit.TitlePane" title="System Restore">
  <p> 
  System Restore allows you to restore all system state to a "snapshot" created
  in the past (dates are shown in the browser's timezone). </p>  
  <p> NOX automatically generates snapshots on regular intervals.  You 
  may also manually generate a snapshot using the "Create New Snapshot" button. 
  </p>
  <br> 
  <div class="buttonContainer">
      <div style="float: left;">
   <button dojoType="dijit.form.Button">
          Create New Snapshot
          <script type="dojo/method" event="onClick">
          snapshot();
          </script>
   </button>
      </div> 
      <div style="float: right; margin-right: 50px">
    <button dojoType="dijit.form.Button" style="float: left;">
              Clear to Factory Defaults
             <script type="dojo/method" event="onClick">
              restore_id = "delete";
              dijit.byId("restore_confirmation_dialog").show();
            </script>
         </button>
    </div>
</div>
 <br>
 <br>  
  <table id="snapshots-table" class="itemRows" width="50%">
    <tr class="headerRow">
      <th id="snapshot-date-column"> Snapshot Date </th>
      <th id="restore-column">  </th>
    </tr> 
    <tbody class="itemRows">
    </tbody> 
   </table>

</div> 



</div>

## popup to confirm the changes ----------------------------------------------

<div id="restore_confirmation_dialog" dojoType="dijit.Dialog"> 
<div align="left"> 
     <p> 
     Warning: System Restore will remove ALL configuration state you have entered <br> 
     since the snapshot.  System restore also restarts the Policy Controller,<br>
     which destroys all runtime network state and requires you to refresh <br>
     the page and reauthenticate.
     </p> 
     <br/> 
     <p> Are you sure you want to proceed?  </p>
     <br/> 
</div> 
     <div id="confirmation_buttons">

         <button dojoType="dijit.form.Button" id="confirm_yes">
             Yes
             <script type="dojo/method" event="onClick">
                 dijit.byId("restore_confirmation_dialog").hide();
                 restore();
             </script>
         </button>

         <button dojoType="dijit.form.Button" id="confirm_no">
              No
              <script type="dojo/method" event="onClick">
                  dijit.byId("restore_confirmation_dialog").hide();
              </script>
         </button>
     </div>
</div>
