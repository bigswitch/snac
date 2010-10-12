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

dojo.provide("nox.apps.directory.directorymanagerws.Host");
dojo.require("nox.apps.directory.directorymanagerws.UserStore");
dojo.require("nox.apps.directory.directorymanagerws.HostGroupStore");
dojo.require("nox.apps.directory.directorymanagerws.HostBindingStore");
dojo.require("nox.apps.directory.directorymanagerws.HostInterfaceStore");

dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws._Principal");

dojo.declare("nox.apps.directory.directorymanagerws.Host", [ nox.apps.directory.directorymanagerws._Principal ], {

    constructor: function (kwarg) {
        dojo.mixin(this.updateTypes, {
            "info": {
                load: dojo.hitch(this, "updateInfo")
            },
            "osFingerprint" : {
                load: dojo.hitch(this, "updateOSFingerprint")
            },
            "lastSeen" : {
                load: dojo.hitch(this, "updateLastSeen")
            }, 
            "activeInterfaces" : {
                load: dojo.hitch(this, "updateActiveInterfaces")
            }
        });
    },

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/host/"
            + encodeURIComponent(this.directoryName()) + "/"
            + encodeURIComponent(this.principalName());
    },

    uiMonitorPath: function () {
        if (this.isNull()) {
            return null;
        }
        return "/Monitors/Hosts/HostInfo?name=" + encodeURIComponent(this._data.name);
    },

    updateInfo: function (kwarg) {
        return this._xhrGetMixin("info", this.wsv1Path());
    },


    updateOSFingerprint: function () {
        return this._xhrGetMixin("osFingerprint", this.wsv1Path() + "/os_fingerprint");
    },

    updateLastSeen: function () {
        return this._xhrGetMixin("lastSeen", this.wsv1Path() + "/last_seen");
    },

    updateActiveInterfaces: function() {
      if(this.activeInterfacesStore == null) { 
        this.activeInterfacesStore = this.interfaceStore({
            hostObj: this, 
            itemParameters: { 
              updateList: [ "info" ]
            }
        }); 
      }
      return this._storeQueryMixin("updateActiveInterfaces", "active_interfaces", 
                      this.activeInterfacesStore, {}, null);  
    }, 
    groupStore: function (kwarg) {
        return new this.dmws.HostGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/group"
        }));
    },

    userStore: function(kwarg) {
        return new this.dmws.UserStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/active/user"
        }));
    },

    bindingStore: function (kwarg) {
        return new this.dmws.HostBindingStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path(),
            "hostObj": this
        }));
    },

    interfaceStore: function (kwarg) {
        return new this.dmws.HostInterfaceStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/active/interface",
            "hostObj": this
        }));
    }, 

    //FIXME: this is hackilicious.  since saving the static 
    // bindings of a host already saves the entire host, we can
    // use that as a hack to implement a generic save method 
    // that can be called for changes to attributes other than 
    // the static binding (e.g., the 'description' field).  Once
    // we full write all of the read-write store functionality, 
    // we should redo it so that the host binding store's save()
    // method simply calls save on the host, but that is not a 
    // simple change right now. 
    // Note: waiting for the onComplete callback is necessary, 
    // as the binding store must contain bindings before it can be saved.
    save : function() { 
      var bs = this.bindingStore({}); 
      bs.update({ onComplete : function() { 
                                  bs.save();
                                  bs.destroy();                         
                                }
                }); 
    } 
});
