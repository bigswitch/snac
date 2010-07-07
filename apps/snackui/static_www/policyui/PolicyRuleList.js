dojo.provide("nox.ext.apps.snackui.policyui.PolicyRuleList");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("nox.ext.apps.snackui.policyui.PolicyRule");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyRuleList", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.policyui", "templates/PolicyRuleList.html"),
    widgetsInTemplate: false,
    policy: [],
    ruleWidgetType: nox.ext.apps.snackui.policyui.PolicyRule,
    policyid: 0,  // FIXME: currently, the policy_id returned for each rule
                  // is wrong if the policy ever changes.  Here we override
                  // that value until it is fixed in the guts of nox

    _rule_widgets: function () {
        var selector = "#" + this.rulelist.id + " > div";
        return dojo.query(selector).map("dijit.byNode(item)");
    },

    _remove_rule_list: function () {
        var widgets = this._rule_widgets();
        this.rulelist.innerHTML = "";
        widgets.forEach("item.destroy()");
    },

    _render_rule_list: function () {
        dojo.forEach(this.policy, dojo.hitch(this, function (r) {
            var w = new this.ruleWidgetType({rule: r});
            w.startup()
            this.rulelist.appendChild(w.domNode);
        }));
    },

    getPolicy: function () {
        return this.policy;
    },

    setPolicy: function (policy) {
        this.policy = policy;
        this._remove_rule_list();
        this._render_rule_list();
    },

    startup: function () {
        this.inherited("startup", arguments);
        this._render_rule_list();
    }
});
