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

dojo.provide("nox.ext.apps.directory.directorymanagerws.HostBinding");

dojo.require("nox.ext.apps.coreui.coreui._UpdatingItem");

dojo.declare("nox.ext.apps.directory.directorymanagerws.HostBinding", [ nox.ext.apps.coreui.coreui._UpdatingItem ], {

    identityAttributes: [ "dladdr", "nwaddr", "dpid", "port" ],
    labelAttributes: [ "dladdr", "nwaddr", "dpid", "port" ],

    constructor: function (data) {
        dojo.mixin(this.derivedAttributes, {
            intfType: {
                get: dojo.hitch(this, "intfType"),
                set: dojo.hitch(this, "setIntfType")
            }
        });
    },

    intfType: function () {
        if (this._data.is_gateway && this._data.is_gateway != "False")
            return "Gateway";
        else if (this._data.is_router && this._data.is_router != "False")
            return "Router";
        else
            return "End-Host";
    },

    setIntfType: function (v) {
        if (v == "Gateway") {
            this.setValue("is_gateway", "True");
            this.setValue("is_router", "False");
        } else if (v == "Router") {
            this.setValue("is_gateway", "False");
            this.setValue("is_router", "True");
        } else {
            this.setValue("is_gateway", "False");
            this.setValue("is_router", "False");
        }
    },

    isValid: function () {
        // TBD: validate contents of all fields.
        var found_binding = false;
        dojo.forEach([ "dladdr", "nwaddr", "location" ], function (t) {
            if (this._data[t] != null && this._data[t] != "") {
                if (found_binding == false) {
                    found_binding = true;
                } else {
                    return false;
                }
            }
        }, this);
        if (! found_binding)
            return false;
        if ((! (this._data.is_gateway == "True"
                || this._data.is_gateway == "False"))
            || (! (this._data.is_router == "True"
                   || this._data.is_router == "False")))
            return false;
        return true;
    }

});
