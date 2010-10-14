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

dojo.provide("nox.ext.apps.directory.directorymanagerws.SwitchStore");

dojo.require("nox.ext.apps.directory.directorymanagerws._PrincipalStore");
dojo.require("nox.ext.apps.directory.directorymanagerws.Switch");

dojo.declare("nox.ext.apps.directory.directorymanagerws.SwitchStore", [ nox.ext.apps.directory.directorymanagerws._PrincipalStore ], {
    url: "",
    data: null,

    constructor: function (kwarg) {
        this.itemConstructor = this.dmws.Switch;
        if (this.url == null)
            this.url = "/ws.v1/switch";
    }

});
