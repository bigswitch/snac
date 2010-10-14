dojo.provide("nox.ext.apps.coreui.coreui.NetworkStatusIndicator");

dojo.require("dijit.layout.BorderContainer");
dojo.require("dijit._Templated");

dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.form.CheckBox");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojo.data.ItemFileWriteStore");
dojo.require("dojo.cookie");

dojo.require("dijit.Dialog");

dojo.declare("nox.ext.apps.coreui.coreui.NetworkStatusTooltip", dijit.TooltipDialog, {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/NetworkStatusTooltip.html"),
	title: "Network Status Changed",
	autofocus: false,

	open: false,
	buttonCancel: 'Cancel',

	_fadeOutTimeout: null,

	postCreate: function(){
		this.inherited(arguments);
		dojo.addClass(this.domNode, "networkStatusTooltip");

		this._fadeOut = dojo.fadeOut({ node: this.domNode, duration: dijit.defaultDuration, onEnd: dojo.hitch(this, "_closeMe") });
		this._fadeIn = dojo.fadeIn({ node: this.domNode, duration: dijit.defaultDuration });
	},

	onOpen: function(){
		this.inherited(arguments);
		this.open = true;
	},

	onClose: function(){
		this.open = false;
		this.attr('content', '');
	},

	addMessage: function(msg){
		var markup = '<div class="message ' + msg['status'] + '">'
			+'<span>' + msg.item_ui_monitor_link_text + '<span> ' + msg.message + '</span></span><br />'
			+'<span class="dateTime">' + msg.dateTime + '</span>'
		+'</div>';

		if(this.open){
			clearTimeout(this._fadeOutTimeout);
			if(this._fadeOut.status() == "playing"){
				this._fadeOut.stop();
				this._fadeIn.play();
			}

			var content = this.attr('content');
			this.attr('content', markup + content);
		}else{
			this.attr('content', markup);

		}
		dijit.popup.open({
			parent: this.parentWidget,
			popup: this,
			around: this.aroundNode,
			orient: { 'TL': 'BL' }
		});
		var self = this;
		this._fadeOutTimeout = setTimeout(function(){
			self._fadeOut.play();
		}, 5000);
	},

	_closeMe: function(){
		clearTimeout(this._fadeOutTimeout);
		if(this._fadeOut.status() == "playing"){
			this._fadeOut.stop();
		}
		dijit.popup.close(this);
		dojo.style(this.domNode, "opacity", 1);
		delete this._fadeOutTimeout;
	}
});

dojo.declare("nox.ext.apps.coreui.coreui.NetworkStatusIndicator", [ dijit.layout.BorderContainer, dijit._Templated ], {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/NetworkStatusIndicator.html"),
	widgetsInTemplate: true,

	splitter: true,
	minSize: 28,
	maxSize: 350,

	store: null,
	tooltip: null,

	"status": "normal",

	status_map: {
		normal: [ "Good", "Normal" ],
		minor: 	[ "Minor Issue", "Minor" ],
		major:  [ "Serious Issue", "Major" ]
	},

	state: {
		defaultSize: 150,
		expanded: true,
		showNotifications: true
	},

	constructor: function(){
		var item = {
			item_name: "Switch 0001",
			item_ui_monitor_link_text: "<a href=''>Switch 0001</a>",
			message: "cannot be reached. Error 40102",
			"status": "major",
			solution: "Brief solution text",
			solution_link_text: "<a href=''>Action link here</a>",
			dateTime: null
		};
		var items = [];

		for(var i=0; i<50; i++){
			var st = "normal";
			var m = i % 3;
			if(m==0){
				st = "normal";
			}else if(m==1){
				st = "minor";
			}else if(m==2){
				st = "major";
			}
			items.push(dojo.mixin(dojo.clone(item), { "status": st }));
			items[i].dateTime = (new Date()).toString();
		}
		this.store = new dojo.data.ItemFileWriteStore({
			data: {
				items: items
			}
		});

		if(dojo.cookie.isSupported()){
			var cookie = dojo.cookie("NOX_Network_Status_Indicator");
			if(cookie){
				dojo.mixin(this.state, dojo.fromJson(cookie));
			}
		}
		this._saveState();
	},

	postCreate: function(){
		this.inherited(arguments);

		var messages = this.messages = new dojox.grid.DataGrid({
			store: this.store,
			query: {},
			region: 'center',
			selectionMode: 'none',
			getSortProps: function(){
				return [{ attribute: "dateTime", descending: true }];
			},
			structure: [
				{
					name: 'message', width: 'auto', get: function(index, item){
						if(!item){ return null; }
						var item_link = item.item_ui_monitor_link_text;
						var message = item.message;
						var time = item.dateTime;

						return '<div class="message ' + item['status'] + '">'
							+'<span>' + item_link + '<span> ' + message + '</span></span><br />'
							+'<span class="dateTime">' + time + '</span>'
						+'</div>';
					}
				}
			]
		});
		this.addChild(messages);
		messages.startup();

		var gridTooltip = this.gridTooltip = new dijit._MasterTooltip();
		dojo.addClass(this.gridTooltip.domNode, "networkStatusGridTooltip");
		

		var _show_timeouts = [];
		var _hide_timeouts = [];

		var self = this;
		var cncts = [];
		var disconCncts = function(index){
			dojo.forEach(cncts[index], dojo.disconnect);
			cncts[index] = [];
		};
		var onTooltipMouseover = function(index, cell, e){
			clearTimeout(_hide_timeouts[index]);
			_hide_timeouts[index] = null;
		};
		var onTooltipMouseout = function(index, cell, e){
			_hide_timeouts[index] = setTimeout(function(){
				gridTooltip.hide(cell);
				_hide_timeouts[index] = null;
				disconCncts(index);
			}, 500);
		};
		var showTooltip = function(e){
			if(_hide_timeouts[e.rowIndex]){
				clearTimeout(_hide_timeouts[e.rowIndex]);
				_hide_timeouts[e.rowIndex] = null;
				return;
			}
			var idx = e.rowIndex;
			var item = messages.getItem(idx);

			var text = item.solution + '<br />' + item.solution_link_text;

			_show_timeouts[idx] = setTimeout(function(){
				gridTooltip.show(text, e.cellNode, [ "above" ]);
				if(!cncts[idx] || !cncts[idx].length){
					cncts[idx] = [];
					cncts[idx].push(dojo.connect(gridTooltip.domNode, "onmouseenter", dojo.partial(onTooltipMouseover, idx, e.cellNode)));
					cncts[idx].push(dojo.connect(gridTooltip.domNode, "onmouseleave", dojo.partial(onTooltipMouseout, idx, e.cellNode)));
				}
			}, 500);
		};
		var hideTooltip = function(e){
			clearTimeout(_show_timeouts[e.rowIndex]);

			_hide_timeouts[e.rowIndex] = setTimeout(function(){
				gridTooltip.hide(e.cellNode);
				_hide_timeouts[e.rowIndex] = null;
				disconCncts(e.rowIndex);
			}, 500);
		};
		this.connect(messages, "onCellMouseOver", showTooltip);
		this.connect(messages, "onCellMouseOut", hideTooltip);

		this.connect(this.store, "onNew", "onNewStatus");

		this.store.fetch({ query: {}, count: 1, sort: [{ attribute: "dateTime", descending: true }],
			onComplete: dojo.hitch(this, function(items){
				var item = items[0];
				this.attr('status', item['status']);
			})
		});

		var initialSize = this.minSize;
		if(this.state.expanded){
			initialSize = this.state.defaultSize;
		}
		dojo.style(this.domNode, {
			height: initialSize + "px"
		});
		this._setExpandedClass();
		this.notificationCheck.attr('checked', this.state.showNotifications);
	},

	_saveState: function(){
		if(dojo.cookie.isSupported()){
			var cookie = dojo.toJson(this.state);
			if(dojo.cookie("NOX_Network_Status_Indicator") != cookie){
				dojo.cookie("NOX_Network_Status_Indicator", dojo.toJson(this.state), { expires: 365, path: '/' });
			}
		}
	},

	_setExpandedClass: function(){
		dojo.addClass(this.domNode, this.state.expanded ? "open" : "closed");
		dojo.removeClass(this.domNode, this.state.expanded ? "closed" : "open");
	},

	resize: function(){
		this.inherited(arguments);

		var height = dojo.marginBox(this.domNode).h;
		if(height > 30){
			this.state.expanded = true;
			this.state.defaultSize = height;
		}else{
			this.state.expanded = false;
		}
		this._setExpandedClass();
		this._saveState();
	},

	onToggle: function(){
		if(this.state.expanded){
			this.state.defaultSize = dojo.marginBox(this.domNode).h;
			this.resize({ h: this.minSize });
		}else{
			this.resize({ h: this.state.defaultSize });
		}
		this.state.expanded = !this.state.expanded;
		this._setExpandedClass();
		this.getParent().resize();
	},

	onNotificationsToggle: function(){
		this.state.showNotifications = this.notificationCheck.attr('checked');
		this._saveState();
	},

	_setStatusAttr: function(st){
		if(!this.status_map[st]){ var st = 'normal'; }

		var stat = this.status_map[st];
		var old_stat = this.status_map[this['status']];

		dojo.removeClass(this.statusContainer.domNode, 'networkStatus' + old_stat[1]);
		dojo.addClass(this.statusContainer.domNode, 'networkStatus' + stat[1]);

		this.statusTextNode.innerHTML = stat[0];

		this['status'] = st;

		return st;
	},

	onNewStatus: function(item){
		this.attr('status', item['status']);
		if(this.state.showNotifications && !this.state.expanded && item['status'] != 'normal'){
			if(!this.tooltip){
				this.tooltip = new nox.ext.apps.coreui.coreui.NetworkStatusTooltip({
					title: "Network Status Changed",
					autofocus: false,
					parentWidget: this,
					aroundNode: this.toggleContainer
				});
				dijit.popup.prepare(this.tooltip.domNode);
			}
			this.tooltip.addMessage(item);
		}
		// because dojo.data doesn't give us sort info, we have to
		// re-render the grid to get the new item to show up in the right place :(
		this.messages.render();
	}
});
