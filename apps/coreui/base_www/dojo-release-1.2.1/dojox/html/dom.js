dojo.provide("dojox.html.dom");


(function(){
	// borrowed from dojo._base.html:
	var handyContainer = null;
	dojo.addOnWindowUnload(function(){
		handyContainer = null; //prevent IE leak
	});

	dojox.html.dom.create = function(/*String*/ frag, /*String|Node?*/ contents){
		// summary: a helper function to create a DOM node from a tag or an HTML snippet.
		// frag: String: the tag name for the node, or the well-formed HTML snippet

		var t = new dojo.NodeList(), c;
		try{
			if(frag.charAt(0) != "<"){
				// create from a tag
				var node = dojo.doc.createElement(frag);
				if(contents){
					if(typeof contents == "string"){
						node.innerHTML = contents;
					}else{
						node.appendChild(contents);
					}
				}
				t.push(node);
				return t;	// dojo.NodeList
			}
			
			// make sure we have a container ready
			if(!handyContainer || handyContainer.ownerDocument != dojo.doc){
				handyContainer = dojo.doc.createElement("div");
			}
		
			// instantiate the HTML snippet
			handyContainer.innerHTML = frag;
			// transfer them to the NodeList
			c = handyContainer.childNodes;
			while(c.length){
				t.push(handyContainer.removeChild(c[0]));
			}
		}catch(e){
			// clean the container
			handyContainer.innerHTML = "";
		}
		return t;	// dojo.NodeList
	};

	dojox.html.dom.createElement = function(
	    /*String|Node*/ tag, /*Object?*/attrs,
	    /*Node?*/ parent, /*String?*/ pos
	){
	    var node = typeof tag == "string" ? 
			(tag.charAt(0) == "#" ? dojo.byId(tag.substr(1)) : dojo.doc.createElement(tag)) :
			tag;
	    if(node){
	        if(attrs){
	            dojo.attr(node, attrs);
	        }
	        if(parent){
	            dojo.place(node, parent, pos);
	        }
	    }
	    return node;    // Node
	}

	var NodeWrapper = function(node){ this.node = node; };
	// add chainable methods
	dojo.forEach(
		["attr", "style", "setSelectable", "removeAttr", "addClass", "removeClass", "toggleClass"],
		function(name){
			NodeWrapper.prototype[name] = function(){
				dojo[name].apply(null, dojo._toArray(arguments, 0, [this.node]));
				return this;
			};
		}
	);
	// add normal methods
	dojo.forEach(
		["getComputedStyle", "contentBox", "marginBox", "coords", "hasAttr", "hasClass", "connect"],
		function(name){
			NodeWrapper.prototype[name] = function(){
				return dojo[name].apply(null, dojo._toArray(arguments, 0, [this.node]));
			};
		}
	);
	// add syntactic sugar for DOM events
	dojo.forEach(
		["blur", "focus", "click", "keydown", "keypress", "keyup", "mousedown",
		"mouseenter", "mouseleave", "mousemove", "mouseout", "mouseover",
		"mouseup", "submit", "load", "error"],
		function(name){
			var on = "on" + name;
			NodeWrapper.prototype[on] = function(a, b){
				return this.connect(on, a, b);
			};
		}
	);
	// place
	NodeWrapper.prototype.place = function(ref, pos){
		dojo.place(this.node, ref instanceof NodeWrapper ? ref.node : ref, pos);
		return this;
	};
	// destroy
	NodeWrapper.prototype.destroy = function(){ dojo._destroyElement(this.node); this.node = null; };
	
	dojox.html.dom.element = function(
	    /*String|Node*/ tag, /*Object?*/attrs,
	    /*Node?*/ parent, /*String?*/ pos
	){
	    var node = typeof tag == "string" ? 
			(tag.charAt(0) == "#" ? dojo.byId(tag.substr(1)) : dojo.doc.createElement(tag)) :
			(tag instanceof NodeWrapper ? tag.node : tag);
	    if(node){
	        if(attrs){
	            dojo.attr(node, attrs);
	        }
	        if(parent){
	            dojo.place(node, parent instanceof NodeWrapper ? parent.node : parent, pos);
	        }
	    }
	    return new NodeWrapper(node);    // NodeWrapper
	}
})();
