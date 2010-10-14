dojo.provide("nox.ext.apps.coreui.coreui.simple_config"); 

dojo.require("dojo.io.iframe"); 
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr"); 
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler"); 

coreui = nox.ext.apps.coreui.coreui; 

dojo.declare("nox.ext.apps.coreui.coreui.simple_config", [], {

  // these are the error handlers used when we PUT config data
  // to the server. 
  _put_error_handlers : { 
              401: function(response, ioArgs, item, itemType) {
                coreui.UpdateErrorHandler.showError(
                    "You are not currently logged in. " + 
                    " Log in via another browser window " +
                    " to avoid losing unsaved changes on the current page.", 
                    { header_msg: "Updating Configuration Failed:" } );
             }, 
             400:  function(response, ioArgs, item, itemType) { 
                coreui.UpdateErrorHandler.showError(response.responseText, 
                  { header_msg: "Updating Configuration Failed: Bad Request:" });  
             }, 
             500:  function(response, ioArgs, item, itemType) { 
                coreui.UpdateErrorHandler.showError(response.responseText, 
                  { header_msg: "Updating Configuration Failed: Server Error:" }); 
             }
        }, 
  
  _get_error_handlers : { 
             400:  function(response, ioArgs, item, itemType) { 
                coreui.UpdateErrorHandler.showError(response.responseText, 
                { header_msg: "Retrieving Configuration Data Failed: Bad Request:"}); 
             }, 
             500:  function(response, ioArgs, item, itemType) { 
                coreui.UpdateErrorHandler.showError(response.responseText, 
              { header_msg: "Retrieving Configuration Data Failed: Server Error:" }); 
             }
        }, 

  // dojo.formToObject() ignores checkbox
  // entries if they are not selected, so we add them here
  formToObject : function(form_id) { 
    var f = dojo.formToObject(form_id); 
    var q_str = "#"+form_id+ " input[type='checkbox']"; 
    dojo.forEach(dojo.query(q_str), function(x) { 
          if(x.checked) 
              f[x.name] = 1;
          else
              f[x.name] = 0; 
        } 
    );

    // convert integer types to native Javascript integers
    q_str = "#"+form_id+ " input[type='integer']"; 
    dojo.forEach(dojo.query(q_str), function(x) { 
            f[x.name] = parseInt(f[x.name]);
        } 
    );

    return f; 
  }, 
  
  submit_form : function(form_id) { 
    this.submit_form_with_callback(form_id, null); 
  },

  submit_form_with_callback : function(form_id, on_load) { 
    var f = this.formToObject(form_id); 
    if(! f["section_id"] ) { 
      console_log("Error, form must have element with id 'section_id'"); 
      return; 
    }
    var section_id = f["section_id"];
    delete f.section_id; 

    // remove any form fields that start with 'ignore_'
    for (key in f) { 
      if (key.indexOf("ignore_") == 0) 
        delete f[key]; 
    }

    this.submit_config(section_id,f,on_load); 
  }, 

  submit_config : function(section_id, values,on_load) { 
    var put_obj = { 
        url: "/ws.v1/config/" + section_id,
        headers: { "content-type" : "application/json" },
        putData: dojo.toJson(values),
        load : dojo.hitch(this, function() { 
          this._signal_update_success("Update Successful");
          if(on_load) 
            on_load(arguments); 
        }), 
        timeout: 1000000, // 1 second
        errorHandlers: this._put_error_handlers 
    };
    this._set_status_text("Update in Progress..."); 
    nox.ext.apps.coreui.coreui.getUpdateMgr().rawXhrPut(put_obj); 
  }, 

  submit_file_form : function(form_id, cb) { 
    var f = this.formToObject(form_id); 
    if(! f["section_id"] ) { 
      console_log("Error, form must have element with id 'section_id'"); 
      return; 
    }
    var section_id = f["section_id"];
    delete f.section_id;
    dojo.io.iframe.send(
      {
        form : form_id,
        contentType : "multipart/form-data", 
        //FIXME: i get an internal dojo error if i set this to application/json
        //handleAs : "application/json",
        handleAs : "html", 
        url: "/ws.v1/config_base64/" + section_id,
        // FIXME: unfortunately, load is called even when we fail.
        load : function(response, ioArgs) {
          if (cb != null) {
            cb();
          }
          return response;
        },
        errorHandlers: this._put_error_handlers 
      } 
    ); 
  }, 

  _checkbox_value : function(key,on_or_off){
    if(on_or_off == 1) return true;
  
    if(on_or_off != 0) { 
      console_log("error, field '"+key+"' should"
                + " be either 0 or 1");
    } 
    return false; 
 },

    // clear the form.  this is dirty. 
 clear_form : function(form_id) { 
    var form_dom = dojo.byId(form_id); 
    for (key in form_dom) {
      if(! form_dom[key] )
        continue; 
      var type = form_dom[key].type; 
      if(! type ) 
        continue; 
      if(type == "text") { 
        form_dom[key].value = "";
      } else if (type == "checkbox") { 
        form_dom[key].checked = false; 
      } else if (type == "select-one") {
        form_dom[key].selectedIndex = -1; 
      }      
    } 

 }, 

 fill_form : function(data_obj, form_id) {
    var form_dom = dojo.byId(form_id);
    this.clear_form(form_id); // help flush out bugs
    for (key in data_obj) { 
      if(!form_dom[key]) {  
        console_log("form has no field with name " + key); 
        continue;
      }
      var value = data_obj[key]; 
      var type = form_dom[key].type; 
      if(type == "text" || type == "textarea" || type == "hidden") { 
        form_dom[key].value = value;
      } else if (type == "checkbox") { 
        form_dom[key].checked = this._checkbox_value(key,value)
      } else if (type == "select-one") {
        for (i = 0; i < form_dom[key].options.length; i++) {
          var op = form_dom[key].options[i].innerHTML; 
          var trimmed = op.replace(/^\s+|\s+$/g, '') ;
          if(trimmed == value){  
            form_dom[key].selectedIndex = i; 
            break; 
          } 
        }
      } else { 
        console_log("element has unknown type '"+type+"'"); 
      } 
    }
 }, 
  
  fill_form_from_config : function(form_id, cb) { 
    var form_dom = dojo.byId(form_id); 
    var sec_id = form_dom["section_id"].value; 
    var oncomplete = dojo.hitch(this, function(response,ioArgs) { 
            this.fill_form(response, form_id); 
            cb();
        });
    this.get_config_as_object(sec_id,oncomplete); 
  },
  
  get_config_as_object : function(section_id, cb) {
    this._set_status_text("Loading Configuration Data..."); 
    nox.ext.apps.coreui.coreui.getUpdateMgr().xhrGet({ 
      url : "/ws.v1/config/" + section_id,
      load : dojo.hitch(this, function (response, ioArgs) {
              this._signal_update_success("Data Successfully Loaded");
              cb(response); 
             }), 
      timeout : 1000000, 
      handleAs : "json",
      errorHandlers : this._get_error_handlers 
    }); 
  }, 
  
  _set_status_text : function(msg) { 
        var status_node = dojo.byId("simple_config_status"); 
        if(status_node != null) { 
          status_node.innerHTML =  msg; 
        } 
  }, 

  _signal_update_success : function(msg) { 
        var status_node = dojo.byId("simple_config_status"); 
        if(status_node != null) { 
          status_node.style.opacity = 1.0; 
          // not using CSS, b/c we don't know what CSS files might be 
          // used on the HTML page
          status_node.innerHTML = 
            "<span><font color='green'>" + msg + "</font></span>"; 
          var anim = dojo.fadeOut({node: status_node, duration : 5000 });
          anim.play(); 
        } 
 } 
}); // end class


(function () {
    var simple_config = null;
    nox.ext.apps.coreui.coreui.getSimpleConfig = function () {
        if (simple_config == null) {
            simple_config = new nox.ext.apps.coreui.coreui.simple_config();
        }
        return simple_config;
    }
})();
