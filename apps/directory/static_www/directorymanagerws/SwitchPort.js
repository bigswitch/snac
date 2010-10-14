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

dojo.provide("nox.ext.apps.directory.directorymanagerws.SwitchPort");

dojo.require("nox.ext.apps.coreui.coreui._NamedEntity");
dojo.require("nox.ext.apps.directory.directorymanagerws.HostStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.UserStore");

dojo.declare("nox.ext.apps.directory.directorymanagerws.SwitchPort", [ nox.ext.apps.coreui.coreui._NamedEntity ], {

    dmws: nox.ext.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        // summary: constructor
        //
        // keywordParameters: {switchObj: object}
        //    Object for host with which this interface is associated.
        if (this.switchObj == undefined)
            throw new Error("SwitchPort must be initialized with the associated switch object");
        dojo.mixin(this.derivedAttributes, {
            uiMonitorPath: {
                get: dojo.hitch(this, "uiMonitorPath"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorLink: {
                get: dojo.hitch(this, "uiMonitorLink"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            uiMonitorLinkText : {
                get: dojo.hitch(this, "uiMonitorLinkText"),
                hasChanged: dojo.hitch(this, "nameHasChanged")
            },
            "uiSwitchAndPortMonitorLinks" : {
                get: dojo.hitch(this, "uiSwitchAndPortMonitorLinks")
            },
            speed: {
                get: dojo.hitch(this, "speed")
            },
            port_no: {
                get: dojo.hitch(this, "port_no")
            },
            locationDirectoryName: {
                get: dojo.hitch(this, "locationDirectoryName"),
                set: dojo.hitch(this, "locationDirectoryNameSet"),
                hasChanged: dojo.hitch(this, "locationHasChanged")
            },
            locationPrincipalName: {
                get: dojo.hitch(this, "locationPrincipalName"),
                set: dojo.hitch(this, "locationPrincipalNameSet"),
                hasChanged: dojo.hitch(this, "locationHasChanged")
            }    
        });
        dojo.mixin(this.updateTypes, {
            "stat" : {
                load: dojo.hitch(this, "updateStat")
            },
            "config" : {
                load: dojo.hitch(this, "updateConfig")
            }
        });
    },

    wsv1Path: function () {
        return this.switchObj.wsv1Path() + "/port/" + this._data.name;
    },

    uiMonitorPath: function () {
        return "/Monitors/Switches/SwitchPortInfo?switch="
            + encodeURIComponent(this.switchObj.getValue("name"))
            + "&port=" + encodeURIComponent(this.getValue("name"));
    },

    uiMonitorLink: function () {
        var a = document.createElement("a");
        a.href = this.uiMonitorPath();
        a.appendChild(document.createTextNode(this._data.name));
        return a;
    },

    uiMonitorLinkText: function () {
        return "<a href='" + this.uiMonitorPath() + "'>" + this._data.name + "</a>";
    },

    uiSwitchAndPortMonitorLinks: function () {
        var s = document.createElement("span");
        s.appendChild(this.switchObj.uiMonitorLink());
        s.appendChild(document.createTextNode(":"));
        s.appendChild(this.uiMonitorLink());
        return s;
    },

    updateStat: function (kwarg) {
        return this._xhrGetMixin("stat", this.wsv1Path() + "/stat");
    },

    updateConfig: function (kwarg) {
        return this._xhrGetMixin("config", this.wsv1Path() + "/config");
    },

    userStore: function (kwarg) {
        return new this.dmws.UserStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/user"
        }));
    },

    hostStore: function (kwarg) {
        return new this.dmws.HostStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/host"
        }));
    },

    speed: function () {
        if (this._data.stat_speed == null)
            return this._data.config_speed;
        return this._data.stat_speed;
    },

    port_no: function () {
        if (this._data.stat_port_no == null)
            return this._data.config_port_no;
        return this._data.stat_port_no;
        },

    locationDirectoryName: function () {
        try {
            return this._data.location.split(";", 2)[0]
        } catch (e) {
            return null;
        }
    },

    locationDirectoryNameSet: function (v) {
        var pname = this.locationPrincipalName();
        this.setValue("location", v + ";" + pname);
    },

    locationPrincipalName: function () {
        try {
            return  this._data.location.split(";", 2)[1]
        } catch (e) {
            return null;
        }
    },

    locationPrincipalNameSet: function (v) {
        var dname = this.locationDirectoryName();
        this.setValue("location", dname + ";" + v);
    },

    locationHasChanged: function (l) {
        return dojo.some(l, "return item.attribute == 'location';");
    }

});
