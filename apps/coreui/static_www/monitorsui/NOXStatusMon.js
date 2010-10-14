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

dojo.provide("nox.ext.apps.coreui.monitorsui.NOXStatusMon");

dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");

var updatemgr = null;
var componentStore = null;


function update_component_status() {
    var t = document.createElement("table");
    t.className = "components";
    everything_good = true
    componentStore.fetch({
        query: { name: "*" },
        sort: [ { attribute: "name", descending: true } ],
        onItem: function (item, request) {
            var name = componentStore.getValue(item, "name");
            var version = componentStore.getValue(item, "version");
            var current_state = componentStore.getValue(item, "state");
            var required_state = componentStore.getValue(item, "required_state");
            var msgclass = "successmsg";
            if (current_state != required_state) {
                msgclass = "errormsg";
                everything_good = false;
            }
            var r = t.insertRow(0);

            td = r.insertCell(-1);
            td.className = "current_state";
            td.innerHTML = "<span class='" + msgclass + "'>" + current_state + "</span>";
            
            var td = r.insertCell(-1);
            td.className = "name";
            td.innerHTML = name;
            
            td = r.insertCell(-1);
            td.className = "version";
            td.innerHTML = version;
            
            td = r.insertCell(-1);
            td.className = "required_state";
            td.innerHTML = required_state;
        },
        onComplete: function (items, request) {
            var d = dojo.byId("component-data");
            nox.ext.apps.coreui.coreui.base.replace_elem_child_id(d, "components-table", t);
            var s = dojo.byId("overall_status_field")
            if (everything_good == true)
                s.innerHTML = "<span class='successmsg'>Good</span>";
            else
                s.innerHTML = "<span class='errormsg'>Bad</span>";
        },
        onError: function (error, request) {
            var r = t.insertRow(0);
            r.innerHTML="<td colspan='4'>Error getting component status: " + error + "</td>";
        }
    });
}


function init_page() {
    if(!dojo.byId("uptime_field")) return;

    updatemgr = nox.ext.apps.coreui.coreui.getUpdateMgr();
    updatemgr.recurrence_period = 10;

    updatemgr.xhrGet({
        url: "/ws.v1/nox/components",
        load: function (response, ioArgs) {
            componentStore = new dojo.data.ItemFileReadStore({data: response});
            update_component_status();
        },
        error: nox.ext.apps.coreui.coreui.UpdateErrorHandler.create(),
        timeout: 30000,
        handleAs: "json",
        recur: true
    });

}

dojo.addOnLoad(init_page);
