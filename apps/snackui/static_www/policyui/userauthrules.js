dojo.provide("nox.ext.apps.snackui.policyui.userauthrules");

dojo.require("nox.webapps.coreui.coreui.UpdateMgr");

var updatemgr = null

var policyid = null;
var rules = null;

function get_rules() {
    nox.webapps.coreui.coreui.getUpdateMgr().xhrGet({
        url: "/ws.v1/policy/" + policyid + "/rules",
        load: function (response, ioArgs) {
            rulelistWidget.setPolicy(response);
        },
        timeout: 30000,
        handleAs: "json"
    });
}

function init_policy() {
    revertBtn.setAttribute("disabled", true);
    //analyzeBtn.setAttribute("disabled", true);
    applyBtn.setAttribute("disabled", true);
    nox.webapps.coreui.coreui.getUpdateMgr().xhrGet({
        url: "/ws.v1/policy",
        load: function (response, ioArgs) {
            policyid = response.policy_id;
            get_rules();
        },
        timeout: 30000,
        handleAs: "json"
    });
}

function on_rulelist_modify() {
    revertBtn.setAttribute("disabled", false);
    //analyzeBtn.setAttribute("disabled", false);
    applyBtn.setAttribute("disabled", false);
}

function revert_changes() {
    this.init_policy();
}

function apply_changes() {
    nox.webapps.coreui.coreui.getUpdateMgr().rawXhrPost({
        url: "/ws.v1/policy",
        postData: dojo.toJson({
            "policy_id" : policyid,
            "rules" : rulelistWidget.getPolicy()
        }),
        headers: { "Content-Type": "application/json" },
        load: function (response, ioArgs) {
            init_policy();
        },
        // TBD: need to gracefully handle errors here...
        timeout: 30000
    });
}

dojo.addOnLoad(function () {
    dojo.connect(rulelistWidget, "onModify", dojo.global, "on_rulelist_modify");
    init_policy();
});
