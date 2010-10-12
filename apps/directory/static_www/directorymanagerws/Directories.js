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

dojo.provide("nox.apps.directory.directorymanagerws.Directories");

dojo.require("nox.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.apps.directory.directorymanagerws.DirectoryStore"); 


(function () {

    var dmws = nox.apps.directory.directorymanagerws;
    var d = dmws.Directories; 

    principal_types = [ "user", "host", "switch", "location" ];

    // Directory for which mangled names should not be displayed
    d.primary = {
        user: null,
        host: null,
        "switch": null,
        location: null
    };

    d.read_default = {
        user: null,
        host: null,
        "switch": null,
        location: null
    };

    d.num_read = {
        user: 0,
        host: 0,
        "switch": 0,
        location: 0
    };

    d.write_default = {
        user: null,
        host: null,
        "switch": null,
        location: null
    };

    d.num_write = {
        user: 0,
        host: 0,
        "switch": 0,
        location: 0
    };

    function determine_primaries_and_defaults() {
        dojo.forEach(principal_types, function (ptype) {
            d.primary[ptype] = null;
            d.read_default[ptype] = null;
            d.write_default[ptype] = null;
            var a = {
                query: {},
                sort: [ { attribute: "search_order" } ],
                onComplete: function (items) {
                    d.num_read[ptype] = items.length;
                    if (items.length <= 0)
                        return;

                    var name = d.datastore.getValue(items[0], "name");
                    d.read_default[ptype] = name;
                    if (items.length == 1)
                        d.primary[ptype] = name;
                },
                onError: function (error) {
                    console_log("Error occured in nox.apps.directory.directorymanagerws.Directories._determine_primaries_and_defaults() while attempting read fetch.");
                }
            };
            a.query["read_" + ptype + "_enabled"] = true;
            d.datastore.fetch(a);
            a = {
                query: {},
                sort: [ { attribute: "search_order" } ],
                onComplete: function (items) {
                    d.num_write[ptype] = items.length;
                    if (items.length <= 0)
                        return;

                    var name = d.datastore.getValue(items[0], "name");
                    d.write_default[ptype] = name;
                },
                onError: function (error) {
                    console_log("Error occured in nox.apps.directory.directorymanagerws.Directories._determine_primaries_and_defaults() while attempting write fetch.");
                }
            };
            a.query["write_" + ptype + "_enabled"] = true;
            d.datastore.fetch(a);
            dojo.publish("update_completions", ["nox.apps.directory.directorymanagerws.Directories"]);
        });
    };

    d.page_init = function () {
        d.datastore = new dmws.DirectoryStore({
            url : "/ws.v1/directory/instance"
        });
        d.datastore.update({
            onComplete: function () {
                determine_primaries_and_defaults();
                dojo.connect(d.datastore,"onNew",determine_primaries_and_defaults);
                dojo.connect(d.datastore,"onDelete",determine_primaries_and_defaults);
            }
            // TBD: - error handlers need to go here.
        });
    }

})();

dojo.addOnLoad(nox.apps.directory.directorymanagerws.Directories.page_init);
