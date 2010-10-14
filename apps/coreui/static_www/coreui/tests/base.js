dojo.provide("nox.ext.apps.coreui.coreui.tests.base");

dojo.require("doh.runner");
dojo.require("nox.ext.apps.coreui.coreui.base");

var b = nox.ext.apps.coreui.coreui.b;

doh.registerGroup("nox.ext.apps.coreui.coreui.tests.base.diffobj", [
    function invalid_arguments() {
        var exception_occurred = false;
        try {
            var r = b.diffobj(1, 2);
        } catch (e) {
            exception_occurred = true;
        }
        doh.assertTrue(exception_occurred);
    },
    function null_objects() {
        var r = b.diffobj({}, {});
        doh.assertEqual(r.length, 0);
    },
    function single_level_and_null_objects() {
        var r = b.diffobj({ "foo" : "bar" }, { });
        doh.assertEqual(r.length, 1);
        doh.assertEqual(r[0], "foo");
    },
    function null_and_single_level_objects() {
        var r = b.diffobj({}, { "foo" : "bar" });
        doh.assertEqual(r.length, 1);
        doh.assertEqual(r[0], "foo");
    },
    function single_level_same() {
        var r = b.diffobj({ "foo" : "bar" }, { "foo" : "bar" });
        doh.assertEqual(r.length, 0);
    },
    function single_level_different_values() {
        var r = b.diffobj({ "foo" : "bar" }, { "foo" : "baz" });
        doh.assertEqual(r.length, 1);
        doh.assertEqual(r[0], "foo");
    },
    function single_level_different_values1() {
        var r = b.diffobj({ "foo" : "bar" }, { "foo" : { "bar" : "baz"} });
        doh.assertEqual(r.length, 1);
        doh.assertEqual(r[0], "foo");
    },
    function single_level_different_propreties() {
        var r = b.diffobj({ "foo" : "baz" }, { "bar" : "baz" });
        doh.assertEqual(r.length, 2);
        r = dojo.map(r, function (l) { return l.join("."); });
        doh.assertTrue(b.in_array("foo", r));
        doh.assertTrue(b.in_array("bar", r));
    },
    function multi_level_same() {
        var r = b.diffobj(
            { "foo" : { "bar" : "baz" }},
            { "foo" : { "bar" : "baz" }});
        doh.assertEqual(r.length, 0);
    },
    function multi_level_different_properties_deep() {
        var r = b.diffobj(
            { "foo" : { "bar" : "baz" }},
            { "foo" : { "baz" : "bar" }});
        doh.assertEqual(r.length, 2);
        r = dojo.map(r, function (l) { return l.join("."); });
        doh.assertTrue(b.in_array("foo.bar", r));
        doh.assertTrue(b.in_array("foo.baz", r));
    },
    function multi_level_different_values_deep() {
        var r = b.diffobj(
            { "foo" : { "bar" : "baz" }},
            { "foo" : { "bar" : "zab" }});
        doh.assertEqual(r.length, 1);
        doh.assertEqual(r[0].join("."), "foo.bar");
    },
    function multi_level_complex() {
        var r = b.diffobj(
            { 1 : 2,
              3 : 4,
              10: 50,
              "foo" : null,
              "x" : { "y" : "z" },
              "y" : { "x" : "z" },
              "z" : { "y" : "x" },
              "a0" : [ 1, 2, 3, 4 ],
              "a1" : [ 1, 2, 3, 4 ],
              "a2" : [ 1, 2, 3]
            },
            { 1 : 2,
              3 : 5,
              "baz" : null,
              "x" : { },
              "y" : { "x" : "z" },
              "z" : null,
              "a0" : [ 1, 2, 3, 4 ],
              "a1" : [ 4, 3, 2, 1 ],
              "a2" : [ 3, 2, 1, 4 ],
              "bar" : "bop"
            });
        doh.assertEqual(r.length,14);
        r = dojo.map(r, function (l) { return l.join("."); });
        doh.assertTrue(b.in_array(3, r));
        doh.assertTrue(b.in_array(10, r));
        doh.assertTrue(b.in_array("foo", r));
        doh.assertTrue(b.in_array("x.y", r));
        doh.assertTrue(b.in_array("z", r));
        doh.assertTrue(b.in_array("a1.0", r));
        doh.assertTrue(b.in_array("a1.1", r));
        doh.assertTrue(b.in_array("a1.2", r));
        doh.assertTrue(b.in_array("a1.3", r));
        doh.assertTrue(b.in_array("a2.0", r));
        doh.assertTrue(b.in_array("a2.2", r));
        doh.assertTrue(b.in_array("a2.3", r));
        doh.assertTrue(b.in_array("bar", r));
        doh.assertTrue(b.in_array("baz", r));
    }
    // TBD: Need to test loops, shared subobjects, etc.
]);

doh.registerGroup("nox.ext.apps.coreui.coreui.tests.base.equivDomTrees", [
    function one_or_more_null_nodes() {
        var r = b.equivDomTrees(null, null);
        doh.assertFalse(r);
        var r = b.equivDomTrees(document.createTextNode("foo"), null);
        doh.assertFalse(r);
        var r = b.equivDomTrees(null, document.createTextNode("foo"));
        doh.assertFalse(r);
    },
    function same_text_nodes() {
        var r = b.equivDomTrees(document.createTextNode("foo"), document.createTextNode("foo"));
        doh.assertTrue(r);
    },
    function empty_span_nodes() {
        var r = b.equivDomTrees(document.createElement("span"), document.createElement("span"));
        doh.assertTrue(r);
    },
    function span_nodes_one_with_text_subnode() {
        var s = document.createElement("span");
        s.appendChild(document.createTextNode("foo"));
        var r = b.equivDomTrees(s, document.createElement("span"));
        doh.assertFalse(r);
        var r = b.equivDomTrees(document.createElement("span"), s);
        doh.assertFalse(r);
    },
    function span_nodes_one_with_class() {
        var s = document.createElement("span");
        s.className="myclass";
        var r = b.equivDomTrees(s, document.createElement("span"));
        doh.assertFalse(r);
        var r = b.equivDomTrees(document.createElement("span"), s);
        doh.assertFalse(r);
    },
    function span_nodes_with_same_text_subnode() {
        var s1 = document.createElement("span");
        s1.appendChild(document.createTextNode("foo"));
        var s2 = document.createElement("span");
        s2.appendChild(document.createTextNode("foo"));
        var r = b.equivDomTrees(s1, s2);
        doh.assertTrue(r);
        var r = b.equivDomTrees(s2, s1);
        doh.assertTrue(r);
    },
    function span_nodes_with_different_text_subnode() {
        var s1 = document.createElement("span");
        s1.appendChild(document.createTextNode("foo"));
        var s2 = document.createElement("span");
        s2.appendChild(document.createTextNode("bar"));
        var r = b.equivDomTrees(s1, s2);
        doh.assertFalse(r);
        var r = b.equivDomTrees(s2, s1);
        doh.assertFalse(r);
    },
    function span_nodes_with_different_text_subnodes_one_with_class() {
        var s1 = document.createElement("span");
        s1.appendChild(document.createTextNode("foo"));
        s1.className = "myclass";
        var s2 = document.createElement("span");
        s2.appendChild(document.createTextNode("bar"));
        var r = b.equivDomTrees(s1, s2);
        doh.assertFalse(r);
        var r = b.equivDomTrees(s2, s1);
        doh.assertFalse(r);
    }
]);
