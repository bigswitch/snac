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

dojo.provide("nox.ext.apps.coreui.coreui.EditableGridUtil");


dojo.declare("nox.ext.apps.coreui.coreui.EditableGridUtil", [], {

        editable_item_formatter: function(value) {
          // if value is empty ... still show that it is editable
          // NOTE: it seems like there is a dojo bug that make this
          // markup not reappear if you cancel an edit on a cell.  
          if(value == null || value == undefined || value == "") 
            value = "&nbsp;&nbsp;&nbsp;"; 
          return '<span class="editable-grid-entry">' + 
            '<span class="editable-grid-value-wrapper">' + value + "</span>" + 
            '<img class="grid-edit-icon" style="visibility: hidden"' + 
            ' src="/static/nox.ext.apps.coreui/coreui/images/editIndicator.png" />' + 
            '</span>'; 
        } 
});

(function () {
    var editable_grid_util = null;
    nox.ext.apps.coreui.coreui.getEditableGridUtil = function () {
        if (editable_grid_util == null) {
            editable_grid_util = new nox.ext.apps.coreui.coreui.EditableGridUtil();
        }
        return editable_grid_util;
    }
})();

