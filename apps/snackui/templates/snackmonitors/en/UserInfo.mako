## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">&nbsp;</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/apps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/apps/coreui/coreui/ItemList.css";
  @import "/static/nox/apps/coreui/coreui/ItemListEditor.css";
  @import "/static/nox/ext/apps/snackui/snackmonitors/UserInfo.css";
  @import "/static/nox/apps/user_event_log/networkevents/NetEvents.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("dijit.TitlePane");
  //dojo.require("nox.ext.apps.snackui.snackmonitors.UserInfo");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_user = "${unicode(request.args.get('name', [''])[-1].replace(r'\\', r'\\\\'), 'utf-8')}";
</%def>

<%def name="head()">
  <script type="text/javascript" src="/static/nox/ext/apps/snackui/snackmonitors/UserInfo.js"></script>
</%def>

## ---------------------------------------------------------------------------

<%def name="monitor_header()">
  <div class="buttonContainer" id="change-password-button">
    <button dojoType="dijit.form.Button" id="change_cred_button" jsid="change_cred_button" disabled="true">
      Change Password
      <script type="dojo/method" event="onClick">
        show_change_cred();
      </script>
    </button>
  </div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <div style="display: none" id="invalid-name-error">
    <b> No record found for the specified user. </b> 
  </div>

  <div id="user-info"></div>

  <div dojoType="dijit.TitlePane" title="Related Network Events">
  <div dojoType="dijit.layout.ContentPane">

  <div dojoType="dijit.layout.ContentPane">
    <table id="netevents-header-table" class="log">
      <tr id="netevents-header-table">
        <th class="priority">Priority</th>
        <th class="timestamp">Timestamp</th>
        <th class="message">Message</th>
      </tr>
    </table>
  </div>

  <div dojoType="dijit.layout.ContentPane">
    <table id="netevents-table" class="log">
      <!-- Dummy row to make browser table layout/Javascript happy... -->
      <tr>
      <td class="priority"></td>
      <td class="timestamp"></td>
      <td class="message"></td>
      </tr>
    </table>
  </div>
  </div>
  </div>

</div>

<div id="change_cred_dialog" dojoType="dijit.Dialog"> 
  <script type="dojo/method" event="onCancel">
    cancel_cred();
  </script>
  <table> 
    <tr> <td> New Password: 
        <input dojoType="dijit.form.TextBox" id="new_cred" type="password"/>
    </td></tr> 
    <tr> <td> Confirm Password:
        <input dojoType="dijit.form.TextBox" id="confirm_cred" type="password"/>
    </td> </tr> 
    <tr><td> 
        <button dojoType="dijit.form.Button" id="submit_change">
          Change Password
          <script type="dojo/method" event="onClick">
            change_cred();
          </script>
        </button>
        <button dojoType="dijit.form.Button" id="clear_cred">
          Clear Password
          <script type="dojo/method" event="onClick">
            clear_cred();
          </script>
        </button>
        <button dojoType="dijit.form.Button" id="cancel_cred">
          Cancel
          <script type="dojo/method" event="onClick">
            cancel_cred();
          </script>
        </button>
    </td></tr>
  </table> 
</div>
