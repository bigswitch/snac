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

dojo.provide("nox.apps.directory.directorymanagerws.HostInterfaceStore");

dojo.require("nox.apps.coreui.coreui._UpdatingStore");
dojo.require("nox.apps.directory.directorymanagerws.HostInterface");
dojo.require("dojo.data.util.simpleFetch");

dojo.declare("nox.apps.directory.directorymanagerws.HostInterfaceStore", [ nox.apps.coreui.coreui._UpdatingStore ], {

    dmws: nox.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        // summary: constructor
        //
        // keywordParameters: {hostObj, object}
        //    Host object to which these bindings apply.  This is required
        //    or the store can not function properly.
        this.itemConstructor = this.dmws.HostInterface;
        if (this.hostObj == undefined)
            throw new Error("HostInterfaceStore must be initialized with host object.");
        this.itemParameters["hostObj"] = this.hostObj;
        if (this.url == null)
            this.url = this.hostObj.wsv1Path() + "active/interface";
    },

    _unpackData: function (r) {
        return dojo.map(r, "return { name: item };");
    }

});

//Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.apps.directory.directorymanagerws.HostInterfaceStore,
            dojo.data.util.simpleFetch);
