dojo.provide("nox.ext.apps.coreui.coreui.ItemListEditor");

dojo.require("dojo.DeferredList");
dojo.require("dijit.Dialog");
dojo.require("dijit.form.Button");
dojo.require("dijit.layout.BorderContainer");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");
dojo.require("dojo.data.ItemFileWriteStore");

dojo.require("dojox.dtl.html");

dojo.declare("nox.ext.apps.coreui.coreui.ItemListEditor", dijit.Dialog, {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ItemListEditor.html"),
	widgetsInTemplate: true,

	quickAddDefaultText: "Quick Add (comma separated)",

	layoutContainer: null,
	selectedStore: null,
	allStore: null,

	postCreate: function(){
		this.inherited(arguments);
	
		var d1 = new dojo.Deferred();
		var d2 = new dojo.Deferred();	
		var dl = new dojo.DeferredList([d1, d2]);

		dl.addCallback(this, function(results){
			var all_groups = results[0][1];
			var selected_groups = results[1][1];

			var isSelected = function(item){
				for(var i=0, j; j=selected_groups[i]; i++){
					if(j.getValue("name") == item.getValue("name")){
						return true;
					}
				}
				return false;
			}

			var ifws_items = [];
			for(var i=0, item; item=all_groups[i]; i++){
				if(!isSelected(item)){
					ifws_items.push({ name: item.getValue("name"), displayName: item.displayName() });
				}
			}
			this.tempAllStore = new dojo.data.ItemFileWriteStore({ data: { items: ifws_items } });
			var leftLayout = [
				{ name: "Groups", field: "displayName", width: "100%", editable: true, type: dojox.grid.cells._Widget }
			];
			var leftGrid = this.leftGrid = new dojox.grid.DataGrid({
				store: this.tempAllStore,
				query: {},
				structure: leftLayout,
				region: 'center'
			});
			this.connect(leftGrid.selection, "onChanged", function(){
				if(leftGrid.edit.isEditing()){
					this.editGroup.attr('disabled', true);
					this.remGroup.attr('disabled', true);
				}else{
					var selected = leftGrid.selection.getSelectedCount();
					this.editGroup.attr('disabled', (selected != 1));
					this.remGroup.attr('disabled', (selected < 1));
				}
			});
			this.connect(leftGrid.edit, "start", function(){
				this.addGroup.attr('disabled', true);
				this.editGroup.attr('disabled', true);
				this.remGroup.attr('disabled', true);
			});
			this.connect(leftGrid.edit, "apply", function(){
				this.addGroup.attr('disabled', false);
				this.editGroup.attr('disabled', false);
				this.remGroup.attr('disabled', false);
			});
			this.connect(leftGrid.edit, "cancel", function(){
				this.addGroup.attr('disabled', false);
				this.editGroup.attr('disabled', false);
				this.remGroup.attr('disabled', false);
			});
			this.left.addChild(leftGrid);
			leftGrid.startup();

			ifws_items = [];
			for(var i=0, item; item=selected_groups[i]; i++){
				ifws_items.push({ name: item.getValue("name"), displayName: item.displayName() });
			}
			this.tempSelectedStore = new dojo.data.ItemFileWriteStore({ data: { items: ifws_items } });
			var rightLayout = [
				{ name: "Groups", field: "displayName", width: "100%" }
			];

			var rightGrid = this.rightGrid = new dojox.grid.DataGrid({
				store: this.tempSelectedStore,
				query: {},
				structure: rightLayout,
				region: 'center'
			});
			this.right.addChild(rightGrid);
			rightGrid.startup();
			this.layoutContainer.resize();
		});

		this.allStore.fetch({
			query: {},
			onComplete: function(items){ d1.callback(items); }
		});

		this.selectedStore.fetch({
			query: {},
			onComplete: function(items){ d2.callback(items); }
		});
	},

	_moveItems: function(grid, fromStore, toStore){
		var selected = grid.selection.getSelected();
		dojo.forEach(selected, function(item){
			toStore.newItem({ name: item.name, displayName: item.displayName });
			fromStore.deleteItem(item);
		});
		toStore.save();
		fromStore.save();
	},

	_moveAll: function(fromStore, toStore){
		fromStore.fetch({
			query: {},
			onComplete: function(items){
				dojo.forEach(items, function(item){
					toStore.newItem({ name: item.name, displayName: item.displayName });
					fromStore.deleteItem(item);
				});
				toStore.save();
				fromStore.save();
			}
		});
	},

	onAddOne: function(){
		this._moveItems(this.leftGrid, this.tempAllStore, this.tempSelectedStore);
	},

	onRemOne: function(){
		this._moveItems(this.rightGrid, this.tempSelectedStore, this.tempAllStore);
	},

	onAddAll: function(){
		this._moveAll(this.tempAllStore, this.tempSelectedStore);
	},

	onRemAll: function(){
		this._moveAll(this.tempSelectedStore, this.tempAllStore);
	},

	onAddGroup: function(){
		var item = this.tempAllStore.newItem({ name: 'New Item', displayName: 'New Item' });
		var row_idx = this.leftGrid.getItemIndex(item);
		this.leftGrid.edit.setEditCell(this.leftGrid.layout.cells[0], row_idx);
	},

	onEditGroup: function(){
		var selected = this.leftGrid.selection.getSelected();
		var row_idx = this.leftGrid.getItemIndex(selected[0]);
		this.leftGrid.edit.setEditCell(this.leftGrid.layout.cells[0], row_idx);
	},

	onRemoveGroup: function(){
		dojo.forEach(this.leftGrid.selection.getSelected(), function(item){
			this.tempAllStore.deleteItem(item);
		}, this);
	},

	onQuickAddTextFocus: function(){
		var text = dojo.trim(this.quickAddText.attr('value'));
		if(text == this.quickAddDefaultText){
			this.quickAddText.attr('value', '');
			this.quickAddText.focus();
		}
	},

	onQuickAddTextBlur: function(){
		var text = dojo.trim(this.quickAddText.attr('value'));
		if(text == ''){
			this.quickAddText.attr('value', this.quickAddDefaultText);
		}
	},

	onQuickAddClicked: function(){
		var text = dojo.trim(this.quickAddText.attr('value'));
		if(text != this.quickAddDefaultText && text != ''){
			var names = text.split(/\s*,\s*/);
			for(var i=0, name; name=names[i]; i++){
				this.tempSelectedStore.newItem({ name: name, displayName: name });
			}
		}
	},

	onDoneClicked: function(){
		// TODO: once Keith gets the writeable stores in, this should apply the edits we've done to
		// the server
		this.hide();
	}
});
