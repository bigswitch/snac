dojo.provide("nox.ext.apps.snackui.policyui.rules");

dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");

var updatemgr = null;

var policyid = null;
var rules = null;

// cache the current policy in a global for hitcounts
var latest_policy = null; 

function get_rules() {
    nox.ext.apps.coreui.coreui.getUpdateMgr().xhrGet({
        url: "/ws.v1/policy/" + policyid + "/rules",
        load: function (response, ioArgs) {
            // remove the following line once policy webservice
            // is fixed to return rules with the correct policy_id
            rulelistWidget.policyid = policyid;
            rulelistWidget.setListType(list_type); 
            rulelistWidget.setPolicy(response);
            latest_policy = response;
            update_hit_counts();  
        },
        timeout: 30000,
        handleAs: "json"
    });
}

function init_policy() {
    revertBtn.setAttribute("disabled", true);
    //analyzeBtn.setAttribute("disabled", true);
    applyBtn.setAttribute("disabled", true);
    nox.ext.apps.coreui.coreui.getUpdateMgr().xhrGet({
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
    nox.ext.apps.coreui.coreui.getUpdateMgr().rawXhrPost({
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

function reset_counters() {
    nox.ext.apps.coreui.coreui.getUpdateMgr().xhrDelete({
        url: "/ws.v1/policy/stats",
        load: function (response, ioArgs) {
            init_policy();
        },
        timeout: 30000
    });
}

// this function is called periodically by the UpdateMgr
// to allow us to update hit counts for all active policy rules
function update_hit_counts() {
     
  dojo.forEach(latest_policy, function(rule) { 
        if(rule.rule_id == null) 
          return; // don't query for non-existent rules

        nox.ext.apps.coreui.coreui.getUpdateMgr().xhrGet({
          url: "/ws.v1/policy/" + policyid + "/rule/" + rule.rule_id + "/stats",
          load: function (response, ioArgs) {
            var elem = dojo.byId("hit-count-" + rule.rule_id);
            if(elem != null) // some rules are not displayed on the page 
              elem.innerHTML = response.count + " matches"; 
          },
          timeout: 30000,
          handleAs: "json", 
          error: function(response, ioArgs) { /* do nothing*/ } 
        });
      }
  ); 
} 

dojo.addOnLoad(function () {
    dojo.connect(rulelistWidget, "onModify", dojo.global, function(e) {
        on_rulelist_modify();
    });
    init_policy();
    
    hit_count_update = coreui.getUpdateMgr().userFnCall({
        purpose: "Updating policy rule hit-counts",
        fn: update_hit_counts, 
        recur: true
    });

});
