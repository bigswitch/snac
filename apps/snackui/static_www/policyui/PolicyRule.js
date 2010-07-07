dojo.provide("nox.ext.apps.snackui.policyui.PolicyRule");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");

dojo.declare("nox.ext.apps.snackui.policyui.PolicyRule", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.snackui.policyui", "templates/PolicyRule.html"),
    widgetsInTemplate: true,
    rule: null,

    action_descriptions: {
        allow: function (args) {
            return "allow";
        },
        deny: function (args) {
            return "deny";
        },
        c_action: function (args) {
            return "call C function named '" + args[0] + "'";
        },
        py_action: function (args) {
            return "call Python function named '" + args[0] + "'";
        },
        waypoint: function (args) {
            return "waypoint through " + args.join(" then ");
        },
        compose: function (args) {
            var l = [];
            dojo.forEach(args, function (a) {
                l.push(this._action2desc(a));
            });
            return l.join(" and ");
        }
    },

    predicate_descriptions: {
        "true": function (args, negated) {
            if (negated)
                return [ "never", 0 ];
            else
                return [ "always", 0 ];
        },
        "false": function (args, negated) {
            if (negated)
                return [ "always", 0 ];
            else
                return [ "never", 0 ];
        },
        dlvlan: function (args, negated) {
            if (args[0] == 0xffff) {
                if (negated)
                    return [ "any vlan tag is present", 0 ];
                else
                    return [ "no vlan tag is present", 0 ];
            } else {
                return [ "vlan tag is " + (negated ? "not " : "") + args[0], 0 ];
            }
        },
        dlsrc: function (args, negated) {
            return [ "source MAC is " + (negated ? "not " : "") + args[0], 0 ];
        },
        dldst: function (args, negated) {
            return [ "destination MAC is " + (negated ? "not " : "") + args[0], 0 ];
        },
        dltype: function (args, negated) {
            return [ "ethertype is " + (negated ? "not " : "") + args[0], 0 ];
        },
        nwsrc: function (args, negated) {
            return [ "source IP is " + (negated ? "not " : "") + args[0], 0 ];
        },
        nwdst: function (args, negated) {
            return [ "destination IP is " + (negated ? "not " : "") + args[0], 0 ];
        },
        nwproto: function (args, negated) {
            return [ "IP protocol is " + (negated ? "not " : "") + args[0], 0 ];
        },
        tpsrc: function (args, negated) {
            return [ "source transport port is " + (negated ? "not " : "") + args[0], 0 ];
        },
        tpdst: function (args, negated) {
            return [ "destination transport port is " + (negated ? "not " : "") + args[0], 0 ];
        },
        apsrc: function (args, negated) {
            return [ "source location is " + (negated ? "not " : "") + args[0], 0 ];
        },
        apdst: function (args, negated) {
            return [ "destination location is " + (negated ? "not " : "") + args[0], 0 ];
        },
        hsrc: function (args, negated) {
            return [ "source host is " + (negated ? "not " : "") + args[0], 0 ];
        },
        hdst: function (args, negated) {
            return [ "destination host is " + (negated ? "not " : "") + args[0], 0 ];
        },
        usrc: function (args, negated) {
            return [ "sending user is " + (negated ? "not " : "") + args[0], 0 ];
        },
        udst: function (args, negated) {
            return [ "receiving user is " + (negated ? "not " : "") + args[0], 0 ];
        },
        subnetsrc: function (args, negated) {
            return [ "source IP is " + (negated ? "not " : "") + "in subnet " + args[0], 0 ];
        },
        subnetdst: function (args, negated) {
            return [ "destination IP is " + (negated ? "not " : "") + "in subnet " + args[0], 0 ];
        },
        conn_role: function (args, negated) {
            return [ "direction is " + (negated ? "not " : "") + { 0: "request", 1: "response"}[args[0]], 0 ];
        },
        protocol: function (args, negated) {
            if (args.length == 1) {
                return [ "protocol is " + (negated ? "not " : "") + args[0], 0 ];
            } else if (args.length == 3) {
                return [ this._pred2desc({
                    pred: "and",
                    args: [
                        { pred: "dltype",
                          args: [ args[0] ]
                        },
                        { pred: "nwproto",
                          args: [ args[1] ]
                        },
                        { pred: "tpdst",
                          args: [ args[2] ]
                        }
                    ]}, negated), 1];
            } else {
                return null;
            }
        },
        in_group: function (args, negated) {
            if (typeof args[0] != "object")
                return this._pred2desc({ pred: args[1].toLowerCase(),
                                    args: [ "a member of the group '" + args[0] + "'"]}, negated);
            else
                return this._pred2desc({ pred: args[1].toLowerCase(),
                                    args: [ "in the set [" + args[0] + "]" ] }, negated);
        },
        func: function (args, negated) {
            return [ "C function named '" + args[0] + "' is true", 0 ];
        },
        not: function (args, negated) {
            return [ this._pred2desc(args[0], ! negated), 0 ]
        },
        and: function (args, negated) {
            return this._logical_clause("and", args, negated);
        },
        or: function (args, negated) {
            return this._logical_clause("or", args, negated);
        }
    },

    logical_op_negations: {
        "and" : "or",
        "or" : "and"
    },

    _action2desc: function (a) {
        var f = this.action_descriptions[a.type]
        if (f != null)
            return f(a.args);
        else
            return "unknown action " + a.type;
    },

    _logical_clause: function (op, args, negated) {
        var l = [];
        var max_lvl = 0;
        dojo.forEach(args, function (p) {
            var t = this._pred2desc(p, negated);
            if (t == null)
                return;
            else
                l.push(t[0]);
            if (t[1] > max_lvl)
                max_lvl = t[1]
        });
        if (l.length != args.length)
            return null
        if (max_lvl > 0) {
            if (negated) {
                return [ "(" + l.join(") " + this._logical_op_negations[op] + " (") + ")", max_lvl + 1 ];
            } else {
                return [ "(" + l.join(") " + op + " (") +  ")", max_lvl + 1 ];
            }
        } else {
            if (negated) {
                return [ l.join(" " + this._logical_op_negations[op] + " "), 1 ];
            } else {
                return [ l.join(" " + op + " "), 1 ];
            }
        }
    },

    _pred2desc: function (p, negated) {
        /* Will return null if can't successfully translate. */
        var f = this.predicate_descriptions[p.pred];
        if (f != null)
            return f(p.args, negated);
        else
            return null;
    },

    generated_description: function () {
        a = this._action2desc(this.rule.actions[0]);
        c = this._pred2desc(this.rule.condition, false);
        if (a == null || c == null)
            return null;
        if (c[0] == "always" || c[0] == "never")
            return a + " " + c[0];
        return a + " when " + c[0];
    },

    startup: function () {
        this.inherited("startup", arguments);
        this.title.innerHTML = this.rule.description;
    }
});
