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

/* Mix-in class to implement sorting for updating lists. */

dojo.provide("nox.ext.apps.coreui.coreui._ItemSort");

dojo.declare("nox.ext.apps.coreui.coreui._ItemSort", [ ], {

    _get_item_dom_node: function (item) {
        throw Error("Method must be implemented by subclass");
    },

    _get_dom_node_item: function (node) {
        throw Error("Method must be implemented by subclass");
    },

    _get_num_item_dom_nodes: function () {
        throw Error("Method must be implemented by subclass");
    },

    _get_item_dom_node_idx: function (idx) {
        throw Error("Method must be implemented by subclass");
    },

    _get_store: function () {
        throw Error("Method must be implemented by subclass");
    },

    _cmp_attr: function (item1, item2) {
        if(item2 == null) 
          return -1; 
        if(item1 == null) 
            throw "first item in _cmp_attr should not be null"; 
        var store = this._get_store();
        for (i = 0; i < this.sort.attr.length; i++) {
            var v1 = store.getValue(item1, this.sort.attr[i]);
            var v2 = store.getValue(item2, this.sort.attr[i]);
            if (v1 < v2)
                return -1;
            else if (v1 > v2)
                return 1;
        }
        return 0
    },

    _insert_helper: function (item) {
        var n = null;
        var m = (this.sort.decreasing == true) ? -1 : 1;
        var lower = 0;
        var upper = this._get_num_item_dom_nodes();
        while (lower != upper) {
            var i = Math.floor((upper - lower)/2);
            n = this._get_item_dom_node_idx(lower + i);
            var z = this._get_dom_node_item(n); 
            var r = m * this.sort.cmp.call(this, item, z);
            if (r < 0) {
                // Item should be inserted earlier
                upper = lower + i;
            } else if (r > 0) {
                // Item should be inserted later
                n = this._get_item_dom_node_idx([lower + i + 1]);
                lower = lower + i + 1;
            } else {
                // Found equivalent item
                break;
            }
        }

        // Append at end of list of equivalent items
        while (n != null && this.sort.cmp.call(this, item, this._get_dom_node_item(n)) == 0)
            n = n.nextSibling;
        return n;
    },

    _node_to_insert_before: function (item) {
        if (this.sort == null || this.sort == "") {
            // If not sorting, append to end of list
            return null;
        } else {
            // Identify insertion point by binary search
            return this._insert_helper(item);
        }
    },

    postMixInProperties: function () {
        if (this.sort != null) {
            if (this.sort.cmp == null)
                this.sort.cmp = this._cmp_attr;
            if (typeof(this.sort.attr) == "string")
                this.sort.attr = [ this.sort.attr ];
        }
    }


});
