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

dojo.provide("nox.ext.apps.directory.directorymanagerws.Location");

dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchPort");
dojo.require("nox.ext.apps.directory.directorymanagerws.Switch");
dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");
dojo.require("nox.ext.apps.directory.directorymanagerws._Principal");
dojo.require("nox.ext.apps.directory.directorymanagerws.HostStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.UserStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.LocationGroupStore");

dojo.declare("nox.ext.apps.directory.directorymanagerws.Location", [ nox.ext.apps.directory.directorymanagerws._Principal ], {

    dmws: nox.ext.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        // summary: constructor
        //
        // keywordParameter: {switchObj: object}
        //    Switch object corresponding to this location.
        // keywordParameter: {switchPortObj: object}
        //    Switch port object corresponding to this location.
        if (this.switchObj == undefined)
            this.switchObj = null;
        if (this.switchPortObj == undefined)
            this.switchPortObj = null;
        dojo.mixin(this.derivedAttributes, {
            "uiSwitchMonitorLink": {
                get: dojo.hitch(this, "uiSwitchMonitorLink"),
                hasChanged: dojo.hitch(this, "basicDataChanged",
                                      [ "switch_name" ])
            },
            "uiSwitchMonitorLinkText": {
                get: dojo.hitch(this, "uiSwitchMonitorLinkText"),
                hasChanged: dojo.hitch(this, "basicDataChanged",
                                      [ "switch_name" ])
            },
            "uiSwitchPortMonitorLink": {
                get: dojo.hitch(this, "uiSwitchPortMonitorLink"),
                hasChanged: dojo.hitch(this, "basicDataChanged",
                                       [ "switch_name", "port_name" ])
            }, 
            "uiSwitchPortMonitorLinkText": {
                get: dojo.hitch(this, "uiSwitchPortMonitorLinkText"),
                hasChanged: dojo.hitch(this, "basicDataChanged",
                                       [ "switch_name", "port_name" ])
            }
        });
        dojo.mixin(this.updateTypes, {
            "info": {
                load: dojo.hitch(this, "updateInfo")
            },
            "config" : {
                load: dojo.hitch(this, "updateConfig")
            }
        });
    },

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/location/"
            + encodeURIComponent(this.directoryName()) + "/"
            + encodeURIComponent(this.principalName());
    },

    uiMonitorPath: function () {
        if (this.isNull())
            return null;
        if (this.switchPortObj == null)
            return null;
        // For the moment, just point to the swithport monitor page
        return this.switchPortObj.uiMonitorPath();
        // If we end up building a location specific page, add it here.
        // return "/Monitors/Locations/LocationInfo?name=" + encodeURIComponent(this.name);
    },

    uiSwitchMonitorLink: function () {
        if (this.switchObj == null)
            return null;
        return this.switchObj.uiMonitorLink();
    },
    
    uiSwitchMonitorLinkText: function () {
        if (this.switchObj == null)
            return null;
        return this.switchObj.uiMonitorLinkText();
    },

    uiSwitchPortMonitorLink: function () {
        if (this.switchPortObj == null)
            return null;
        return this.switchPortObj.uiMonitorLink();
    },
    
    uiSwitchPortMonitorLinkText: function () {
        if (this.switchPortObj == null)
            return null;
        return this.switchPortObj.uiMonitorLinkText();
    },

    updateConfig: function () {
        return this._xhrGetMixin("config", this.wsv1Path() + "/config", function (r) {
            this.switchObj = new this.dmws.Switch({
                initialData: { name: r.switch_name }
            });
            this.switchPortObj = new this.dmws.SwitchPort({
                initialData: { name: r.port_name },
                switchObj: this.switchObj
            });
            return r;
        });
    },

    updateInfo: function () {
        return this._xhrGetMixin("info", this.wsv1Path());
    },

    hostStore: function (kwarg) {
        return new this.dmws.HostStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/host",
            "locationObj": this
        }));
    },

    userStore: function (kwarg) {
        return new this.dmws.UserStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/user",
            "locationObj": this
        }));
    },

    groupStore: function (kwarg) {
        return new this.dmws.LocationGroupStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/group",
            "locationObj": this
        }));
    }

});
