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

dojo.provide("nox.ext.apps.coreui.coreui.ItemList");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("nox.ext.apps.coreui.coreui._ItemSort");

dojo.require("dojox.dtl.Context");

dojo.declare("nox.ext.apps.coreui.coreui.ItemList", [ dijit._Widget, dijit._Templated, nox.ext.apps.coreui.coreui._ItemSort ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ItemList.html"),
	DTLTemplatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ItemListDTL.html"),
	editableDTLTemplatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/EditableItemListDTL.html"),
	deleteIcon: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "images/itemClose.png"),

    widgetsInTemplate: false,
    store: null,
    labelAttr: null,
    get: null,
    sort: null,
    ignoreNullValues: false,
    delimiter : ", ",
    editable: false, 

    constructor: function (kwarg) {
        this.id_base = dijit.getUniqueId("ItemList");
    },

    _get_item_id: function (item) {
        return this.id_base + '-' + this.store.getIdentity(item);
    },

    _get_item_value: function (item) {
        if (this.get != null)
            var value = this.get(item);
        else if (this.labelAttr != null && this.labelAttr != "")
            value = this.store.getValue(item, this.labelAttr, null);
        else
            value = this.store.getLabel(item);

        if (value == null)
            value = document.createTextNode((this.ignoreNullValues) ? "" : "?");
        else if (typeof(value) == "string")
            value = document.createTextNode(value);
        else if (typeof(value) == "number")
            value = document.createTextNode(String(value));

        return value;
    },

    _create_span: function (item) {
        var s = document.createElement("span");
        s.id = this._get_item_id(item);
        s.appendChild(this._get_item_value(item));
        return s;
    },

    _get_item_dom_node: function (item) {
        return dojo.byId(this._get_item_id(item));
    },

    _get_dom_node_item: function (node) {
        var id = node.id.substr(this.id_base.length + 1); 
        return this.store.fetchItemByIdentity(id)
    },

    _get_num_item_dom_nodes: function () {
        return this.item_list.childNodes.length;
    },

    _get_item_dom_node_idx: function (idx) {
        return this.item_list.childNodes[idx];
    },

    _get_store: function () {
        return this.store;
    },

    _reset_delimiters: function() {
                         
        for(var i = 0; i < this._get_num_item_dom_nodes(); i++) { 
          var node = this._get_item_dom_node_idx(i);
          for(j = 0; j < node.childNodes.length; j++) { 
            var cnode = node.childNodes[j];
            if(cnode.id == this.id_base + "_delimiter")
              node.removeChild(cnode); 
          } 
        }
        var b = this._get_num_item_dom_nodes() - 1; 
        for(z = 0; z < b; z++) {
            var node = this._get_item_dom_node_idx(z);
            var cnode = document.createElement("span");
            cnode.id = this.id_base + "_delimiter";
            cnode.appendChild(document.createTextNode(this.delimiter));
            node.appendChild(cnode); 
        } 

    },

    _onNewItem: function (item) {
        this._refresh();
        //var n = this._node_to_insert_before(item);
        //var s = this._create_span(item);
        //dojo.addClass(s, "item-list-item-span");
        //this.item_list.insertBefore(s, n);
        //this._reset_delimiters(); 
    },

    // renames should come as add delete, so we should be ok ignoring this
    _onItemChange: function (item, attribute, oldValue, newValue) {},

    _onDeleteItem: function (item) {
        this._refresh();
        //var n = this._get_item_dom_node(item);
        //this.item_list.removeChild(n);
        //this._reset_delimiters(); 
    },

    _refresh: function () {
        this.store.fetch({
            query: {},
            onComplete: dojo.hitch(this, function (items) {
				var template_path = this.editable ? this.editableDTLTemplatePath : 
                                        this.DTLTemplatePath; 
				var template = new dojox.dtl.Template(template_path);
        var context = new dojox.dtl.Context({
					items: items,
					iconURL: this.deleteIcon
				});
				this.domNode.innerHTML = template.render(context);

                                var i = 0;
                                var store = this.store;
                                var onDelete = this.onDelete;

				dojo.query("img", this.domNode).forEach(
                                    function(node) {
                                        var item = items[i];
                                        i++;
                                        dojo.connect(node, "onclick",
                                                     function() {
                                                         onDelete(item);
                                                     });
                                    });
            })
        });
    },

    postCreate: function () {
        dojo.connect(this.store, "onNew", this, "_onNewItem");
        dojo.connect(this.store, "onSet", this, "_onItemChange");
        dojo.connect(this.store, "onDelete", this, "_onDeleteItem");

        this._refresh();
    },

    /* Notifications */
    onDelete: function (deletedItem) {
    }
})
