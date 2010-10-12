/*
 Copyright 2008 (C) Nicira, Inc.

 This file is part of NOX.

 NOX is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 NOX is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
n MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

dojo.provide("nox.apps.directory.directorymanagerws.HostInterface");

dojo.require("nox.apps.coreui.coreui._NamedEntity");
dojo.require("nox.apps.directory.directorymanagerws.Switch");
dojo.require("nox.apps.directory.directorymanagerws.SwitchPort");
dojo.require("nox.apps.directory.directorymanagerws.Location");

dojo.declare("nox.apps.directory.directorymanagerws.HostInterface", [ nox.apps.coreui.coreui._NamedEntity ], {

    dmws: nox.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        // summary: constructor
        //
        // keywordParameters: {hostObj: object}
        //    Object for host with which this interface is associated.
        this.itemConstructor = this.dmws.HostInterface
        if (this.hostObj == undefined)
            throw new Error("HostInterface must be initialized with the associated host object");
        dojo.mixin(this.derivedAttributes, {
            uiLocationMonitorLink: {
                get: dojo.hitch(this, "uiLocationMonitorLink")
            },
            uiLocationMonitorLinkText: {
                get: dojo.hitch(this, "uiLocationMonitorLinkText")
            },
            uiSwitchMonitorLink: {
                get: dojo.hitch(this, "uiSwitchMonitorLink")
            },
            uiSwitchPortMonitorLink: {
                get: dojo.hitch(this, "uiSwitchPortMonitorLink")
            },
            uiSwitchAndPortMonitorLinks: {
                get: dojo.hitch(this, "uiSwitchAndPortMonitorLinks")
            }
        });
        dojo.mixin(this.updateTypes, {
            "info": {
                load: dojo.hitch(this, "updateInfo")
            }
        });
    },

    wsv1Path: function () {
        return this.hostObj.wsv1Path() + "/interface/" + this._data.name;
    },

    uiMonitorPath: function () {
        return "/Monitors/Hosts/HostInfo?name="
            + encodeURIComponent(this.hostObj.getValue("name"))
            + "&interface=" + encodeURIComponent(this._data.name);
    },

    uiLocationMonitorLink: function () {
        if (this.location == null)
            return null;
        else
            return this.location.uiMonitorLink();
    },
    
    uiLocationMonitorLinkText: function () {
        if (this.location == null)
            return null;
        else
            return this.location.uiMonitorLinkText();
    },

    uiSwitchMonitorLink: function () {
        if (this.switchObj == null)
            return null;
        return this.switchObj.uiMonitorLink();
    },

    uiSwitchPortMonitorLink: function () {
        if (this.switchPortObj == null)
            return null;
        return this.switchPortObj.uiMonitorLink();
    },

    uiSwitchAndPortMonitorLinks: function () {
        if (this.switchPortObj == null)
            return null;
        else
            return this.switchPortObj.uiSwitchAndPortMonitorLinks();
    },

    updateInfo: function (kwarg) {
        return this._xhrGetMixin("info", this.wsv1Path(), function (response) {
            if (response["switch_name"]) {
                this.switchObj = new nox.apps.directory.directorymanagerws.Switch({ initialData: { name: response["switch_name"] }});
                if (response["port_name"]) {
                    this.switchPortObj = new nox.apps.directory.directorymanagerws.SwitchPort({ 
                        switchObj:  this.switchObj,
                        initialData: { name: response["port_name"] }
                    });
                    if (response["location_name"]) {
                        this.location = new nox.apps.directory.directorymanagerws.Location({ 
                            initialData: { name: response["location_name"] },
                            updateList: ["config"],   // In what situations do we need?
                            switchObj: this.switchObj,
                            switchPortObj: this.switchPortObj
                        });
                    } 
                }
            }

            if (response.gateway)
                response.intftype = "Gateway";
            else if (response.router)
                response.intftype = "Router";
            else
                response.intftype = "End-Host";
            return response;
        });
    }
});
