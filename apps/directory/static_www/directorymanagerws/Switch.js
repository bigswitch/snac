/*
 Copyright 2008 (C) Nicira, Inc.

 This file is part of NOX.

 NOX is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 NOX is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

dojo.provide("nox.apps.directory.directorymanagerws.Switch");

dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws._Principal");
dojo.require("nox.apps.directory.directorymanagerws.SwitchPortStore");
dojo.require("nox.apps.directory.directorymanagerws.SwitchGroupStore");
dojo.require("nox.apps.coreui.coreui.UpdateMgr");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("dijit.Dialog"); 
dojo.require("nox.apps.default_switch_approval.switch_approval.SwitchApprover");

dojo.declare("nox.apps.directory.directorymanagerws.Switch", [ nox.apps.directory.directorymanagerws._Principal ], {

    constructor: function (kwarg) {
        dojo.mixin(this.updateTypes, {
            "config" : {
                load: dojo.hitch(this, "updateConfig")
            },
            "stat" : {
                load: dojo.hitch(this, "updateStat")
            },
            "approval" : {
                load: dojo.hitch(this, "updateApproval")
            },
            "info" : {
                load: dojo.hitch(this, "updateInfo")
            },
            "desc" : {
                load: dojo.hitch(this, "updateDesc")
            }
        });
    },

    wsv1Path: function () {
        if (this.isNull())
            return null;
        return "/ws.v1/switch/"
            + encodeURIComponent(this.directoryName()) + "/"
            + encodeURIComponent(this.principalName());
    },

    uiMonitorPath: function () {
        if (this.isNull())
            return null;
        return "/Monitors/Switches/SwitchInfo?name=" + 
          encodeURIComponent(this.getValue("name"));
    },

    updateInfo: function () {
        return this._xhrGetMixin("info", this.wsv1Path(), function (r) {
            return { dpid: r.dpid };
        });
    },

    updateConfig: function () {
        return this._xhrGetMixin("config", this.wsv1Path() + "/config");
    },
    
    updateDesc: function () {
        return this._xhrGetMixin("desc", this.wsv1Path() + "/desc");
    },


    updateStat: function () {
        // summary: update statistics values for switch
        // description:
        //    Statistics values are only available if the switch is active.
        //    This method protects against that by checking to see if the
        //    switch is active before updating.  Since the active status
        //    is determined by the "status" update type, that type must
        //    be in updateList (which is processed sequentially) before the
        //    "stat" updateType.

        // updated - took out active check.  switch page handles error
        return this._xhrGetMixin("stat", this.wsv1Path() + "/stat");
    },

    updateApproval: function () {
        return this._xhrGetMixin("approval", this.wsv1Path() + "/approval");
    },

    portStore: function (kwarg) {
        return new this.dmws.SwitchPortStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/port",
            "switchObj": this
        }));
    },

    groupStore: function (kwarg) {
        return new this.dmws.SwitchGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/group"
        }));
    },

    set_approval: function(is_approved, onComplete) {
        var updatemgr =  nox.apps.coreui.coreui.getUpdateMgr();  
        var path = this.wsv1Path() + "/approval?approved=" + is_approved; 
        updatemgr.rawXhrPut({
            handleAs: 'json',
            url: path,
            headers: { "content-type": "application/json" },
            putData: {},
            timeout: 5000,
            load: dojo.hitch(this, function (response, ioArgs) {
                      nox.apps.coreui.coreui.getUpdateMgr().updateNow();
                      if(onComplete != null) 
                          onComplete(this); 
                      return null; 
            })
      });
    },

  is_registered : function() { 
      var registered = false; 
      if(this._data.fp_credentials) { 
        dojo.forEach(this._data.fp_credentials, function(cred) { 
          if(cred.is_approved) 
            registered = true; 
        } );
      }
      return registered; 
  }, 

  get_fingerprint : function() { 
    if(this._data.fp_credentials && this._data.fp_credentials.length > 0)
      return this._data.fp_credentials[0].fingerprint;
    return ""; 
  }     
});

// the global SwitchUtil object provides access to code that is needed by 
// both the SwitchesMon and SwitchInfoMon pages in order to prevent code
// duplication. 

dojo.declare("nox.apps.directory.directorymanagerws.SwitchUtil", [], {

register_switch : function(selected_list, onComplete) {
  if (selected_list.length == 0) { 
      coreui.UpdateErrorHandler.showError("Must select a switch to register.", 
          { hide_retry : true , 
            header_msg : "Invalid Operation:",
            validation_error: true  
          });
      return; 
  } 
  if (selected_list.length > 1) { 
      coreui.UpdateErrorHandler.showError("Cannot register multiple switches simultaneously.", 
          { hide_retry : true , 
            header_msg : "Invalid Operation:",
            validation_error: true  
          });
      return; 
  } 
  var item = selected_list[0];
  item.update( { 
    onComplete: dojo.hitch(this, function() {
      this.show_switch_reg_dialog(item, 
        {load_new_switch_page : false,
         onComplete : onComplete }); 
      })
    }); 
}, 


//FIXME: I now know there are easier ways to do this.
// See the dialogs used to modify groups. 
show_switch_reg_dialog : function(switch_obj,props) { 
                  if(switch_obj.is_registered()) { 
                      coreui.UpdateErrorHandler.showError(
                      "You must deregister the switch, then register it again.",
                              {  hide_retry : true,
                                header_msg : "Switch Already Registered:",
                                validation_error : true
                              });
                      return; 
                  } 

                  var appr = dijit.byId("approve_id"); 
                  if( appr ) {
                      // must destroy to avoid duplicate id error 
                      appr.destroy(); 
                  }
                  if (props == null) 
                    props = {}; 
                  props.id = "approve_id";
                  props.switch_obj = switch_obj; 
                  appr = new nox.apps.default_switch_approval.switch_approval.SwitchApprover(props);
                  dojo.body().appendChild(appr.domNode);
                  appr.startup();

}, 

get_status_cell : function() { 

      var status_cell = { 
                name: "status",
                header: "Status" ,
                get: function (item) {
                    var s = document.createElement("span");
                    var txt = item.getValue("status");
                    s.className = "errormsg"
                    if(!item.is_registered()) {
                        txt = "unregistered";
                    } else if (txt != "inactive") {
                        s.className = "successmsg";
                    }
                    s.appendChild(document.createTextNode(txt));
                    return s;
                }
      };

      return status_cell; 
} // end fn  

});


(function () {
    var switch_util = null;
    nox.apps.directory.directorymanagerws.getSwitchUtil = function () {
        if (switch_util == null) {
            switch_util = new nox.apps.directory.directorymanagerws.SwitchUtil();
        }
        return switch_util;
    }
})();

