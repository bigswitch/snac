/*
 Copyright 2008 (C) Nicira,

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
dojo.provide("nox.ext.apps.user_event_log.networkevents.NetEventsFormatter");

dojo.require("nox.ext.apps.directory.directorymanagerws.User"); 
dojo.require("nox.ext.apps.directory.directorymanagerws.Switch"); 
dojo.require("nox.ext.apps.directory.directorymanagerws.Host"); 
dojo.require("nox.ext.apps.directory.directorymanagerws.HostGroup"); 
dojo.require("nox.ext.apps.directory.directorymanagerws.UserGroup"); 
dojo.require("nox.ext.apps.directory.directorymanagerws.LocationGroup"); 

// switch groups are not implemented yet
//dojo.require("nox.apps.directory.directorymanagerws.SwitchGroup");

(function() {

    var nef = nox.ext.apps.user_event_log.networkevents.NetEventsFormatter;
    var dmws = nox.ext.apps.directory.directorymanagerws;

    var objConstructors = {
        "switch" : dmws.Switch,
        "location" : null,  // Has to be handled as a special case...
        "host" : dmws.Host,
        "user" : dmws.User,
        "switch group": dmws.SwitchGroup,
        "location group": dmws.LocationGroup,
        "host group": dmws.HostGroup,
        "user group": dmws.UserGroup
    };

    // get text when principal list contains a single entry
    function single_text(ptype_str, name) {
        if (name == "<unknown>")
            return "unknown " + ptype_str;
        return ptype_str + " " + get_link(ptype_str,name);
    }

    // get text when principal list contains multiple entries
    function multiple_text(ptype_str, name_list) {
        var unknown_cnt = 0;
        var l = [];
        dojo.forEach(name_list, function (n) {
            if (n == "<unknown>")
                l.push("unknown" + unknown_cnt++);
            else
                l.push(get_link(ptype_str,n));
        });
        if (ptype_str == "switch")
            return ptype_str + "es " + l.join(", ");
        else
            return ptype_str + "s " + l.join(", ");
    }

    function get_link(ptype_str, principal_name) {
        var principal_obj = null;
        var c = objConstructors[ptype_str];
        if (ptype_str == "location") {
            return location_link(principal_name);
        } else if (c) {
            var o = new c({initialData: { name: principal_name }});
            return o.uiMonitorLinkText(true);
        } else {
            console_log("unknown principal type '" + ptype_str
                        + " for name '" + principal_name + "' in get_link");
            return principal_name;
        }
    }

    function fix_backslash (s) {
        return s.replace(/\\\\/g, "\\");
    }

    // location stuff is special-cased because we want to link to
    // switch port page.

    function location_link(location) {
        var loc_info = split_location(location)
        return "<a href='/Monitors/Switches/SwitchPortInfo?switch=" + encodeURIComponent(loc_info[1]) + "&port=" + encodeURIComponent(loc_info[2]) + "'>" + loc_info[0] + "</a>"
    }

    function split_location (location) {
        var pieces = location.split(/(\\*)#/);
        var result = [];
        result.push(fix_backslash(pieces[0]));
        for (var i = 1; i < pieces.length; i += 2) {
            var sep = pieces[i];
            var len = pieces[i].length;
            if (len > 0)
                result.push(result.pop() + fix_backslash(sep.substring(0, len-1)));
            if (len & 1 == 1) {
                // This is an invalid split point
                result.push(result.pop() + "#" + fix_backslash(pieces[i+1]));
            } else {
                result.push(fix_backslash(pieces[i+1]));
            }
        }
        return result;
    }


    function replace_template(match, type, value) {
        var single_types = ["user","host","location","switch",
            "user group", "host group", "location group",
            "switch group"];
        var multiple_types = dojo.map(single_types,
            function(t) { return t + "s";});

        if (type == "switches") { // lame special case
            return multiple_text("switch",value.split(","));
        } else if (dojo.indexOf(single_types,type) != -1) {
            return single_text(type,value);
        } else if (dojo.indexOf(multiple_types,type) != -1) {
            var type_str = type.substring(0,type.length - 1);
            return multiple_text(type_str, value.split(","));
        } else {
            return match;
        }
    }

    nef.format_msg = function(m) {
        return m.replace(/{([^\|]*)\|([^}]*)}/g, replace_template);
    }

})();
