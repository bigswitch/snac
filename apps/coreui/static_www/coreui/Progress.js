dojo.provide("nox.ext.apps.coreui.coreui.Progress");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.Tooltip");
dojo.require("dijit.ProgressBar");

dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");

dojo.require("dojo.i18n");
dojo.requireLocalization("nox.ext.apps.coreui.coreui", "Progress");

dojo.declare("nox.ext.apps.coreui.coreui._Tooltip", dijit._MasterTooltip, {
	disabled: true,

	templateString: null,

	widgetsInTemplate: true,

	position: [ "below" ],

	events: ["onMouseOver", "onMouseOut", "onFocus", "onBlur", "onHover", "onUnHover"],

	constructor: function(){
		this._tooltip_connects = [];
	},

	postMixInProperties: function(){
		var _nlsResources = dojo.i18n.getLocalization("nox.ext.apps.coreui.coreui", "Progress");
		dojo.mixin(this, _nlsResources);
		this.inherited(arguments);
	},

	postCreate: function(){
		this.inherited(arguments);
		if(this.srcNodeRef){
			this.srcNodeRef.style.display = "none";
		}

		this._connectNodes = [];

		if(!this.disabled){
			this._enable();
		}
	},

	show: function(/*DomNode*/ aroundNode, /*String[]?*/ position){
		// summary:
		//	Display tooltip w/specified contents to right specified node
		//	(To left if there's no space on the right, or if LTR==right)

		if(this.aroundNode && this.aroundNode === aroundNode){
			return;
		}

		if(this.fadeOut.status() == "playing"){
			// previous tooltip is being hidden; wait until the hide completes then show new one
			this._onDeck=arguments;
			return;
		}

		// Firefox bug. when innerHTML changes to be shorter than previous
		// one, the node size will not be updated until it moves.
		this.domNode.style.top = (this.domNode.offsetTop + 1) + "px";

		// position the element and change CSS according to position[] (a list of positions to try)
		var align = {};
		var ltr = this.isLeftToRight();
		dojo.forEach( (position && position.length) ? position : dijit.Tooltip.defaultPosition, function(pos){
			switch(pos){
				case "after":				
					align[ltr ? "BR" : "BL"] = ltr ? "BL" : "BR";
					break;
				case "before":
					align[ltr ? "BL" : "BR"] = ltr ? "BR" : "BL";
					break;
				case "below":
					// first try to align left borders, next try to align right borders (or reverse for RTL mode)
					align[ltr ? "BL" : "BR"] = ltr ? "TL" : "TR";
					align[ltr ? "BR" : "BL"] = ltr ? "TR" : "TL";
					break;
				case "above":
				default:
					// first try to align left borders, next try to align right borders (or reverse for RTL mode)
					align[ltr ? "TL" : "TR"] = ltr ? "BL" : "BR";
					align[ltr ? "TR" : "TL"] = ltr ? "BR" : "BL";
					break;
			}
		});
		var pos = dijit.placeOnScreenAroundElement(this.domNode, aroundNode, align, dojo.hitch(this, "orient"));

		// show it
		dojo.style(this.domNode, "opacity", 0);
		this.fadeIn.play();
		this.isShowingNow = true;
		this.aroundNode = aroundNode;
	},

	disable: function(){
		if(this.disabled){ return; }
		this.hide(this.aroundNode);
		dojo.forEach(this._tooltip_connects, function(cts){
			this.disconnect(cts);
		}, this);
		this.disabled = true;
	},

	enable: function(){
		if(!this.disabled){ return; }
		this._enable();
	},

	_enable: function(){
		dojo.forEach(this.connectId, function(id) {
			var node = dojo.byId(id);
			if(node){
				this._connectNodes.push(node);
				dojo.forEach(this.events, function(event){
					this._tooltip_connects.push(this.connect(node, event.toLowerCase(), "_"+event));
				}, this);
				if(dojo.isIE){
					// BiDi workaround
					node.style.zoom = 1;
				}
			}
		}, this);
		this.disabled = false;
	},

	_onMouseOver: function(/*Event*/ e){
		this._onHover(e);
	},

	_onMouseOut: function(/*Event*/ e){
		if(dojo.isDescendant(e.relatedTarget, e.target)){
			// false event; just moved from target to target child; ignore.
			return;
		}
		this._onUnHover(e);
	},

	_onFocus: function(/*Event*/ e){
		this._focus = true;
		this._onHover(e);
		this.inherited(arguments);
	},
	
	_onBlur: function(/*Event*/ e){
		this._focus = false;
		this._onUnHover(e);
		this.inherited(arguments);
	},

	_onHover: function(/*Event*/ e){
		if(!this._showTimer && e){
			var target = e.target;
			this._showTimer = setTimeout(dojo.hitch(this, function(){this.open(target)}), this.showDelay);
		}
	},

	_onUnHover: function(/*Event*/ e){
		// keep a tooltip open if the associated element has focus
		if(this._focus){ return; }
		if(this._showTimer){
			clearTimeout(this._showTimer);
			delete this._showTimer;
		}
		this.close();
	},

	open: function(/*DomNode*/ target){
		// summary: display the tooltip; usually not called directly.
		target = target || this._connectNodes[0];
		if(!target){ return; }

		if(this._showTimer){
			clearTimeout(this._showTimer);
			delete this._showTimer;
		}
		this.show(target, this.position);
		
		this._connectNode = target;
	},

	close: function(){
		// summary: hide the tooltip; usually not called directly.
		this.hide(this._connectNode);
		delete this._connectNode;
		if(this._showTimer){
			clearTimeout(this._showTimer);
			delete this._showTimer;
		}
	},

	uninitialize: function(){
		this.close();
	},

	destroy: function(){
		this._tooltip_connects = null;
	}
});

dojo.declare("nox.ext.apps.coreui.coreui.ProgressTooltip", nox.ext.apps.coreui.coreui._Tooltip, {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ProgressTooltip.html"),

	setPercentage: function(pct){
		this.progress.update({ progress: pct });
	}
});

dojo.declare("nox.ext.apps.coreui.coreui.ErrorTooltip", nox.ext.apps.coreui.coreui._Tooltip, {
	templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/ErrorTooltip.html"),

	events: ["onMouseOver", "onFocus", "onHover"],

	setError: function(error_text, args){
    if(error_text.length > 300) { 
        error_text = error_text.substring(0,280) + " [message truncated]";  
    }
		this.errorNode.innerHTML = '';
    this.errorNode.appendChild(dojo.doc.createTextNode(error_text));
    if(args.header_msg)
      this.errorHeaderNode.innerHTML = args.header_msg;
    if(args.hide_retry)
      dojo.style(this.retryButton.domNode, {display: 'none'}); 
    else
      dojo.style(this.retryButton.domNode, {display: 'inline'}); 
    if(args.hide_dismiss)
      dojo.style(this.dismissButton.domNode, {display: 'none'}); 
    else
      dojo.style(this.dismissButton.domNode, {display: 'inline'}); 
	}
});

dojo.declare("nox.ext.apps.coreui.coreui.Progress", [dijit._Widget, dijit._Templated], {
	loadingImage: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "images/progress.gif"),

	templateString: "<div class='noxCoreuiProgress'><img src='${loadingImage.uri}' dojoAttachPoint='loadingNode' style='visibility: hidden;' class='noxCoreuiProgressSpinner'/></div>",

	constructor: function(){
	},

	postCreate: function(){
		this.inherited(arguments);

		this.tooltip = new nox.ext.apps.coreui.coreui.ProgressTooltip({
			connectId: [ this.domNode ],
			disabled: true
		});
		this.errorTooltip = new nox.ext.apps.coreui.coreui.ErrorTooltip({
			id: "noxErrorTooltip",
			connectId: [ this.domNode ],
			disabled: true
		});
		this.connect(this.errorTooltip.retryButton, "onClick", "onRetry");
		this.connect(this.errorTooltip.dismissButton, "onClick", "onDismissError");

		dojo.setSelectable(this.loadingNode, false);

		this.connect(this.domNode, "onclick", "onRefresh");

		var u = nox.ext.apps.coreui.coreui.getUpdateMgr();

		this.connect(u, "onUpdateStart", "onStart");

		if(u._updates_started){
			this.onStart();
		}

		this.connect(u, "onMakeRequest", "onActivity");
		this.connect(u, "onUserFunctionCall", "onActivity");
		this.connect(u, "onCountdownStart", "onIdle");
		this.connect(u, "onResponseProcessingTick", "onProcessingTick");
        this.connect(u, "onUpdateComplete", "onComplete");

		this.connect(nox.ext.apps.coreui.coreui.UpdateErrorHandler, "onError", "onError");
	},

	onStart: function(){
		dojo.style(this.domNode, 'display', 'block');
	},

	onRefresh: function(){
		if(this._activity_started){ return; }
		nox.ext.apps.coreui.coreui.getUpdateMgr().updateNow();
	},

    onRetry: function () {
		if(this._activity_started){ return; }
		this._error = false;
		this.onIdle();
		nox.ext.apps.coreui.coreui.getUpdateMgr().retry_failed_request();
    },

	onIdle: function(){
		if(!this._error){
			dojo.style(this.loadingNode, 'visibility', 'hidden');
			this._activity_started = false;
			dojo.style(this.domNode, "backgroundPosition", "0px 0px");
			dojo.addClass(this.domNode, "noxCoreuiProgressCanRefresh");
			this.tooltip.disable();
			this.errorTooltip.disable();
		}
	},

    onComplete: function() {
        this.onIdle();
        dojo.style(this.domNode, 'display', 'none');
    },

	onActivity: function(){
		if(!this._activity_started){
			this._error = false;
			this._activity_started = true;
			this.tooltip.setPercentage(0);
			dojo.style(this.domNode, "backgroundPosition", "-26px 0px");
			dojo.removeClass(this.domNode, "noxCoreuiProgressCanRefresh");
			dojo.style(this.loadingNode, 'visibility', 'visible');
			this.tooltip.enable();
			this.errorTooltip.disable();
		}
	},

	onError: function(error_text, args){
    if(args == null) 
      args = {}; 

		this._error = true;
		this._activity_started = false;
    this.resume_on_dismiss = false; 
		dojo.style(this.loadingNode, 'visibility', 'hidden');
		this.errorTooltip.setError(error_text,args);
		dojo.style(this.domNode, "backgroundPosition", "-52px 0px");
		dojo.removeClass(this.domNode, "noxCoreuiProgressCanRefresh");
		this.tooltip.disable();
    if(args.validation_error != null && args.validation_error == true) { 
		  // we have to manually suspend the update manager
      nox.ext.apps.coreui.coreui.getUpdateMgr().suspend();
      this.resume_on_dismiss = true; 
    }  
		this.errorTooltip.enable();
    
    // this shows the error tool-tip automatically
    if(args.auto_show == null || args.auto_show == true) 
      this.errorTooltip.open(dojo.byId("progress")); 
	},

	onDismissError: function(){
		this._error = false;
		this.onIdle();
		if(this.resume_on_dismiss) { 
        nox.ext.apps.coreui.coreui.getUpdateMgr().resume();
        this.resume_on_dismiss = false; 
    } else 
		  nox.ext.apps.coreui.coreui.getUpdateMgr().skip_failed_request();
	},

	onProcessingTick: function(in_progress_responses, min_progress){
		this.tooltip.setPercentage(min_progress);
	}
});
