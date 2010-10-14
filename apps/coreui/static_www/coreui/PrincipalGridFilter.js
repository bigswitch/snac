dojo.provide("nox.ext.apps.coreui.coreui.PrincipalGridFilter");

dojo.require("nox.ext.apps.directory.directorymanagerws.Directories");

dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.Button");
dojo.require("dojox.form.DropDownSelect");

dojo.declare("nox.ext.apps.coreui.coreui.PrincipalGridFilter", [dijit._Widget, dijit._Templated], {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/PrincipalGridFilter.html"),
	widgetsInTemplate: true,

	grid: null,
	principalType: "switch",
	directoryStore: nox.ext.apps.directory.directorymanagerws.Directories.datastore,

	constructor: function(){
		this._wconnects = []
		this.directoryStore = nox.ext.apps.directory.directorymanagerws.Directories.datastore;
	},

	postCreate: function(){
		this.inherited(arguments);
		this._fillDirectories();

		this._connectWidgets();

        this.connect(this.directoryStore,"onNew","_onNewDirectory");
        this.connect(this.directoryStore,"onDelete","_onDeleteDirectory");
	},

	_fillDirectories: function(){
		this.directories.removeOption();
		this.directories.addOption({ value: "*", label: "", selected: true });

		this.directoryStore.fetch({
			onComplete: dojo.hitch(this, function(items, req){
				var enabled_str = "read_" + this.principalType + "_enabled";
				dojo.forEach(items, function(item){
					this.directories.addOption({ value: item.name, label: item.name });
				}, this);
			})
		});
	},

	_onNewDirectory: function(item){
		this.directories.addOption({ value: item.name, label: item.name });
	},

	_onDeleteDirectory: function(item){
		this.directories.removeOption(item.name);
	},

	_connectWidgets: function(){
		this._wconnects = []
		this._wconnects.push(this.connect(this.name, "onChange", "filter"));
		this._wconnects.push(this.connect(this.directories, "onChange", "filter"));
		this._wconnects.push(this.connect(this.status, "onChange", "filter"));
	},

	_disconnectWidgets: function(){
		dojo.forEach(this._wconnects, function(c){
			this.disconnect(c);
		}, this);
	},

	clear: function(){
		this._disconnectWidgets();
		this.name.attr('value', '');
		this.directories.attr('value', '*');
		this.filter();
		this._connectWidgets();
	},

	filter: function(){
		var query = this.grid.attr('query');
		var name = this.name.attr('value');
		var directory = this.directories.attr('value');
		var st = this.status.attr('value');

		if(name){
			name = "*" + name + "*";
		}else{
			name = "*";
		}

		query = {
			name: name,
			directoryName: directory,
			"status": st
		};

		this.grid.filter(query);
	}
});
