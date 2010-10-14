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

dojo.provide("nox.ext.apps.directory.directorymanagerws.SwitchGroup");

dojo.require("nox.ext.apps.directory.directorymanagerws._PrincipalGroup");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.SwitchGroupStore");

dojo.declare("nox.ext.apps.directory.directorymanagerws.SwitchGroup", [ nox.ext.apps.directory.directorymanagerws._PrincipalGroup ], {

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/group/switch/"
            + encodeURIComponent(this.directoryName()) + "/"
            + encodeURIComponent(this.groupName());
    },

    uiMonitorPath: function () {
        if (this.isNull()) {
            return null;
        }
        return "/Monitors/Groups/SwitchGroupInfo?name=" + encodeURIComponent(this._data.name);
    },

    parentGroupStore: function (kwarg) {
        return new this.dmws.SwitchGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/parent"
        }));
    },

    principalMemberStore: function (kwarg) {
        return new this.dmws.SwitchStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/principal"
        }));
    },

    subgroupMemberStore: function (kwarg) {
        return new this.dmws.SwitchGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/subgroup"
        }));
    }

});
