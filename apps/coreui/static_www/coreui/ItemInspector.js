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

dojo.provide("nox.ext.apps.coreui.coreui.ItemInspector");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dojox.dtl._Templated");
dojo.require("nox.ext.apps.coreui.coreui.base");

dojo.declare("nox.ext.apps.coreui.coreui.ItemInspector", [ dijit._Widget, dojox.dtl._Templated ], {

    templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ItemInspector.html"),
	editIconPath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "images/editIndicator.png"),
    widgetsInTemplate: false,
    item: null,
    model: null,
    ignoreNullValues: false,

    constructor: function () {
        this._initialized = false;
        this._editValue = null;
        this._editRow = null;
        this._editor = null;
    },

    _get_value: function (rowdef) {
        if (rowdef.get != null) {
            var value = rowdef.get(this.item);
        } else if (rowdef.attr != null && rowdef.attr != "") {
            value = this.item.getValue(rowdef.attr);
        } else {
            value = null;
        }

        if (typeof(value) == "function")
            value = value.call(this.item);

        if (value == null)
            value = document.createTextNode((this.ignoreNullValues) ? "" : "?");
        else if (typeof(value) == "string")
            value = document.createTextNode(value);
        else if (typeof(value) == "number")
            value = document.createTextNode(String(value));

        return value;
    },

    _get_edit_value: function (rowdef) {
        if (rowdef.getEdit != null) {
            var value = rowdef.getEdit(this.item);
        } else if (rowdef.editAttr != null && rowdef.editAttr != "") {
            value = this.item.getValue(rowdef.editAttr);
        } else if (rowdef.get != null) {
            value = rowdef.get(this.item);
        } else if (rowdef.attr != null && rowdef.attr != "") {
            value = this.item.getValue(rowdef.attr);
        } else {
            value = null;
        }

        if (typeof(value) == "function")
            value = value.call(this.item);

        return value;
    },

    _set_value: function (rowdef, v) {
        if (rowdef.editSet != null) {
            rowdef.editSet(this.item, v);
        } else if (rowdef.editAttr != null && rowdef.editAttr != "") {
            this.item.setValue(rowdef.editAttr, v);
        } else if (rowdef.attr != null && rowdef.attr != "") {
            this.item.setValue(rowdef.attr, v);
        }
    },

    _get_row_value: function (i) {
        return this.table.rows[i].cells[1].childNodes[0];
    },

    _set_row_value: function (i, v) {
        this.table.rows[i].cells[1].replaceChild(v, this._get_row_value(i));
    },

    _update_row: function (i) {
        // Don't update row when edit is in progress...
        var m = this.model[i];
        if(!m){ return; }
        if (m.separator == null || m.separator != true) {
            if (this._initialized && m.noupdate == true)
                return;
            var new_v = document.createElement("span");
            dojo.addClass(new_v, "item-inspector-value-wrapper");
            new_v.appendChild(this._get_value(m));
            var old_v = this._get_row_value(i);
            if (! nox.ext.apps.coreui.coreui.base.equivDomTrees(old_v, new_v)) {
                this._set_row_value(i, new_v);
                if (this.changeAnimFn != null)
                    this.changeAnimFn(new_v.parentNode).play();
            }
        }
    },

    update: function () {
        for (var i = 0; i < this.model.length; i++) {
            if (this._editRow != i) {
                // Only update a row if we aren't currently editing it.
                this._update_row(i);
            }
        }
    },

    _destroy_editor: function () {
        if (this._editRow == null) {
            return;
        }
        this.table.rows[this._editRow].cells[1].tabIndex = 0;
        this._editRow = null;
        this._editValue = null;
        var e = this._editor;
        this._editor = null;
        //console.log("destroying control.");
        //e.destroy();
    },


    _edit_cancel: function (is_dialog) {
        if (this._editRow == null)
            return;
        this._set_row_value(this._editRow, this._editValue);
        this._update_row(this._editRow);
		if(!is_dialog){
			this._destroy_editor();
		}
    },

    _edit_change: function (is_dialog) {
        if (this._editRow == null)
            return;
        if (this._editor.isValid == undefined || 
            (this._editor.isValid && this._editor.isValid())) {
            this._set_row_value(this._editRow, this._editValue);
            this._set_value(this.model[this._editRow], this._editor.getValue());
            this._update_row(this._editRow);

            if(!is_dialog){
                this._destroy_editor();
            }
        } else {
            this._edit_cancel(is_dialog);
        }
    },

    _edit_keypress: function (event) {
        switch (event.keyCode) {
        case dojo.keys.ESCAPE:
            this._edit_cancel();
            break;
        case dojo.keys.ENTER:
            this._edit_change();
            break;
        }
    },

	_edit_common: function(event){
		var target = event.target;
		while(target && target.tagName && target.tagName.toLowerCase() != "td" && !dojo.hasClass(target, "item-inspector-value")){
			target = target.parentNode;
		}
        target.tabIndex = -1;
        var i = target.parentNode.rowIndex;
        if (this._editRow != null && i != this._editRow) {
            this._edit_cancel();
        }
        this._editRow = i;
        this._editValue = this._get_row_value(i);

		return i;
	},

    _edit_start: function (event) {
		var i = this._edit_common(event);
        this._editor = new this.model[i].editor(this.model[i].editorProps);
    var val = this._get_edit_value(this.model[i]) || ""; 
		this._editor.setDisplayedValue(val);
		//dojo.connect(this._editor, "onChange", this, "_edit_change");
		dojo.connect(this._editor, "onBlur", this, "_edit_cancel");
		//dojo.connect(this._editor, "onClose", this, "_edit_cancel");
		dojo.connect(this._editor.domNode, "onkeypress", this, "_edit_keypress");
		this._set_row_value(i, this._editor.domNode);
		this._editor.focus();
    },

	_edit_dialog_start: function(event){
		var i = this._edit_common(event);
		var editor = this.model[i].editor;
		if(editor){
			this._editor = new editor(this.model[i].editorProps);
		}else{
			this._editor = new dijit.Dialog(this.model[i].editorProps);
		}
		this._editor.show();
		dojo.connect(this._editor,"onCancel",dojo.hitch(this, "_edit_cancel", true));
		dojo.connect(this._editor,"onExecute",dojo.hitch(this, "_edit_apply", true));
		dojo.connect(this._editor._fadeOut,"onEnd",this,"_destroy_editor");
	},

    postCreate: function () {
		this.inherited(arguments);
		dojo.query("td.item-inspector-editable", this.table).forEach(function(cell){
			if(!dojo.hasClass(cell, "item-inspector-editable-dialog")){
				var timeout, clicked = false;
				this.connect(cell, "onmousedown", (function(){
					// handles double-click and prevents selection
					return function(e){
						clearTimeout(timeout);
						if(clicked){
							dojo.stopEvent(e);
							this._edit_start(e);
						}
						clicked = true;
						timeout = setTimeout(function(){
							clicked = false;
						}, 500);
					}
				})());
				this.connect(cell, "onfocus", function(e){
					if(!clicked){
						this._edit_start(e);
					}
				});
				this.connect(cell, "onkeypress", function(e){
					if(e.keyCode == dojo.keys.ENTER && this._editRow != null){
						this._edit_start(e);
					}
				});
				var editIcon = dojo.query("img.item-inspector-edit-icon", cell)[0];
				this.connect(editIcon, "onclick", "_edit_start");
			}else{
				var editIcon = dojo.query("img.item-inspector-edit-icon", cell)[0];
				this.connect(editIcon, "onclick", "_edit_dialog_start");
			}
		}, this);
        this.update();
        this._initialized = true;
    }

});
