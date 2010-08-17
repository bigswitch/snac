dojo.provide("nox.ext.apps.snackui.policyui.PolicyStoreRule");

dojo.require("nox.webapps.coreui.coreui._UpdatingItem");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyStoreRule", [ nox.webapps.coreui.coreui._UpdatingItem ], {

    identityAttributes: [ "rule_id" ],
    labelAttributes: [ "text" ]

});
