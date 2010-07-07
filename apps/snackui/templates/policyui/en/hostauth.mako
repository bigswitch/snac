## -*- coding: utf-8 -*-

<%inherit file="policy-layout.mako"/>
<%def name="page_title()">Host Authentication Rules</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/policyui/rules.css";
  @import "/static/nox/ext/apps/snackui/policyui/hostauthrules.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.Button");
  dojo.require("nox.ext.apps.snackui.policyui.EditablePolicyRuleList");
  dojo.require("nox.ext.apps.snackui.policyui.hostauthrules");
</%def>

## ---------------------------------------------------------------------------

<%def name="module_header()">
  <div class="buttonContainer">

##      <button dojoType="dijit.form.Button" id="filterBtn"
##              disabled="disabled">
##        Filter Rules
##        <script type="dojo/method" event="onClick">
##          alert("This function is not yet implemented.");
##        </script>
##      </button>
      <button dojoType="dijit.form.Button" id="deleteRuleBtn">
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
              "rule_type" : "hostauth"
          });
        </script>
      </button>
      <button dojoType="dijit.form.Button" id="addRuleBtn">
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
        Revert
        <script type="dojo/method" event="onClick">
          revert_changes();
        </script>
      </button>
      <span class="buttonDivider"></span>
      <!-- Unimplemented
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
        Apply Changes
        <script type="dojo/method" event="onClick">
          apply_changes();
        </script>
      </button>
  </div>
</%def>


## ---------------------------------------------------------------------------

<div dojoType="nox.ext.apps.snackui.policyui.EditablePolicyRuleList"
     jsId="rulelistWidget">
</div>
