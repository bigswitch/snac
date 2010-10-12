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

dojo.provide("nox.apps.directory.directorymanagerws.NWAddrGroup");

dojo.require("nox.apps.directory.directorymanagerws._PrincipalGroup");
dojo.require("nox.apps.directory.directorymanagerws.NWAddrStore");
dojo.require("nox.apps.directory.directorymanagerws.NWAddrGroupStore");

dojo.declare("nox.apps.directory.directorymanagerws.NWAddrGroup", [ nox.apps.directory.directorymanagerws._PrincipalGroup ], {

    wsv1Path: function () {
        if (this.isNull()) {
            return null;
        }
        return "/ws.v1/group/nwaddr/"
            + encodeURIComponent(this.getValue("directoryName")) + "/"
            + encodeURIComponent(this.getValue("groupName"));
    },

    uiMonitorPath: function () {
        if (this.isNull()) {
            return null;
        }
        return "/Monitors/Groups/NWAddrGroupInfo?name=" + encodeURIComponent(this._data.name);
    },

    parentGroupStore: function (kwarg) {
        return new this.dmws.NWAddrGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/parent"
        }));
    },

    principalMemberStore: function (kwarg) {
        return new this.dmws.NWAddrStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/address"
        }));
    },

    subgroupMemberStore: function (kwarg) {
        return new this.dmws.NWAddrGroupStore(dojo.mixin(kwarg, {
            url: this.wsv1Path() + "/subgroup"
        }));
    }, 
    

    direct_member_path : function (addr_str) {
        return this.wsv1Path() + "/address/"  
            + encodeURIComponent(addr_str);
    },
    
    // override the default modify_direct memeber because we do not
    // need to instantiate a class or test if the underlying memeber exists
    modify_direct_member : function(method, args) {
        var path = this.direct_member_path(args.addr_str);
        var onComplete = this._patch_callback(args); 
        this._do_modify_request(path, method, onComplete);
    } 

});
