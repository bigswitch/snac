dojo.provide("nox.ext.apps.snackui.policyui.PolicyStore");

dojo.require("nox.apps.coreui.coreui._UpdatingStore");
dojo.require("nox.ext.apps.snackui.policyui.PolicyStoreRule");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyStore", [ nox.apps.coreui.coreui._UpdatingStore ], {

    // TBD: - This store *really* needs to have user-visible conflict
    // TBD:   notification implemented.

    // description:
    //    Store containing rules of a policy.  Because preventing
    //    inadvertent loss of policy rules due to near-simultaneous
    //    update by multiple users is extremely important, the policy
    //    web service operates slightly different from most other web
    //    services.  It requires that submission of a new policy be
    //    accompanied by the policy ID of the currently active policy,
    //    and changes the policy ID on every policy change.
    //
    //    When update() is called on this store (or whenever an
    //    auto-update occurs) the store will attempt to update its
    //    contents to the most recent policy on the server.  If the
    //    user is editing the rules (as opposed to just viewing them)
    //    using the autoUpdate may be confusing.  In these cases it is
    //    suggested to refrain from using auto-update.  If auto-update
    //    is not used there is a chance the server policy will have
    //    changed before the user saves local edits.  In these cases the
    //    server will return a conflict error on save requests.  The
    //    conflict error handler can then notify the user that the
    //    policy has changed and call update to attempt to merge the
    //    changes into the most recent policy.

    _internals_init: function () {
        this.inherited(arguments);
        this.policyId = null;
        this.itemConstructor = nox.ext.apps.snackui.policyui.PolicyStoreRule;
        this.url = "/ws.v1/policy";  // Note: user shouldn't attempt to change!
        this._pendingPolicyId = null;
    },

    _handleServerResponse: function (response, ioArgs) {
        // implementation:
        //    Overriding _handleServerResponse gives us an opportunity
        //    to place another asynchronous call in the chain to get
        //    the policy ID.  No additional work is required if the
        //    policy ID has not changed.  Otherwise we call the
        //    inherited _handleServerResponse to do the rest of the
        //    work.
        this._pendingPolicyId = response.policy_id;
        if (this.policyId != this._pendingPolicyId) {
            this.updatemgr.xhrGet({
                url: this.url + "/" + this._pendingPolicyId.toString() + "/rules",
                load: dojo.hitch(this, nox.apps.coreui.coreui._UpdatingStore.prototype._handleServerResponse),
                error: this._inProgressUpdates.slice(-1)[0].errhandler,
                timeout: this.timeout,
                handleAs: "json"
            });
        } else {
            this._finishUpdate();
        }
    },

    _finishUpdate: function () {
        // implementation:
        //    Overriding _finishUpdate allows us to record the new
        //    policy ID.  We don't want to record it earlier because
        //    we haven't really successfully updated yet.
        this.policyId = this._pendingPolicyId;
        this._pendingPolicyId = null;
        this.inherited(arguments);
    }

});
