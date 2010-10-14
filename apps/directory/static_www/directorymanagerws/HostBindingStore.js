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

dojo.provide("nox.ext.apps.directory.directorymanagerws.HostBindingStore");

dojo.require("nox.ext.apps.coreui.coreui._UpdatingStore");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.directory.directorymanagerws.HostBinding");
dojo.require("dojo.data.util.simpleFetch");

dojo.declare("nox.ext.apps.directory.directorymanagerws.HostBindingStore", [ nox.ext.apps.coreui.coreui._UpdatingStore ], {

    dmws: nox.ext.apps.directory.directorymanagerws,

    constructor: function (kwarg) {
        // summary: constructor
        //
        // keywordParameters: {hostObj, object}
        //    Host object to which these bindings apply.  This is required
        //    or the store can not function properly.
        this.itemConstructor = this.dmws.HostBinding;
        if (this.hostObj == undefined)
            throw new Error("HostBindingStore must be initialized with the associated host object");
        this.itemParameters["hostObj"] = this.hostObj;
        if (this.url == null)
            this.url = this.hostObj.wsv1Path();
    },

    _unpackData: function (response) {
        return response.netinfos;
    },

    _packData: function () {
        var other_data =  { name: this.hostObj.getValue("name") }; 
        var desc = this.hostObj.getValue("description")
        if(desc != null) 
          other_data["description"] = desc; 
        return this._packDataList({
            name: "netinfos",
            otherData: other_data, 
            packFn: dojo.hitch(this, "_extractSaveData")
        });
    },

    _extractSaveData:  function (i) {
        var r = {};
        dojo.forEach([ "dladdr", "nwaddr", "dpid", "port", "is_router", "is_gateway" ], function (a) {
            var d = this.getValue(i, a);
            if (d != null && d != "")
                r[a] = d;
        }, this);
        return r;
    }

});
//Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.ext.apps.directory.directorymanagerws.HostBindingStore,dojo.data.util.simpleFetch);
