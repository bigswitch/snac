/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.ControllerInterface");

dojo.require("nox.apps.coreui.coreui._NamedEntity");

dojo.declare("nox.ext.apps.snackui.settingsui.ControllerInterface", 
             [ nox.apps.coreui.coreui._NamedEntity ], {
   constructor: function (kwarg) {
       dojo.mixin(this.updateTypes, {
               "info": {
                   load: dojo.hitch(this, "updateInfo"),
                   save: dojo.hitch(this, "storeInfo")
                }
       });
   },

   updateInfo: function (kwarg) {
       return this._xhrGetMixin("info", this.wsv1Path());
   },

   storeInfo: function (kwarg) {
        nox.apps.coreui.coreui.getUpdateMgr().xhr("PUT", {
            url: this.wsv1Path(),
            headers: { "content-type": "application/json" },
            putData: dojo.toJson(this._data),
            load: function (response, ioArgs) {
                    if (response != true) {
                        nox.apps.coreui.coreui.getUpdateMgr().updateNow();
                    }
            },
            timeout: 30000,
            error: coreui.UpdateErrorHandler.create()
        });       
   },

   wsv1Path: function () {
                if (this.isNull()) {
                    return null;
                }

                return "/ws.v1/nox/local_config/interface/" +
                    encodeURIComponent(this.displayName());
   }
});
