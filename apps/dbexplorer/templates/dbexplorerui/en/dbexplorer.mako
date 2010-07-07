## -*- coding: utf-8 -*-

<%inherit file="layout.mako"/>
<%def name="page_title()">${dbname.upper()}Explorer</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "${self.dojo_root()}/dojox/grid/resources/nihiloGrid.css";
  @import "/static/nox/ext/apps/dbexplorer/dbexplorer/dbexplorerui.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dojo.data.ItemFileWriteStore");
  dojo.require("dijit.form.Form");
  dojo.require("dijit.form.FilteringSelect");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.NumberTextBox");
  dojo.require("dijit.layout.AccordionContainer");
  dojo.require("dojox.grid.DataGrid");
</%def>

<%def name="head_js()">
  ${parent.head_js()}

  var default_grid_layout = [ { name: "", field: "id" } ]
  var default_grid_store = new dojo.data.ItemFileWriteStore({data: { identifier: "id", items: []} });

  var current_table_name;

  function update_status_msg(msg, msg_class) {
      var status_node = dojo.byId("statusMsgArea");
      status_node.style.opacity = 1.0;
      status_node.innerHTML = "<span class='" + msg_class + "'>" + msg + "</span>";
  }

  function update_status_msg_fadeout(msg, msg_class, duration) {
      update_status_msg(msg, msg_class);
      var status_node = dojo.byId("statusMsgArea");
      var anim = dojo.fadeOut({node: status_node,
                               "duration": duration});
      anim.play();
  }

  function insert_form_submit() {
      var insertform = dijit.byId("insertform");
      if (! insertform.isValid()) {
          update_status_msg_fadeout("Update aborted due to invalid field values", "errormsg", 5000);
          return;
      }
      update_status_msg("Submitting row...", "normalmsg");
      var formcontent = dojo.formToJson("insertform");
      dojo.rawXhrPost({url: "/ws.v1/storage/${dbname}/table/" + current_table_name,
                       headers: {"content-type": "application/json"},
                       postData: formcontent,
                       timeout: 10000,
                       load: function() {
                            update_status_msg_fadeout("Update succeeded", "successmsg", 2000);
                            form = dijit.byId("insertform");
                            form.reset();
                            dijit.byId("insert_form_first_field").focus();
                        },
                        error: function() {
                            update_status_msg_fadeout("Update failed", "errormsg", 5000);
                        }});
  }

  function add_cell_to_row_of_form_tbl(row, value, class_name, id) {
      var cell = row.insertCell(-1);
      if (id != undefined)
          cell.id = id;
      if (class_name != undefined)
          cell.className = class_name;
      cell.appendChild(value);
  }

  function add_field_row_to_form_tbl(tbl, fld_name, fld_type, id) {
      if (fld_type == 3)
          return;
      var row = tbl.insertRow(-1);
      add_cell_to_row_of_form_tbl(row, document.createTextNode(fld_name), "insertFormLabel");
      var w = undefined;
      switch (fld_type) {
          case 0:  /* INT */
              w = new dijit.form.NumberTextBox({ "id": id, name: fld_name, constraints: { places: 0}, required: true});
              break;id
          case 1:  /* TEXT */
              w = new dijit.form.TextBox({ "id": id, name: fld_name });
              break;
          case 2:  /* DOUBLE */
              w = new dijit.form.NumberTextBox({ "id": id, "name": fld_name, "required" : true});
              break;
          case 3:  /* GUID */
              alert("GUID field type!!!!.");
              break;
          default:
              alert("Unknown field type.");
              return;
      }
      add_cell_to_row_of_form_tbl(row, w.domNode, "insertFormControl");
  }

  function add_submit_row_to_form_tbl(tbl) {
      var row = tbl.insertRow(-1);
      add_cell_to_row_of_form_tbl(row, document.createTextNode(""),
                                  "insertFormLabel");
      w = new dijit.form.Button({ "id" : "insert_submit_btn",
                                  "label" : "Submit"});
      dojo.connect(w, "onClick", dojo.global, "insert_form_submit");
      add_cell_to_row_of_form_tbl(row, w.domNode, "insertFormSubmitBtn");
  }

  function handle_table_item(tbl, item) {
      var fld_names = schemaStore.getValues(item, "field_names");
      var fld_types = schemaStore.getValues(item, "field_types");
      id = "insert_form_first_field";
      for (i = 0; i < fld_names.length; i++) {
          add_field_row_to_form_tbl(tbl, fld_names[i], fld_types[i], id);
          first_field = false;
          id = undefined;
      }
      add_submit_row_to_form_tbl(tbl);
  }

  function create_form(table_name) {
      var fw = new dijit.form.Form({"id" : "insertform"});
      var tbl = document.createElement("table");
      schemaStore.fetch({ "query": { "table_name": table_name },
                          "onItem": function(item, request) {
                                        handle_table_item(tbl, item);
                                   }});
      fw.domNode.appendChild(tbl);
      return fw;
   }

   function table_data_grid_delete(item) {
       dojo.xhrDelete({
           url: item["GUID.link"][0],
           load: function(response, ioArgs) {
               update_status_msg_fadeout("Deleted", "successmsg", 500);
           },
           error: function(response, ioArgs) {
               update_status_msg_fadeout("Delete failed", "errormsg", 5000);
           },
           timeout: 10000
       });
   }

   function handle_grid_item(cells, item) {
      var fld_names = schemaStore.getValues(item, "field_names");
      var fld_types = schemaStore.getValues(item, "field_types");
      for (i = 0; i < fld_names.length; i++) {
         var field = {};
         field.name = fld_names[i];
         field.field = fld_names[i];
         field.width = 100 / fld_names.length + "%";
         cells.push(field);
      }
   }

   function table_data_request_ok(response, ioArgs) {
       update_status_msg("Data retrieved, constructing view...", "normalmsg");
       var table_name = current_table_name;
       var grid = dijit.byId("currentDataGrid");
       var store = new dojo.data.ItemFileWriteStore({ data: response });
       cells = [];
       schemaStore.fetch({ "query": { "table_name" : table_name },
                           "onItem": function(item, request) {
                                         handle_grid_item(cells, item);
                                     }});
       grid.setStore(store);
       grid.setStructure(cells);
	   grid.setQuery({ "GUID": '*' });
       dojo.connect(store, "onDelete", table_data_grid_delete);
       update_status_msg_fadeout("Update complete.", "successmsg", 2000);
   }

   function refresh_current_data_grid(table_name) {
      update_status_msg("Retreiving data...", "normalmsg");
      dojo.xhrGet({
          url: "/ws.v1/storage/${dbname}/table/" + table_name,
          load: table_data_request_ok,
          error: function (response, ioArgs) {
              update_status_msg_fadeout("Retrieval of current table data failed.", "errormsg", 5000);
          },
          handleAs: 'json',
          timeout: 10000
      });
   }

</%def>

## ---------------------------------------------------------------------------

<div dojoType="dojo.data.ItemFileWriteStore"
     jsId="schemaStore" url="/ws.v1/storage/${dbname}/schema">
</div>

<div dojoType="dijit.layout.BorderContainer" id="dbexplorer_main"
     design="headline" region="center">

  <div dojoType="dijit.layout.ContentPane" region="top">
    <form dojoType="dijit.form.Form" method="get">
      Table: <select dojoType="dijit.form.FilteringSelect" name="selectedTable" autocomplete="true" store="schemaStore" searchAttr="table_name">
        <script type="dojo/method">
          this.focus()
        </script>
        <script type="dojo/method" event="onChange" args="event">
          current_table_name = this.value;
          refresh_current_data_grid(this.value);
          var insert_pane = dijit.byId("insert_pane");
          insert_pane.destroyDescendants();
          fw = create_form(this.value);
          insert_pane.setContent(fw.domNode);
          fw.startup();
        </script>
      </select>
      <button dojoType="dijit.form.Button" id="refreshButton">
        Refresh
        <script type="dojo/method" event="onClick">
          if (current_table_name != undefined) { 
            refresh_current_data_grid(current_table_name);
          } else {
            update_status_msg_fadeout("No table selected for refresh", "error", 5000);
          }
        </script>
      </button>
      <button dojoType="dijit.form.Button" id="deleteButton">
        Delete
        <script type="dojo/method" event="onClick">
          update_status_msg("Removing selected items", "normalmsg");
          var grid = dijit.byId("currentDataGrid");
          grid.removeSelectedRows();
        </script>
      </button>
      <span id="statusMsgArea"></span>
    </form>
  </div>

  <div dojoType="dijit.layout.AccordionContainer",
       duration="50" region="center">
    <div dojoType="dijit.layout.AccordionPane"
         selected="true" title="Current Data">
         <div dojoType="dojox.grid.DataGrid" jsId="currentDataGrid" id="currentDataGrid"
              store="default_grid_store" structure="default_grid_layout" query="{ 'id': '*' }"
			  rowSelector="15px" authWidth="1" authHeight="1">
			<script type="dojo/connect" event="onBlur">
				currentDataGrid.selection.deselectAll();
			</script>
		</div>
    </div>

    <div dojoType="dijit.layout.AccordionPane"
         selected="true" title="Insert Row" id="insert_pane">
    </div>

  </div>
</div>
