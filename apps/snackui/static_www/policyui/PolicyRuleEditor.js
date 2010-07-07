dojo.provide("nox.ext.apps.snackui.policyui.PolicyRuleEditor");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.ComboBox");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.Textarea");
dojo.require("dijit.form.SimpleTextarea");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyRuleEditor", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.policyui", "templates/PolicyRuleEditor.html"),
    widgetsInTemplate: true,

    rule: null,


    postMixInProperties: function () {
        this.inherited("postMixInProperties", arguments);
        this.rule = dojo.clone(this.rule);
    },
    
    _set_disabled_status: function(disable){
        this.exception.attr("disabled", disable);
        this.comment.attr("disabled", disable);
        this.description.attr("disabled", disable);
    },

    _set_widget_values: function () {
        this.pyrule.setValue(this.rule.text);
        this.description.setValue(this.rule.description);
        this.exception.setValue(this.rule.exception);
        this.protect.setValue(this.rule["protected"]);
        this.comment.setValue(this.rule.comment);
        var dt = new Date(this.rule.timestamp * 1000);
        if(this.rule.user != null) 
          var m = dt.toLocaleString() + " by " + this.rule.user;
        else
          var m = "Never"; 
        this.modifiedmsg.appendChild(document.createTextNode(m));
        if (this.rule["protected"] != undefined) {
            this._set_disabled_status(this.rule["protected"]);
        } else {
            this._set_disabled_status(false);
        }
    },

    _update_rule: function (prop, value) {
        if (this.rule[prop] != value) {
            this.modified = true;
            this.rule[prop] = value;
        }
    },

    _get_widget_values: function () {
        this._update_rule("text", this.pyrule.getValue());
        this._update_rule("description", this.description.getValue());
        this._update_rule("exception", this.exception.getValue() == "on");
        this._update_rule("protected", this.protect.getValue() == "on");
        this._update_rule("comment", this.comment.getValue());
    },

    _cancel: function () {
        this.onCancel(this.rule);
    },

    _done: function () {
        this._get_widget_values();
        this.onDone(this.rule, this.modified);
    },
    
    _findRuleContainer: function(node){
        for(; node; node = node.parentNode){
            if(node === dojo.body()){
                node = null;
                break;
            }
            if(dojo.hasClass(node, "ruleContainer")){
                break;
            }
        }
        return node;
    },
    
    _protect: function(){
        var ruleNode = this._findRuleContainer(this.domNode),
            disable = this.protect.getValue() == "on";
        if(ruleNode){
            if(disable){
                dojo.addClass(ruleNode, "protected");
                dojo.query(".rule", ruleNode).removeClass("dojoDndHandle");
            }else{
                dojo.removeClass(ruleNode, "protected");
                dojo.query(".rule", ruleNode).addClass("dojoDndHandle");
            }
        }
        this._set_disabled_status(disable);
    },

    _keypress: function (evt) {
        if (evt.keyCode == dojo.keys.ENTER)
            this._done();
        else if (evt.keyCode == dojo.keys.ESCAPE)
            this._cancel();
    },

    startup: function () {
        this.inherited("startup", arguments);
        this.modified = false;
        this._set_widget_values();
        //this.pyrule.focus();
        dojo.connect(this.doneBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
        dojo.connect(this.protect, "onClick", this, "_protect");
        //dojo.connect(this.content, "onkeypress", this, "_keypress");
    },

    onDone: function (rule, modified) {
        // Called when user clicks the done button w/updated rule contents
    },

    onCancel: function (rule) {
        // Called when user clicks the done button w/original rule contents
    }

});
