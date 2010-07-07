dojo.provide("nox.ext.apps.snackui.policyui.PolicyStoreRule");

dojo.require("nox.apps.coreui.coreui._UpdatingItem");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyStoreRule", [ nox.apps.coreui.coreui._UpdatingItem ], {

    identityAttributes: [ "rule_id" ],
    labelAttributes: [ "text" ]

});
