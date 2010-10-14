dojo.provide("nox.ext.apps.coreui.coreui.Search");

dojo.require("dijit.Menu");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.Button");

dojo.declare("nox.ext.apps.coreui.coreui.Search", [dijit._Widget, dijit._Templated], {
    
    templatePath: dojo.moduleUrl("nox.ext.apps.coreui.coreui", "templates/Search.html"),
    widgetsInTemplate: true,
    
    // search: string
    //    The name to use for the search string when submitting the form
    search: "search",
    
    // subset: string
    //    The name to use for the subset string when submitting the form
    subset: "subset",
    
    // action: string
    //	The form's action => a url
    action: "/Monitors/Search",
    
    // method: string
    //	The form's method => GET/POST
    method: "GET",
    
    // prompt: string
    //	The prefix to use when prompting users
    prompt: "Search ",
    
    // standard construction/destruction methods
    
    _fillContent: function(/* Node */ source){
        this._source = source;
    },

    startup: function(){
        if(this._started){ return; }
        
        // the child widget from srcNodeRef is the dropdown widget.  Insert it in the page DOM,
        // make it invisible, and store a reference to pass to the popup code.
        if(!this.dropDown){
            var dropDownNode = dojo.query("[widgetId]", this._source)[0];
            this.dropDown = dijit.byNode(dropDownNode);
            delete this._source;    // remove unnecessary reference
        }
        dijit.popup.prepare(this.dropDown.domNode);

        this.reflectState(true);
        
        this.events = [
            dojo.connect(this.searchString, "onfocus", this, "onSearchFocus"),
             dojo.connect(this.searchString, "onblur",  this, "onSearchBlur")
        ];

        this.inherited(arguments);
    },

    destroyDescendants: function(){
        dojo.forEach(this.events, dojo.disconnect);
        if(this.dropDown){
            this.dropDown.destroyRecursive();
            delete this.dropDown;
        }
        this.inherited(arguments);
    },
    
    onBlur: function(){
        // summary: called magically when focus has shifted away from this widget and it's dropdown
        this._closeDropDown();
        // don't focus on button.  the user has explicitly focused on something else.
        this.inherited(arguments);
    },
    
    // the dropdown management

    _toggleDropDown: function(){
        // summary: toggle the drop-down widget; if it is up, close it, if not, open it
        dijit.focus(this.changeFilterNode);
        if(!this.dropDown){ return; }
        this[this._opened ? "_closeDropDown" : "_openDropDown"]();
    },

    _openDropDown: function(){
        if(this._opened){ return; }
        this._opened = dojo.map(this.dropDown.getDescendants(), function(x){ return x.checked; });
        dijit.popup.open({
            parent: this,
            popup:  this.dropDown,
            around: this.changeFilterNode,
            orient:
                // TODO: add user-defined positioning option, like in Tooltip.js
                this.isLeftToRight() ? {'BL':'TL', 'BR':'TR', 'TL':'BL', 'TR':'BR'}
                : {'BR':'TR', 'BL':'TL', 'TR':'BR', 'TL':'BL'},
            onExecute: dojo.hitch(this, "onExecute"), 
            onCancel:  dojo.hitch(this, "_closeDropDown"),
            onClose:   dojo.hitch(this, function(){ this._opened = null; })
        });
        if(typeof this.dropDown.focus == "function"){
            this.dropDown.focus();
        }
    },
    
    _closeDropDown: function(){
        if(this._opened){
            dijit.popup.close(this.dropDown);
            this._opened = null;            
        }
    },

    // business logic
    
    reflectState: function(/* Boolean */ empty){
        this.isEmpty = empty;
        if(empty){
            dojo.addClass(this.domNode, "empty");
            dojo.some(this.dropDown.getDescendants(), function(widget){
                if(widget.attr("checked")){
                    this.searchString.value = this.prompt + widget.attr("label");
                    return true;
                }
                return false;
            }, this);
        }else{
            dojo.removeClass(this.domNode, "empty");
            this.searchString.value = "";
        }
    },
    
    onExecute: function(){
        var checkboxes = this.dropDown.getDescendants(), current,
            state = dojo.map(checkboxes, function(widget, i){
                return widget.attr("checked") ^ this._opened[i];
            }, this);
        // uncheck old settings
        dojo.forEach(checkboxes, function(widget, i){
            widget.attr("checked", state[i]);
            if(state[i]){
                current = widget.attr("label");
            }
        });
        this._closeDropDown();
        if(this.isEmpty){
            this.searchString.value = this.prompt + current;
        }
    },
    
    onChangeFilter: function(){
        this._toggleDropDown();
    },
    
    onSearchFocus: function(){
        if(this.isEmpty){
            this.reflectState(false);
        }
    },
    
    onSearchBlur: function(){
        if(this.searchString.value){
            this.isEmpty = false;
        }else{
            this.reflectState(true);
        }
    },
    
    onReset: function(){
        this.reflectState(true);
    },
    
    onSubmit: function(){
        // fill out internal inputs
        if(this.isEmpty){
            this.searchString.value = "";
        }
        var checkboxes = this.dropDown.getDescendants(), current;
        dojo.some(checkboxes, function(widget){
            if(widget.attr("checked")){
                this.subsetString.value = widget.attr("label");
                return true;
            }
            return false;
        }, this);
        return true;
    },
    
    submit: function(){
        // summary:
        //        programmatically submit form if and only if the `onSubmit` returns true
        if(!(this.onSubmit() === false)){
            this.containerNode.submit();
        }
    }
});
