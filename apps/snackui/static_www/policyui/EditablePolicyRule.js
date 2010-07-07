dojo.provide("nox.ext.apps.snackui.policyui.EditablePolicyRule");

dojo.require("nox.ext.apps.snackui.policyui.PolicyRule");
dojo.require("nox.ext.apps.snackui.policyui.PolicyRuleEditor");

dojo.declare("nox.ext.apps.snackui.policyui.EditablePolicyRule", [ nox.ext.apps.snackui.policyui.PolicyRule ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.policyui", "templates/EditablePolicyRule.html"),
    rule: null,
    ruleEditor: nox.ext.apps.snackui.policyui.PolicyRuleEditor,

    _edit_cancelled: function(rule) {
        this.collapse();
    },

    _update_rule_display: function () {
        if (this.rule.description != null && this.rule.description != "") {
            this.rtitle.innerHTML = this.rule.description;
        // TBD: - Re-enable generated rule description when can do it for
        // TBD:   new rules added client-side.
        //} else if (this.rule.actions != null) {
        //    this.rtitle.innerHTML = this.generated_description();
        } else if (this.rule.text != null && this.rule.text != "") {
            this.rtitle.innerHTML = this.rule.text;
        } else {
            this.rtitle.innerHTML = "INVALID RULE";
        }
        this.hit_count.id = "hit-count-" + this.rule.rule_id; 
        if (this.rule.exception)
            dojo.addClass(this.domNode, "exception");
        else
            dojo.removeClass(this.domNode, "exception");
        if (this.rule["protected"]) {
            dojo.addClass(this.domNode, "protected");
            dojo.query(".rule", this.domNode).removeClass("dojoDndHandle");
        } else {
            dojo.removeClass(this.domNode, "protected");
            dojo.query(".rule", this.domNode).addClass("dojoDndHandle");
        }
    },

    _edit_done: function (rule, modified) {
        if (modified) {
            var c = this.onChange(this, this.rule, rule);
            if (c != null && c != false) {
                this.collapse();
                return;
            }
            this.modified = true;
            this.rule = rule;
            // Remove the rule_id so policyws will see this as an updated rule.
            delete this.rule["rule_id"];
            this._update_rule_display();
            this.collapse();
        } else {
            this.modified = false;
            this.collapse();
        }
    },

    _widgets2rule: function () {
    },

    _rule2widgets: function () {
        var a = this.rule.actions;
        if (a.type == "deny" || a.type == "allow") {
            this.action0.setValue(a.type);
        } else {
            console_log("Action '", a.type, "' is not a simple action, bailing out...");
            // TBD: show non-editable rule information....
            return;
        }

        var negate = false;
        var p = this.rule.condition;
        if (p.pred == "not") {
            p = p.args[0];
            negate = true;
        }

        if (p.pred != "and") {
            this._simple_condition2widgets(p, negate);
        } else  {
            if (negate == false) {
                this._complex_condition2widgets(p);
            } else {
                console_log("Negated complex conditions are not handled, bailing out...");
            }
        }
    },

    collapse: function () {
        var c = this.onCollapse(this);
        if (c != null && c != false)
            return;

        this.expanded = false;
        dojo.removeClass(this.domNode, "expanded");
        dojo.style(this.editor, "display", "none");
        var w = dijit.byNode(this.editor.firstChild);
        this.editor.innerHTML = "";
        if (w != null)
            w.destroy();
    },

    expand: function () {
        if (this.expanded == true)
            return;
        this.expanded = true;
        dojo.addClass(this.domNode, "expanded");

        var c = this.onExpand(this);

        // Hack: if new rule has no text and description NEW RULE, assume
        // is a new rule and remove the "NEW RULE" description.
        if (this.rule.text == "" && this.rule.description == "New Rule")
            this.rule.description = "";

        if (c != null && c != false)
            return;

        var w = new nox.ext.apps.snackui.policyui.PolicyRuleEditor({rule: this.rule});
        w.startup();
        dojo.connect(w, "onDone", this, "_edit_done");
        dojo.connect(w, "onCancel", this, "_edit_cancelled");
        this.editor.appendChild(w.domNode);
        dojo.style(this.editor, "display", "block");
    },

    postCreate: function () {
        //this._rule2widgets();
        this.flow_link.href = "/Monitors/FlowHistory?policy_id=" +
                this.rule.policy_id + "&rule_id=" + this.rule.rule_id; 
    },

    startup: function () {
        this.inherited("startup", arguments);
        this._update_rule_display();
        this.expanded = false;
        this.modified = false;
        dojo.style(this.editor, "display", "none");
        dojo.connect(this.rulecontents, "ondblclick", this, "expand");
    },

    onChange: function (rule_widget, old_rule, new_rule) {
        // Called when someone changes the rule.  Return null or false
        // or no value at all to allow the change, else the change is
        // disallowed and the rule stays as it was before.
    },

    onExpand: function (rule_widget) {
        // Called when someone attempts to expand a rule.  Passes the
        // current rule information.  Return null or false or no value
        // at all to allow expansion to continue, else it is blocked.
    },

    onCollapse: function (rule_widget) {
        // Called when someone attempts to collapse a rule.  Passes the
        // current rule information.  Return null or false or no value
        // at all to allow collapse to continue, else it is blocked.
    }
});
