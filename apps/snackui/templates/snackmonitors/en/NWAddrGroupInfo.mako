## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">&nbsp;</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/apps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/apps/coreui/coreui/ItemList.css";
  @import "/static/nox/ext/apps/snackui/snackmonitors/NWAddrGroupInfo.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("dijit.TitlePane");
  dojo.require("nox.ext.apps.snackui.snackmonitors.NWAddrGroupInfo");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var selected_group = "${unicode(request.args.get('name', [''])[-1].replace(r'\\', r'\\\\'), 'utf-8')}";
</%def>

## ---------------------------------------------------------------------------

<%def name="monitor_header()">
  ${parent.monitor_header()}
</%def>

## ---------------------------------------------------------------------------

  <div dojoType="dijit.layout.ContentPane" region="top">
    <div style="display: none" id="invalid-name-error">
      <b> No record found for the specified group. </b>  
    </div>

    <div dojoType="dijit.layout.ContentPane" region="top" id="monitor_content">
        <div id="group-inspector"></div>

        <div dojoType="dijit.TitlePane" title="Direct Members">
          <div dojoType="dijit.layout.ContentPane" region="top" id="member_content">
             <div id="buttonContainer">
               <button dojoType="dijit.form.Button" id="add_direct_member_link">
                 Add Member
               </button>
               <span class="buttonDivider"></span>
               <button dojoType="dijit.form.Button" id="delete_direct_member_link">
                 Remove Selected
               </button>
             </div>
          </div>
        </div>
    </div>
  </div>

  <div dojoType="dijit.Dialog" jsId="add_address_dialog" title="Add Network Addresses to Group"> 
        <table> 
        <tr>          <td> IPv4 Address(es): </td> 
            <td> 
            <input type="text" dojoType="dijit.form.ValidationTextBox" 
                    jsId="address_to_add"
            regExp="(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(/[0-9]|/[1-2][0-9]|/3[0-2])?"
            value="" require="true" trim="true"
            promptMessage="Enter IPv4 address or prefix (e.g., '10.0.0.1' or '10.0.0.0/16')"
            invalidMessage="Not a valid IPv4 address or prefix"> 
        </td></tr> 
        </table> 
    <button dojoType="dijit.form.Button" jsId="addBtn">Add
<script type="dojo/method" event="onClick">
  try_to_add_address(); 
</script>
    </button>
    <button dojoType="dijit.form.Button" jsId="cancelBtn">Cancel

<script type="dojo/method" event="onClick">
  address_to_add.setValue("");  
  add_address_dialog.hide();
</script>

</button>
      </div>  
