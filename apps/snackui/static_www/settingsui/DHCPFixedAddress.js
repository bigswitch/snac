/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.DHCPFixedAddress");

dojo.require("nox.apps.coreui.coreui._NamedEntity");

dojo.declare("nox.ext.apps.snackui.settingsui.DHCPFixedAddress", 
             [ nox.apps.coreui.coreui._NamedEntity ], {
   constructor: function (kwarg) {
       dojo.mixin(this.updateTypes, {
               "info": {
                   load: dojo.hitch(this, "updateInfo"),
                   save: dojo.hitch(this, "storeInfo")
                }
           });
       this.updateList = [ 'info' ];
   },

   updateInfo: function (kwarg) {

   },

   storeInfo: function (kwarg) {

   },

   wsv1Path: function () {
       return "/ws.v1/config/dhcp_config";
   }
});
