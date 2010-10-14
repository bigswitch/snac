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

dojo.provide("nox.ext.apps.coreui.coreui.base");

(function () {
    var b = nox.ext.apps.coreui.coreui.base;

    dojo.addOnLoad(function () { dojo.query("body").style("visibility", "visible"); });

    // TBD: Get rid of swap_elem.  (replace w/dojo.place?)
    b.swap_elem = function(name, new_value) {
        // NOTE: this often doesn't work with dojo widgets since they
        //       re-write their HTML and the parentNode thus may not be
        //       what you think it is...
        var p = dojo.byId(name).parentNode;
        b.replace_elem_child_id(p, name, new_value);
    }

    b.replace_elem_child_id = function(e, child_id, new_e) {
	    var c = dojo.query("> #" + child_id, e)[0];
	    if (c) {
            c.id = "";
		    new_e.id = child_id;
		    e.replaceChild(new_e, c);
        }
        return c;
    }

    function unset_all_pagetoolbar_buttons () {
	    var toolbar = dojo.byId("pagetoolbar");
	    if (toolbar) {
		    dojo.query("button", toolbar).forEach(
                function (button) {
                    dijit.byId(button.id).attr("checked", false);
                });
        }
    }

    b.set_pagetoolbar_button = function(name) {
        unset_all_pagetoolbar_buttons();
        var w = dijit.byId(name + "Button")
        if (w != null)
            w.attr("checked", true);
    }

    b.highlight_current_section = function() {
	    var sec = document.location.pathname.split("/")[1]
        b.set_pagetoolbar_button(sec);
    }

    b.highlight_current_sidebar_link = function() {
	    dojo.query("div#lsidebar li > a").forEach(function(a){
            var li = a.parentNode;
            var visiting = encodeURIComponent(document.location.pathname + 
                                              document.location.search); 
            var link = encodeURIComponent(a.pathname + a.search); 
            dojo.toggleClass(li, "active", visiting.match("^" + link) != null);
        });
    }

    b.update_status_msg = function(msg, msg_class) {
        var status_node = dojo.byId("statusMsgArea");
        if (status_node != undefined) {
		    dojo.style(status_node, "opacity", 1);
            status_node.innerHTML = "<span class='" + msg_class + "'>" + msg + "</span>";
        }
    }

    b.update_status_msg_fadeout = function(msg, msg_class, duration) {
        b.update_status_msg(msg, msg_class);
        var status_node = dojo.byId("statusMsgArea");
        if (status_node != undefined) {
            var anim = dojo.fadeOut({node: status_node,
                "duration": duration});
            anim.play();
        }
    }

    b.changeHighlightFn = function(node) {
        return dojo.animateProperty({
            node: node,
            duration: 8000,
            properties: {
                backgroundColor: {
                    start: "#fffec9",
                    end: "#ffffe9"
                }
            },
            onEnd: function () {
                dojo.style(node, "backgroundColor", "");
            }
        })
    }

    b.in_array = function(v, a) {
        for (var i = 0; i < a.length; i++) {
            if (a[i] == v)
                return true;
        }
        return false;
    }

    b.diffobj = function(old_item, new_item, old_visited, new_visited) {
        // Deep compare two objects with cycle detection.

        //console.log("diffobj(", old_item, ", ", new_item, ", ", old_visited, ", ", new_visited, ")");

        var old_type = typeof old_item;
        var new_type = typeof new_item;
        if (! (old_type == "object" && new_type == "object"))
            throw Error("diffobj only works on objects");

        if (old_visited == null)
            old_visited = [ ];
        if (new_visited == null)
            new_visited = [ ];
        old_visited.push(old_item);
        new_visited.push(new_item);
        var different = [];
        for (var p in old_item) {
            if (! old_item.hasOwnProperty(p)) {
                // ignore stuff in the prototype object.
                continue;
            }
            if (! new_item.hasOwnProperty(p)) {
                different.push([p]);
                continue;
            }
            old_type = typeof old_item[p];
            new_type = typeof new_item[p];
            if ((old_type == "object" && new_type == "object")
                || (old_type == "array" && new_type == "array")) {
                if ((old_item[p] == null && new_item[p] != null)
                    || (old_item[p] != null && new_item[p] == null)) {
                    different.push([p]);
                    continue;
                }
                var visited_old = b.in_array(old_item[p], old_visited);
                var visited_new = b.in_array(new_item[p], new_visited);
                if (visited_old && visited_new) {
                    continue;  // The've already been compared.
                } else if (! (visited_old || visited_new)) {
                    var l = b.diffobj(old_item[p], new_item[p], old_visited, new_visited);
                    for (var i = 0; i < l.length; i++) {
                        l[i].unshift(p);
                    }
                    different = different.concat(l);
                } else {
                    // One already visited, the other not, there must
                    // be a difference...  (I think....)
                    different.push([p]);
                }
            } else if (new_item[p] != old_item[p]) {
                different.push([p]);
            }
        }
        for (p in new_item) {
            if ((! new_item.hasOwnProperty(p)) || old_item.hasOwnProperty(p))
                continue;  // Already handled in previous loop
            different.push([p]);p
        }
        return different;
    }

    b.equivDomTrees = function(n1, n2) {
        // Compares 2 dom trees to see if they will appear the same to the user.
        if (n1 != null && n2 != null
            && n1.nodeType == n2.nodeType
            && n1.nodeName == n2.nodeName) {
            if (n1.nodeType === /* Node.ELEMENT_NODE */ 1) {
                if (n1.attributes.length == n2.attributes.length
                    && n1.childNodes.length == n2.childNodes.length) {
                    for (var i = 0; i < n1.attributes.length; i++) {
                        if (! b.equivDomTrees(n1.attributes[i], n2.attributes[i]))
                            return false;
                    }
                    for (i = 0; i < n1.childNodes.length; i++) {
                        if (! b.equivDomTrees(n1.childNodes[i], n2.childNodes[i]))
                            return false;
                    }
                } else {
                    return false;
                }
            } else if (n1.nodeType === /* Node.TEXT_NODE */ 3
                       || n1.nodeType === /* Node.CDATA_SECTION_NODE */ 4) {
                return n1.data == n2.data;
            } else if (n1.nodeType === /* Node.ATTRIBUTE_NODE */ 2) {
                return n1.value == n2.value;
            }
            return true;
        } else {
            return false;
        }
    }

    b.createLink = function(href, text) {
        var a = document.createElement("a");
        a.href = href;
        a.appendChild(document.createTextNode(text));
        return a;
    }

    dojo.global.console_log = function(/* ... */) {
        // This will log to the firebug console (or the dojo debugOn console)
        // if it is present and will otherwise be silent with no javascript
        // warning, etc.  It should only be used in cases where it is
        // desirable to ensure that the logs stay in place long term.  Typically
        // this means it should only be used to indicate where an API is being
        // misused.
        if (console != null && console.log != null)
            console.log.apply(console, arguments);
    }

    b.update_page_title = function (str, fragment) {
        if (fragment == null)
            fragment = document.createTextNode(str);
        document.title = dojo.byId("network_name").value 
                                    + " Network " + str; 
        var n = dojo.byId("page-title");
        dojo.query(n).empty();
        n.appendChild(fragment);
    }

    b.set_nav_title = function (navlist) {
        if (navlist == null || navlist.length == 0)
            return;

        var text = "";
        var fragment = document.createDocumentFragment();
        for (var i = 0; i < navlist.length - 1; i++) {
            var o = navlist[i]
            if (o.title_text != null) {
                if (o.title_text != "")
                    text = text + o.title_text + " ";
            } else {
                text = text + o.nav_text + " ";
            }
            if (o.nav_url != null) {
                var n = document.createElement("a");
                n.href = o.nav_url
                n.appendChild(document.createTextNode(o.nav_text));
            } else {
                var n = document.createTextNode(o.nav_text);
            }
            fragment.appendChild(n);
            fragment.appendChild(document.createTextNode(" << "));
        }
        var o = navlist[navlist.length - 1];
        if (o.title_text != null)
            text = text + o.title_text;
        else
            text = text + o.nav_text;
        fragment.appendChild(document.createTextNode(o.nav_text));
        b.update_page_title(text, fragment);
    }
    
    // found online at http://www.netlobo.com/url_query_string_javascript.html
    b.get_url_param = function( name ){
        name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
        var regexS = "[\\?&]"+name+"=([^&#]*)";
        var regex = new RegExp( regexS );
        var results = regex.exec( window.location.href );
        if( results == null )
          return "";
        else
          return results[1];
    }
 
    b.remove_all_children = function(parentDomNode) { 
        while (parentDomNode.hasChildNodes()) {
          parentDomNode.removeChild(parentDomNode.childNodes[0]);
        }
    } 

})();
