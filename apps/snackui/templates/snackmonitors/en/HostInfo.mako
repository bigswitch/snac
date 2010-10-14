## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">&nbsp;</%def>

<%
  from nox.ext.apps.coreui.template_utils import utf8quote
  mangled_name = request.args.get('name', [''])[-1].replace(r'\\', r'\\\\')
%> 

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/webapps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/webapps/coreui/coreui/ItemList.css";
  @import "/static/nox/ext/apps/snackui/snackmonitors/HostInfo.css";
  @import "/static/nox/netapps/user_event_log/networkevents/NetEvents.css";
  @import "/static/nox/webapps/coreui/coreui/EditableGrid.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  //dojo.require("nox.ext.apps.snackui.snackmonitors.HostInfo");
  dojo.require("dijit.TitlePane");
</%def>

<%def name="head()">
    <script type="text/javascript" src="/static/nox/ext/apps/snackui/snackmonitors/HostInfo.js"></script>
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_host = "${unicode(request.args.get('name', [''])[-1].replace(r'\\', r'\\\\'), 'utf-8')}";
</%def>

## ---------------------------------------------------------------------------

<%def name="monitor_header()">
  ${parent.monitor_header()}
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

    <div style="display: none" id="invalid-name-error">
      <b> No record found for the specified host. </b>  
  	</div>

    <div id="host-info"></div>

  <div dojoType="dijit.TitlePane" title="Static Bindings">
   <div class="buttonContainer">
           <button dojoType="dijit.form.Button" jsid="add_binding_btn2">
             Add MAC Binding
             <script type="dojo/method" event="onClick">
                mac_add_binding_dialog.show();
              </script>
          </button>
          <span class="buttonDivider"></span>
           <button dojoType="dijit.form.Button" jsid="add_binding_btn1">
             Add IP Binding
             <script type="dojo/method" event="onClick">
                ip_add_binding_dialog.show();
            </script>
          </button>
          <span class="buttonDivider"></span>
          <button dojoType="dijit.form.Button" jsid="delete_selected_binding" disabled="true">
             Delete Selected Binding
             <script type="dojo/method" event="onClick">delete_binding();</script>
          </button>
        </div>
   <div id="static-bindings-table"></div>
  </div>

  <div dojoType="dijit.TitlePane" title="Active Bindings">
    <div id="active-bindings-table"></div>
  </div>
  
<div dojoType="dijit.TitlePane" title="Recent Policy Matches">
  <div dojoType="dijit.layout.ContentPane">

<!-- store url in hidden field to avoid double query on page load --> 
<input type="hidden" id="first_load" value="true">  
<iframe id="listframe" width="100%"
src="/Monitors/HostFlowSummary?hostname=${utf8quote(mangled_name)}">  
 Error: could not load flow history.  
</iframe> 

</div>
</div> 

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

<div jsId="ip_add_binding_dialog" dojoType="dijit.Dialog" title="Add Static IP Binding"> 

<table> 
    <tr><td> IP Address: </td> 
        <td><input dojoType="dijit.form.ValidationTextBox" jsId="ip_binding"
              promptMessage="Enter address in dotted decimal form."
              invalidMessage="Address is not in dotted decimal form."
              regExp="(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])" 
              /> 
        </td> </tr> 
</table>   
<button dojoType="dijit.form.Button">Create
<script type="dojo/method" event="onClick">insert_binding("ip"); </script>
</button>
<button dojoType="dijit.form.Button">Cancel
<script type="dojo/method" event="onClick">
    reset_binding_dialogs();
    ip_add_binding_dialog.hide();
</script>
</button>
</div>

<div jsId="mac_add_binding_dialog" dojoType="dijit.Dialog" title="Add Static MAC Binding"> 

<table> 
    <tr><td> MAC Address: </td> 
        <td><input dojoType="dijit.form.ValidationTextBox" jsId="mac_binding"
              promptMessage="Enter address as colon-separated hex digits"
              invalidMessage="Address does not contain colon separated hex digits"
              regExp="([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"/>
        
        </td> </tr> 
    <tr><td> Type: </td> 
        <td> <select jsId="mac_iface_type" dojoType="dijit.form.ComboBox">
              <option>End-Host</option>
              <option >Router</option>
              </select>    
        </td></tr> 
</table>   
<button dojoType="dijit.form.Button">Create
<script type="dojo/method" event="onClick">insert_binding("mac"); </script>
</button>
<button dojoType="dijit.form.Button">Cancel
<script type="dojo/method" event="onClick">
  reset_binding_dialogs();
  mac_add_binding_dialog.hide();
</script>
</button>
</div>
