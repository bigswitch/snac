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

dojo.provide("nox.apps.directory.directorymanagerws.User");

dojo.require("nox.apps.coreui.coreui.base");
dojo.require("nox.apps.directory.directorymanagerws.Directories");
dojo.require("nox.apps.directory.directorymanagerws._Principal");
dojo.require("nox.apps.directory.directorymanagerws._PrincipalStore");

var AUTH_SIMPLE = "simple_auth";

dojo.declare("nox.apps.directory.directorymanagerws.User", [ nox.apps.directory.directorymanagerws._Principal ], {

    constructor: function (kwarg) {
        dojo.mixin(this.updateTypes, {
            "info" : {
                load: dojo.hitch(this, "updateInfo")
            },
            "cred" : {
                load: dojo.hitch(this, "updateCred")
            }
        });
        dojo.mixin(this.derivedAttributes, {
            "passwd_set" : {
                get: dojo.hitch(this, "passwd_set")
            }
        });
    },

    wsv1Path: function () {
        if (this.isNull())
            return null;
        return "/ws.v1/user/"
            + encodeURIComponent(this.directoryName()) + "/"
            + encodeURIComponent(this.principalName());
    },

    uiMonitorPath: function () {
        if (this.isNull())
            return null;
        return "/Monitors/Users/UserInfo?name=" + encodeURIComponent(this._data.name);
    },

    passwd_set: function () {
        if (this._data.cred != null && this._data.cred[AUTH_SIMPLE] != null) {
            return "Yes";
        }
        return "No";
    },
        
    updateInfo: function (kwarg) {
        return this._xhrGetMixin("info", this.wsv1Path());
    },

    updateCred: function (kwarg) {
        return this._xhrGetMixin("cred", this.wsv1Path() + "/cred",
                                 function (response) {
                                     return { "cred": response };
                                 });
    },

    hostStore: function (kwarg) {
        return new this.dmws.HostStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/active/host",
            "userObj": this
        }));
    },

    groupStore: function (kwarg) {
        return new this.dmws.UserGroupStore(dojo.mixin(kwarg, {
            "url": this.wsv1Path() + "/group",
            "userObj": this
        }));
    },

    save: function (kwarg) {
        var uinfo = { name: this._data.name };
        if (this._data.user_id != null) {
            uinfo["user_id"] = this._data.user_id;
        }
        if (this._data.user_real_name != null) {
            uinfo["user_real_name"] = this._data.user_real_name;
        }
        if (this._data.description != null) {
            uinfo["description"] = this._data.description;
        }
        if (this._data.phone != null) {
            uinfo["phone"] = this._data.phone;
        }
        if (this._data.user_email != null) {
            uinfo["user_email"] = this._data.user_email;
        }
        if (this._data.location != null) {
            uinfo["location"] = this._data.location;
        }

        var errHandlers;
        if (kwarg != null &&  kwarg["errorHandlers"] != null) {
            errHandlers = kwarg["errorHandlers"];
        } else {
            errHandlers = {
                400: function(response, ioArgs, item, itemType) {
                    nox.apps.coreui.coreui.UpdateErrorHandler.showError(
                        response.responseText, { header_msg : "Save failed" });
                }
            };
        }
        
        nox.apps.coreui.coreui.getUpdateMgr().rawXhrPut({
            url: this.wsv1Path(),
            headers: { "content-type": "application/json" },
            putData: dojo.toJson(uinfo),
            timeout: 30000,
            errorHandlers: errHandlers
        });
    },

    saveCred: function(pwd, kwarg) {
        var errHandlers;
        if (kwarg != null &&  kwarg["errorHandlers"] != null) {
            errHandlers = kwarg["errorHandlers"];
        } else {
            errHandlers = {
                400: function(response, ioArgs, item, itemType) {
                    nox.apps.coreui.coreui.UpdateErrorHandler.showError(response.responseText,
                     { auto_show : true, header_msg : "Save credentials failed." });
                }
            };
        }

        var cred = {};
        if (pwd != null) {
            cred[AUTH_SIMPLE] = [{ password: pwd }];
        }
                
        nox.apps.coreui.coreui.getUpdateMgr().rawXhrPut({
            url: this.wsv1Path() + "/cred",
            headers: { "content-type": "application/json" },
            putData: dojo.toJson(cred),
            timeout: 30000,
            errorHandlers: errHandlers
        });
        this._updateBasicData({"cred": cred });
    }
});
