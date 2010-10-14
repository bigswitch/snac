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

dojo.provide("nox.ext.apps.coreui.coreui.ItemTable");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.Menu");
dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui._ItemSort");

dojo.declare("nox.ext.apps.coreui.coreui.ItemTable", [ dijit._Widget, dijit._Templated, nox.ext.apps.coreui.coreui._ItemSort ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ItemTable.html"),
    widgetsInTemplate: false,
    store: null,
    model: null,
    ignoreNull: false,
    changeAnimFn: null,
    contextMenu: null,
    displayValidity: false,
    editAllowed: null,

    constructor: function (kwarg) {
        this.id_base = dijit.getUniqueId("ItemTable");
        this._editCell = null;
        this._editInfo = null;
        this._editItem = null;
        this._editor = null;
        this._editValue = null;
        this._mouse2down = false;
        this._menus = {};

    },

    _get_item_id: function (item) {
        return this.id_base + "-" + this.store.getIdentity(item);
    },

    _get_cell_id: function (item, column) {
        return this._get_item_id(item) + "-" + column;
    },

    _get_item_dom_node: function (item) {
        return dojo.byId(this._get_item_id(item));
    },

    _get_dom_node_item: function (node) {
        return this.store.fetchItemByIdentity(node.id.substr(this.id_base.length + 1));
    },

    _get_num_item_dom_nodes: function () {
        return this.itemrows.rows.length;
    },

    _get_item_dom_node_idx: function (idx) {
        return this.itemrows.rows[idx];
    },

    _get_store: function () {
        return this.store;
    },

    _item_column_value: function (item, column_def) {
        if (column_def.get != null)
            var value = column_def.get(item);
        else if (column_def.attr != null && column_def.attr != "")
            value = this.store.getValue(item, column_def.attr, null);
        else
            value = null;

        return value;
    },

    _value_domtree: function (value) {
        if (value == null)
            value = document.createTextNode((this.ignoreNull) ? "" : "-");
        else if (typeof(value) == "string" || typeof(value) == "number")
            value = document.createTextNode(value.toString());

        var s = document.createElement("span");
        dojo.addClass(s, "item-table-value-wrapper");
        s.appendChild(value);

        return s;
    },

    _get_edit_value: function () {
        if (this._editInfo.getEdit != null) {
            var value = this._editInfo.getEdit(this._editItem);
        } else if (this._editInfo.editAttr != null
                   && this._editInfo.editAttr != "") {
            value=this.store.getValue(this._editItem, this._editInfo.editAttr);
        } else if (this._editInfo.get != null) {
            value = this._editInfo.get(this._editItem);
        } else if (this._editInfo.attr != null && this._editInfo.attr != "") {
            value=this.store.getValue(this._editItem, this._editInfo.attr);
        } else {
            value = null;
        }

        if (typeof(value) == "function")
            value = value.call(this._editItem);
        return value;
    },

    _set_value: function (info, item, value) {
        if (info.editSet != null) {
            info.editSet(item, value);
        } else if (info.editAttr != null
                   && info.editAttr != "") {
            this.store.setValue(item, info.editAttr, value);
        } else if (info.attr != null && info.attr != "") {
            this.store.setValue(item, info.attr, value);
        }
    },

    _destroy_editor: function () {
        if (this._editCell == null) {
            return;
        }
        this._editCell.tabIndex = 0;
        this._editInfo = null;
        this._editCell = null;
        this._editItem = null;
        this._editValue = null;
        this._editor = null;
    },

    _edit_cancel: function () {
        if (this._editCell == null)
            return;
        this._editCell.replaceChild(this._editValue, this._editCell.childNodes[0]);
        this._destroy_editor();
    },

    _edit_change: function () {
        if (this._editCell == null)
            return;
        if (typeof(this._editor.isValid) == "function"
            && ! this._editor.isValid())
            return;
        this._editCell.replaceChild(this._editValue, this._editCell.childNodes[0]);
        var info = this._editInfo;
        var item = this._editItem;
        var v = this._editor.getValue();
        this._destroy_editor();
        this._set_value(info, item, v);
    },

    _edit_keypress: function (event) {
        switch (event.keyCode) {
        case dojo.keys.ESCAPE:
            this._edit_cancel();
            break;
        case dojo.keys.ENTER:
            this._edit_change()
            break
        }
    },

    _edit_start: function (event) {
        if (this._mouse2down) {
            // So the resulting focus event doesn't screw up the context
            // menus...
            this._mouse2down = false;
            return;
        }
        if (this._editCell != null) {
            if (event.currentTarget != this._editCell) {
                this._edit_cancel();
            } else {
                // We're already editing...
                return;
            }
        }
        this._editCell = event.currentTarget;
        this._editInfo = this.model[this._editCell.cellIndex];
        this._editItem = this._get_dom_node_item(this._editCell.parentNode);
        if (this._editInfo.editAllowed != null) {
            if (! this._editInfo.editAllowed.call(this, this._editItem)) {
                this._editCell = null;
                this._editInfo = null;
                this._editItem = null;
                return;
            }
        }
        this._editCell.tabIndex = -1;
        this._editValue = this._editCell.childNodes[0];
        this._editor = new this._editInfo.editor(this._editInfo.editorProps);
        this._editor.setValue(this._get_edit_value());
        this._editor.focus();
        dojo.connect(this._editor, "onChange", this, "_edit_change");
        dojo.connect(this._editor, "onBlur", this, "_edit_cancel");
        //dojo.connect(this._editor, "onClose", this, "_edit_cancel");
        dojo.connect(this._editor.domNode, "onkeypress", this, "_edit_keypress");
        this._editCell.replaceChild(this._editor.domNode, this._editCell.childNodes[0]);
    },

    _create_contextmenu: function (item) {
        var m = new dijit.Menu;
        if (item != null) {
            var itemid = this.store.getIdentity(item);
            if (this._menus[itemid] != null)
                this._menus[itemid].destroy();
            this._menus[itemid] = m;
        }
        dojo.forEach(this.contextMenu, function (entry) {
            if (item == null && entry.includeOnHeader != true)
                return;
            var mentry = new dijit.MenuItem({ label: entry.label });
            dojo.connect(mentry, "onClick", this, function (evt) {
                entry.handler.call(this, item);
            });
            m.addChild(mentry);
        }, this);
        return m;
    },

    _display_validity: function (item, row) {
        if (this.displayValidity == true) {
            if (this.store.isValid(item))
                dojo.removeClass(row, "item-table-invalid");
            else
                dojo.addClass(row, "item-table-invalid");
        }
    },

    _onNewItem: function (item, parentInfo) {
        var i = this.itemrows.rows.length;
        var n = this._node_to_insert_before(item);
        if (n != null)
            i = n.sectionRowIndex;
        var r = this.itemrows.insertRow(i);
        this._display_validity(item, r);
        r.id = this._get_item_id(item);
        if (this.contextMenu != null) {
            var m = this._create_contextmenu(item);
            m.bindDomNode(r);
        }
        dojo.addClass(r, "item-table-item-row");
        for (i = this.model.length; i > 0; i--) {
            var c = r.insertCell(0);
            var m = this.model[i-1];
            c.id = this._get_cell_id(item, m.name);
            dojo.addClass(c, m.name);
            var v = this._item_column_value(item, m);
            if (m.editor != null) {
                dojo.connect(c, "onclick", this, "_edit_start");
                dojo.connect(c, "onfocus", this, "_edit_start");
                dojo.connect(c, "onmousedown", this, function (e) {
                    if (e.button == 2)
                        this._mouse2down = true;
                });
            }
            c.appendChild(this._value_domtree(v));
            if (((this.store.isDirty == null)
                 || (! this.store.isDirty(item))) && this.changeAnimFn != null)
                this.changeAnimFn(c).play();
        }
    },

    _onItemChange: function (item, attribute, oldValue, newValue) {
        var r = this._get_item_dom_node(item);
        if (r == null)
            return;  // Item wasn't being displayed.
        this._display_validity(item, r);
        for (var i = 0; i < this.model.length; i++) {
            var m = this.model[i];
            var c = r.childNodes[i];
            if (this._editCell != null && c == this._editCell) {
                // Don't update a cell being edited...
                continue;
            }
            var v = this._item_column_value(item, m);
            var t = this._value_domtree(v);
            if (! nox.ext.apps.coreui.coreui.base.equivDomTrees(t, c.childNodes[0])) {
                c.replaceChild(t, c.childNodes[0]);
                if (this.changeAnimFn != null)
                    this.changeAnimFn(c).play();
            }
        }
    },

    _onDeleteItem: function (item) {
        var r = this._get_item_dom_node(item);
        var itemid = this.store.getIdentity(item);
        if (this._menus[itemid] != null) {
            var m = this._menus[itemid];
            m.unBindDomNode(r);
            m.destroy();
            delete this._menus[itemid];
        }
        r.parentNode.removeChild(r);
    },

    postCreate: function () {
        dojo.connect(this.store, "onNew", this, "_onNewItem");
        dojo.connect(this.store, "onSet", this, "_onItemChange");
        dojo.connect(this.store, "onDelete", this, "_onDeleteItem");

        if (this.header != false) {
            var m = this._create_contextmenu(null);
            m.bindDomNode(this.headerrow);
            for (var i = this.model.length; i > 0; i--) {
                var cell = this.headerrow.insertCell(0);
                cell.appendChild(document.createTextNode(this.model[i-1].header));
            }
        }

        this.store.fetch({
            query: {},
            onItem: dojo.hitch(this, "_onNewItem")
        });
    }
});
