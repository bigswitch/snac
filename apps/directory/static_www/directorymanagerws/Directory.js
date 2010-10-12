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

dojo.provide("nox.apps.directory.directorymanagerws.Directory");

dojo.require("nox.apps.coreui.coreui._NamedEntity");

dojo.declare("nox.apps.directory.directorymanagerws.Directory",
             [ nox.apps.coreui.coreui._NamedEntity ], {
    principal_types : ["user", "host", "switch", "location"],
    group_types : ["user", "host", "switch", "location","dladdr","nwaddr"],

    constructor: function (kwarg) {
        dojo.mixin(this.updateTypes, {
            "info": {
                load: dojo.hitch(this, "updateInfo"),
                save: dojo.hitch(this, "storeInfo")
            }
        });

        // translate enabled_principals so that we can more easily query
        // over them within a dojo store
        dojo.forEach(this.principal_types, function (ptype) {
            // special case 'discovered' directory,
            // which should appear read-only to UI.
            if(this._data.name == "discovered") { 
              this._data["enabled_principals"][ptype] = "RO"; 
            }

            if (this._data.enabled_principals[ptype] == "RW") {
                this._data["read_" + ptype + "_enabled" ] = true;
                this._data["write_" + ptype + "_enabled" ] = true;
            } else if (this._data.enabled_principals[ptype] == "RO") {
                this._data["read_" + ptype + "_enabled" ] = true;
                this._data["write_" + ptype + "_enabled" ] = false;
            } else {
                this._data["read_" + ptype + "_enabled" ] = false;
                this._data["write_" + ptype + "_enabled" ] = false;
            }
        }, this);
        
        // same for groups
        dojo.forEach(this.group_types, function (gtype) {
            // special case 'discovered' directory,
            // which should appear read-only to UI.
            if(this._data.name == "discovered") { 
              this._data["enabled_groups"][gtype] = "RO"; 
            }

            if (this._data.enabled_groups[gtype] == "RW") {
                this._data["read_" + gtype + "group_enabled" ] = true;
                this._data["write_" + gtype + "group_enabled" ] = true;
            } else if (this._data.enabled_groups[gtype] == "RO") {
                this._data["read_" + gtype + "group_enabled" ] = true;
                this._data["write_" + gtype + "group_enabled" ] = false;
            } else {
                this._data["read_" + gtype + "group_enabled" ] = false;
                this._data["write_" + gtype + "group_enabled" ] = false;
            }
        }, this);
        delete this._data.enabled_principals;
        delete this._data.enabled_groups;
    },

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/directory/instance/" + this.displayName();
    },

    updateInfo: function (kwarg) {
        return this._xhrGetMixin("info", this.wsv1Path());
    },

    storeInfo: function (kwarg) {
        return this._xhrPutData("info", this.wsv1Path());
    }
});
