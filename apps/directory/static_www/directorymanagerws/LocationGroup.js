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

dojo.provide("nox.apps.directory.directorymanagerws.LocationGroup");

dojo.require("nox.apps.directory.directorymanagerws._PrincipalGroup");
dojo.require("nox.apps.directory.directorymanagerws.LocationStore");
dojo.require("nox.apps.directory.directorymanagerws.LocationGroupStore");

dojo.declare("nox.apps.directory.directorymanagerws.LocationGroup", [ nox.apps.directory.directorymanagerws._PrincipalGroup ], {

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/group/location/"
            + encodeURIComponent(this.getValue("directoryName")) + "/"
            + encodeURIComponent(this.getValue("groupName"));
    },

    uiMonitorPath: function () {
        if (this.isNull()) {
            return null;
        }
        return "/Monitors/Groups/LocationGroupInfo?name=" + encodeURIComponent(this._data.name);
    },

    parentGroupStore: function (kwarg) {
        return new this.dmws.LocationGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/parent"
        }));
    },

    principalMemberStore: function (kwarg) {
        return new this.dmws.LocationStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/principal"
        }));
    },

    subgroupMemberStore: function (kwarg) {
        return new this.dmws.LocationGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/subgroup"
        }));
    }


});
