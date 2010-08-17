dojo.provide("nox.ext.apps.snackui.policyui.EditablePolicyRuleList");

dojo.require("dojo.dnd.Source");
dojo.require("nox.ext.apps.snackui.policyui.PolicyRuleList");
dojo.require("nox.ext.apps.snackui.policyui.EditablePolicyRule");

dojo.declare("nox.ext.apps.snackui.policyui.EditablePolicyRuleList", [ nox.ext.apps.snackui.policyui.PolicyRuleList ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.policyui", "templates/PolicyRuleList.html"),
    widgetsInTemplate: false,
    policy: [],
    ruleWidgetType: nox.ext.apps.snackui.policyui.EditablePolicyRule,
    list_type: "all", //list_type determines what type 
                      // of rules are shown in this instantiation of the list 
                      // This can be changed by calling setListType

    _remove_rule_list: function () {
        this.dnd_source.selectAll();
        this.dnd_source.deleteSelectedNodes();
    },

    _render_rule_list: function () {
        // remove the following loop once policy webservice
        // is fixed to return rules with the correct policy_id
        dojo.forEach(this.policy, function(r) { 
            r.policy_id = this.policyid; 
        }, this); 


        if(this.list_type == "all") { 
          this.dnd_source.insertNodes(false, this.policy);
          return; 
        }
        //FIXME: for now we are just going to split things into 
        // to pages, based on whether they 'auth' rules or 'comm' rules
        // This will put all rules pertaining to host and user auth into one page
        // and all communcation rules that pertain to authenticated
        // hosts and users on another.  
        
        this.hidden_nat_rules = [];
        this.hidden_rules = []; // holds the 'comm' or 'auth' rules,
                                // depending on the list_type
        var filtered_list = dojo.filter(this.policy, 
            function(item) { 
              // NAT rules should not be shown on either page. We save 
              // them here and put them on the front of the policy 
              // before we submit. 
              if(item.rule_type == "nat") { 
                  this.hidden_nat_rules.push(item); 
                  return false; 
              } 
              if(this.list_type == item.rule_type){ 
                return true; 
              } else { 
                this.hidden_rules.push(item);
                return false; 
              }
            }, this); 
        this.dnd_source.insertNodes(false, filtered_list);
    },

    _expanding_rule: function (w) {
        this.dnd_source.selectNone();
    },

    _collapsing_rule: function (w) {
        this.dnd_source.selectNone();
    },

    _changing_rule: function (w, old_rule, new_rule) {
        this.modified = true;
        this.onModify();
    },

    _on_dnd_drop: function (source, nodes, copy) {
        this.modified = true;
        this.onModify();
    },

    deleteSelected: function () {
        this.modified = true;
        this.dnd_source.deleteSelectedNodes();
        this.onModify();
    },

    _keypress: function (evt) {
        // TBD: This is not yet working correctly.  Seems to fail to get
        // TBD: keypress events when rule is not expanded.
        if (evt.keyCode == dojo.keys.DELETE)
            this.dnd_source.deleteSelectedNodes();
    },

    addRule: function (rule) {
        this.modified = true;
        var anchor = this.dnd_source.anchor;
        this.dnd_source.insertNodes(true, [ rule ], true, anchor);
        this.onModify();
    },

    getPolicy: function () {
        if (! this.modified) { 
            return this.policy;
        }

        if(this.list_type == "all") {
            // if all items are on the page
            return dojo.query("div.ruleContainer", this.rulelist).map(function (n, idx) {
              var r = dijit.byNode(n).rule;
              if (idx != r.priority) {
                  r.priority = idx;
                  // Remove rule_id so policyws will see this as an updated rule
                  delete r["rule_id"];
              }
              return r;
            });
        }

        // remaining cases:  this.item_type == "comm" or "auth"
        var visible_rules = 
          dojo.query("div.ruleContainer", this.rulelist).map(function (n, idx) {
              return dijit.byNode(n).rule;
        });

        // auth rules must go before comm rules
        var non_nat_rules = (this.list_type == "comm") ? 
                              this.hidden_rules.concat(visible_rules) : 
                              visible_rules.concat(this.hidden_rules);
        // nat rules always go up front
        var all_rules = this.hidden_nat_rules.concat(non_nat_rules); 
        // i'm being lazy here and not even trying to preserve
        // any rule_ids that may not have changed. 
        dojo.forEach(all_rules, function(r,idx) {       
          r.priority = idx;
          delete r["rule_id"];
        });
        return all_rules; 
    },

    setListType: function(new_type) { 
      this.list_type = new_type; 
    },

    onModify: function () {
        // Extention point called when policy is modified
    },

    startup: function () {
        this.modified = false;
        this.dnd_source = new dojo.dnd.Source(this.rulelist, {
            creator: dojo.hitch(this, function (r) {
                var w = new this.ruleWidgetType({rule: r});
                w.startup();
                if (w.onExpand != null) {
                    dojo.connect(w, "onExpand", this, "_expanding_rule");
                }
                if (w.onCollapse != null) {
                    dojo.connect(w, "onCollapse", this, "_collapsing_rule");
                }
                if (w.onChange != null) {
                    dojo.connect(w, "onChange", this, "_changing_rule");
                }
                return { node: w.domNode, data: r, type: "rule" };
            }),
            skipForm: true,
            withHandles: true
        });
        dojo.subscribe("/dnd/drop", dojo.hitch(this, this._on_dnd_drop));
        dojo.connect(this.rulelist, "onkeypress", this, "_keypress");

        this.inherited("startup", arguments);
    }
});
