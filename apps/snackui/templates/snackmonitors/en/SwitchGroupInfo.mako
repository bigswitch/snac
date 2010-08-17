## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">&nbsp;</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/webapps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/webapps/coreui/coreui/ItemList.css";
  @import "/static/nox/ext/apps/snackui/snackmonitors/SwitchGroupInfo.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Form");
  dojo.require("dijit.TitlePane");
  dojo.require("nox.ext.apps.snackui.snackmonitors.SwitchGroupInfo");
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
