## -*- coding: utf-8 -*-

## TBD: It would be nice to support the following:
## TBD:    - Fix tab order for request body.  Dojo weirdness...
## TBD:    - Turn request method & path into a FilteringSelect with a
## TBD:      data store behind it that stores previously specified
## TBD:      requests (including content-type and message body) so you
## TBD:      don't have to type them in over and over again.
## TBD:    - Store the contents of the request path data store in
## TBD:      a cookie so a page reload (forced by a need to reauth or
## TBD:      whatever) does not lose all the requests you want to make
## TBD:      easily.
## TBD:    - Add styling rules for twisted tracebacks to make it look
## TBD:      nicer when something goes really wrong.
## TBD:    - Fix dojo rendering for Method & URI TextBox/FilteringSelect

<%inherit file="layout.mako"/>
<%def name="page_title()">Web Service Test Client</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.layout.SplitContainer");
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.FilteringSelect");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.Textarea");
  dojo.require("dijit.form.SimpleTextarea");
  dojo.require("dijit.form.Button");
</%def>

<%def name="head_css()">
  ${parent.head_css()}

  div#layout_helper {
    margin-right: 3em;
  }

  div#page_content {
    overflow: auto; /* Override the default set elsewhere... */
  }

  table {
    border-collapse: separate;
    table-layout: fixed;
    width: 100%;
  }
  table#info_table  tr {
    vertical-align: top;
  }
  table#info_table td {
    vertical-align: top;
    text-align: left;
    margin: 0;
    padding: 0;
    border: 0;
  }
  table#info_table td.label {
    text-align: right;
    width: 10%;
  }
  input#request_method_and_path {
    width: 100%;
  }
</%def>

<%def name="head()">
  ${parent.head()}
  <script type="text/javascript" src="/static/nox/ext/apps/webservice_testui/webservice_testui/webservice_testui.js"></script>
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  dojo.addOnLoad(function() {
      attach_keypress_handler();
      var path_widget = dijit.byId("request_method_and_path");
      path_widget.focus();
  })
</%def>

## ---------------------------------------------------------------------------


<div dojoType="dijit.layout.ContentPane" region="center" id="page_content">

<div id="layout_helper">

  <table id="info_table">
    <tr><td class="label"><td></td></tr>
    <tr><td colspan="2"><h1>Request</h1></td></tr>
    <tr>
      <td class="label">Method & URI:</td>
      <td class="request_method_and_path">
        <input dojoType="dijit.form.TextBox"  id="request_method_and_path"
               type="text" name="uri" value="" tabIndex="2"/>
      </td>
    </tr><tr>
      <td class="label">Content Type:</td>
      <td>
        <select dojoType="dijit.form.ComboBox" id="request_content_type"
                tabIndex="3">
          <option value="application/json">application/json</option>
        </select>
      </td>
    </tr><tr>
      <td class="label">Body:</td>
      <td>
        <textarea dojoType="dijit.form.SimpleTextarea" id="request_body"
                  tabIndex="4" rows="10"></textarea>

      </td>
    </tr><tr>
      <td colspan="2">
        <button dojoType="dijit.form.Button" id="submit_request"
                tabIndex="5">
          Submit
          <script type="dojo/method" event="onClick">
            submit_request();
          </script>
        </button>
        <button dojoType="dijit.form.Button" id="clear_request_body"
                tabIndex="6">
          Clear Content
          <script type="dojo/method" event="onClick">
            var content = dijit.byId("request_body");
            content.setValue("");
          </script>
        </button>
      </td>
    </tr>
    <tr><td colspan="2"><hr/></td></tr>
    <tr><td colspan="2"><h1>Response</h1></td></tr>
    <tr>
      <td class="label">Status:</td>
      <td><span id="statusMsgArea">No request sent yet.</span></td>
    </tr>
    <tr>
      <td class="label">Headers:</td>
      <td>
        <textarea dojoType="dijit.form.Textarea" id="response_headers"
                  readOnly="true"></textarea>
      </td>
    </tr><tr>
      <td class="label">Body:</td>
      <td>
        <div dojoType="dijit.layout.ContentPane" id="response_body">
        </div>
      </td>
    </tr>
  </table>

</div>

</div>
