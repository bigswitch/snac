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

dojo.provide("nox.ext.apps.coreui.coreui._NamedEntity");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui._UpdatingItem");

dojo.declare("nox.ext.apps.coreui.coreui._NamedEntity", [ nox.ext.apps.coreui.coreui._UpdatingItem ], {

    identityAttributes: [ "name" ],
    labelAttributes: [ "name" ],

    constructor: function(kwarg) {
        // summary: Constructor
        // description:
        //     See the documentation for the constructor for
        //     nox.ext.apps.coreui.coreui.UpdatingEntity for information on
        //     valid keyword parameters.
        //
        //     For this to represent a valid named entity, the initialData
        //     parameter must include a name property with a unique string
        //     for the name.  If it does not, it will effectively be a
        //     "null" object.
        dojo.mixin(this.derivedAttributes, {
            displayName: {
                get: this.displayName,
                hasChanged: this.nameHasChanged
            }
        });
        if (this._data.name == undefined)
            this._data.name = null;
    },

    isNull: function () {
        return this._data.name == null || this._data.name == "";
    },

    nameHasChanged: function (l) {
        return dojo.some(l, "return item.attribute == 'name';");
    },

    displayName: function () {
        return this._data.name;
    },

    check_name: function (name) {
        if (name == ""
            || name.indexOf("#") != -1 
            || name.indexOf(";") != -1 
            || name.indexOf("'") != -1 
            || name.indexOf('"') != -1)
        {
            return false;
        }
        return true;
    }
        
});
