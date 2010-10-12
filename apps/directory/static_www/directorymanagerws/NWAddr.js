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

dojo.provide("nox.apps.directory.directorymanagerws.NWAddr");

dojo.require("nox.apps.coreui.coreui._UpdatingItem");

dojo.declare("nox.apps.directory.directorymanagerws.NWAddr", [ nox.apps.coreui.coreui._UpdatingItem ], {

    identityAttributes: [ "ip_str" ],
    labelAttributes: [ "ip_str" ],
    
    constructor: function (data) {
    },

    isValid: function () {
      return true; 
    }

});
