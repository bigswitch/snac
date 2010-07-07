## -*- coding: utf-8 -*-

<%inherit file="policy-layout.mako"/>
<%def name="page_title()">
% if request.args.get('view', [''])[-1] == "auth" :
System Policy Rules
% else:  
Site Policy Rules
% endif 

</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/policyui/rules.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Button");
  dojo.require("nox.ext.apps.snackui.policyui.EditablePolicyRuleList");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  var from_url = "${request.args.get('view', [''])[-1]}";
  var list_type = (from_url == "comm" || from_url == "auth") ? from_url : "all"; 
  var new_rule_type = (list_type == "all") ? "comm" : list_type; 
  dojo.require("nox.ext.apps.snackui.policyui.rules");
</%def>

<%def name="module_header()">
  <div class="buttonContainer">

##      <button dojoType="dijit.form.Button" id="filterBtn"
##              disabled="disabled">
##        Filter Rules
##        <script type="dojo/method" event="onClick">
##          alert("This function is not yet implemented.");
##        </script>
##      </button>
      <div style="float: left;">
      <button dojoType="dijit.form.Button" >
        Add
        <script type="dojo/method" event="onClick">
          rulelistWidget.addRule({
              "description" : "New Rule",
              "actions" : [ { "args" : [], "type": "allow" } ],
              "condition" : { "pred": true, "args" : [] },
              "policy_id" : null,
              "rule_id" : null,
              "user" : null,
              "timestamp" : null,
              "text" : "",
              "priority" : 1,
              "comment" : "",
              "exception" : false,
              "expiration" : 0.0,
              "rule_type" : new_rule_type
          });
        </script>
      </button>
      <button dojoType="dijit.form.Button">
        Delete
        <script type="dojo/method" event="onClick">
          rulelistWidget.deleteSelected();
        </script>
      </button>
      <span class="buttonDivider"></span>
      <!-- Unimplemented
      <button dojoType="dijit.form.Button" id="undoLastBtn"
              disabled="disabled">
        Undo Last
        <script type="dojo/method" event="onClick"
          alert("This function is not yet implemented.");
        </script>
      </button>
      -->
      <button dojoType="dijit.form.Button" id="revertBtn"
              disabled="disabled" jsId="revertBtn">
        Revert Policy
        <script type="dojo/method" event="onClick">
          revert_changes();
        </script>
      </button>

      <!-- Unimplemented
      <span class="buttonDivider"></span>
      <button dojoType="dijit.form.Button" id="analyzeBtn"
              disabled="disabled", jsId="analyzeBtn">
        Analyze Changes
        <script type="dojo/method" event="onClick">
          console_log("FIXME: Analyzing changes");
        </script>
      </button>
      -->
      <button dojoType="dijit.form.Button" id="applyBtn"
              disabled="disabled" jsId="applyBtn">
        Commit Changes
        <script type="dojo/method" event="onClick">
          apply_changes();
        </script>
      </button>
      </div>

      <div style="float: right; text-align: right;">
      <button dojoType="dijit.form.Button" id="resetBtn"
              jsId="resetBtn">
        Reset Counters
        <script type="dojo/method" event="onClick">
          reset_counters();
        </script>
      </button>
      </div>
  </div>
</%def>


## ---------------------------------------------------------------------------

<div dojoType="nox.ext.apps.snackui.policyui.EditablePolicyRuleList"
     jsId="rulelistWidget" ></div>
