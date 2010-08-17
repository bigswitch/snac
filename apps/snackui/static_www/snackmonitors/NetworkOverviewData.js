dojo.provide("nox.ext.apps.snackui.snackmonitors.NetworkOverviewData");

dojo.require("nox.webapps.coreui.coreui._UpdatingItem");
dojo.require("dojo.number"); 

dojo.declare("nox.ext.apps.snackui.snackmonitors.NetworkOverviewData", [ nox.webapps.coreui.coreui._UpdatingItem ], {

    constructor: function (data) {
        dojo.mixin(this.derivedAttributes, {
            "uptime_str": {
                get: dojo.hitch(this, "uptimeStr"),
                hadChanged: dojo.hitch(this, "basicDataChanged",
                                       [ "uptime" ])
            },
            "switch_cnts" : {
                get: dojo.hitch(this, "entityCnts", "switches")
            },
            "location_cnts" : {
                get: dojo.hitch(this, "entityCnts", "locations")
            },
            "host_cnts" : {
                get: dojo.hitch(this, "entityCnts", "hosts")
            },
            "user_cnts" : {
                get: dojo.hitch(this, "entityCnts", "users")
            },
            "flow_cnts" : {
                get: dojo.hitch(this, "flowCnts")
            }
        });
        dojo.mixin(this.updateTypes, {
            "serverinfo" : {
                load: dojo.hitch(this, "updateServerInfo")
            },
            "serverstat" : {
                load: dojo.hitch(this, "updateServerStat")
            },
            "servercpu" : {
                load: dojo.hitch(this, "updateServerCpu")
            },
            "entitycnts" : {
                load: dojo.hitch(this, "updateEntityCnts")
            },
            "policystats" : {
                load: dojo.hitch(this, "updatePolicyStats")
            }
        });
        // Interval below is not 1 second to desync updates
        setInterval(dojo.hitch(this, "_uptimeUpdateTimer"), 1010);
    },

    _uptimeUpdateTimer: function () {
        var t = this.getValue("uptime");
        if (t != null) {
            // We don't use setValue here because we explicitly don't
            // want to record that a change was made client-side
            this._updateBasicData({ "uptime" : t + 1 });
        }
        this.uptimeUpdated.call(null);
    },

    uptimeUpdated: function () {
        // summary: Extension point to react to changes to uptime
        // implementation:
        //     DO NOT USE THIS FOR ANYTHING!!!  This is a hack to
        //     support updating uptime on the network overview page
        //     only and needs to be removed once ItemInspector is
        //     changed to properly detect updates automatically
        //     based on the onSet extension point.  It WILL go away.
    },

    uptimeStr: function () {
        // This sucks, but javascript's toFixed() rounds
        // so just doing the division isn't quite right.
        var d = this._data.uptime;
        if (d == null)
            return "unknown";
        var SEC_PER_MIN = 60;
        var SEC_PER_HOUR = 60 * SEC_PER_MIN;
        var SEC_PER_DAY = 24 * SEC_PER_HOUR;
        var SEC_PER_YEAR = 365 * SEC_PER_DAY;

        var years = Math.max(0,(d / SEC_PER_YEAR).toFixed() - 1);
        d -= years * SEC_PER_YEAR;
        while(d >= SEC_PER_YEAR) {
            years++;
            d -= SEC_PER_YEAR;
        }
        var days = Math.max(0,(d / SEC_PER_DAY).toFixed() - 1);
        d -= days * SEC_PER_DAY;
        while(d >= SEC_PER_DAY) {
            days++;
            d -= SEC_PER_DAY;
        }
        var hours = Math.max(0,(d / SEC_PER_HOUR).toFixed() - 1);
        d -= hours * SEC_PER_HOUR;
        while(d >= SEC_PER_HOUR) {
            hours++;
            d -= SEC_PER_HOUR;
        }
        var minutes = Math.max(0,(d / SEC_PER_MIN).toFixed() - 1);
        d -= minutes * SEC_PER_MIN;
        while(d >= SEC_PER_MIN) {
            minutes++;
            d -= SEC_PER_MIN;
        }
        var seconds = d.toFixed();
        a = []
        if (years == 1) {
            a.push("1 year");
        } else if (years > 1) {
            a.push(years);
            a.push(years);
        }
        if (days == 0) {
            if (years > 0) {
                a.push("0 days");
            }
        } else if (days == 1) {
            a.push("1 day");
        } else {
            a.push(days);
            a.push("days");
        }
        if (hours == 0) {
            if (years > 0 || days > 0) {
                a.push("0 hours");
            }
        } else if (hours == 1) {
            a.push("1 hour");
        } else {
            a.push(hours);
            a.push("hours");
        }
        if (minutes == 0) {
            if (years > 0 || days > 0 || hours > 0) {
                a.push("0 minutes");
            }
        } else if (minutes == 1) {
            a.push("1 minute");
        } else {
            a.push(minutes);
            a.push("minutes");
        }
        a.push(seconds);
        a.push("seconds");
        return a.join(" ");
    },

    entityCnts: function (entity_type) {
        var s = document.createElement("span");
        dojo.forEach([ "active", "total", "unregistered"], function (ct) {
            var v = (this._data[ct] != null) ? this._data[ct][entity_type] : null;
            var u = "/Monitors/" + entity_type[0].toUpperCase() + entity_type.substr(1);
            if (ct == "active")
              u += "?active=true"; 
            else if (ct == "unregistered")
              u += "?directory=discovered"; 

            if (typeof(v) != "number")
                v = "?"
            else
                v = dojo.number.format(v); 
            
            s.appendChild(coreui.base.createLink(u, v));
            s.appendChild(document.createTextNode(" / "));
        }, this);
        s.removeChild(s.childNodes[s.childNodes.length-1]);
        return s;
    },

    flowCnts: function () {
        var s = document.createElement("span");
        var allowed = this._data["num_allows"];
        var denied = this._data["num_drops"];

        var a_str = typeof(allowed) == "number" ? dojo.number.format(allowed) : "?";
        var d_str = typeof(denied) == "number" ? dojo.number.format(denied) : "?";
        var t_str = "?";
        if (typeof(allowed) == "number" && typeof(denied) == "number") {
            t_str = dojo.number.format(allowed + denied);
        }

        var lbase = "/Monitors/FlowHistory?";
        s.appendChild(coreui.base.createLink(lbase + "allowed=1", a_str));
        s.appendChild(document.createTextNode(" / "));
        s.appendChild(coreui.base.createLink(lbase + "denied=1", d_str));
        s.appendChild(document.createTextNode(" / "));
        s.appendChild(coreui.base.createLink(lbase + "all=1", t_str));

        return s;
    },

    updateServerInfo: function () {
        return this._xhrGetMixin("serverinfo", "/ws.v1/config/nox_config", function (r) {
            for (a in r) {
                r[a] = r[a][0];
            }
            return r;
        });
    },

    updateServerStat: function () {
        return this._xhrGetMixin("servercpu", "/ws.v1/nox/stat");
    },

    updateServerCpu: function () {
        return this._xhrGetMixin("servercpu", "/ws.v1/nox/cpu/stat", function (r) {
            r["cpu-load"] = Math.ceil(r["user"]) + "%";
            return r;
        });
    },

    updateEntityCnts: function () {
        return this._xhrGetMixin("serverinfo", "/ws.v1/bindings/entity_counts");
    },

    updatePolicyStats: function () {
        return this._xhrGetMixin("serverinfo", "/ws.v1/policy/stats");
    }

});
