dojo.provide("nox.ext.apps.coreui.monitorsui.SwitchPortNatConfig");

dojo.require("dijit._Widget");
dojo.require("dijit.Dialog");
dojo.require("dijit._Templated");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.form.NumberTextBox");
dojo.require("nox.ext.apps.coreui.coreui.simple_config"); 
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler"); 

dojo.declare("nox.ext.apps.coreui.monitorsui.SwitchPortNatConfig", [ dijit._Widget, dijit._Templated ], {
    templatePath: dojo.moduleUrl("nox.ext.apps.coreui.monitorsui", 
                                  "templates/SwitchPortNatConfig.html"),
    widgetsInTemplate: true,

    name : null, 
    text_field_names : [ "ipv4_external_prefix", "ipv4_internal_prefix", "tcp_ports","udp_ports","mac_to_rewrite" ], 
    radio_field_types : [ "srcip", "tcp", "udp","icmp","rewrite" ], 
    current_config : [], 

    _get_radio_value: function(proto) { 
      var val = "all"; 
      dojo.forEach(["all","some","none"], function(x) { 
          var rbutton = dijit.byId(proto + "_" + x);
          if (rbutton != null && rbutton.checked) 
            val = x; 
        } ); 
      return val; 
    }, 
    
    _set_radio_values : function(proto, cur_val) { 
      dojo.forEach(["all","some","none"], function(x) { 
          var rbutton = dijit.byId(proto + "_" + x);
          if (rbutton != null) 
            rbutton.setChecked(cur_val == x); 
        } ); 
    },

    _set_widget_values: function () {
        if(this.current_config.length == 0)
          return; 

        for(i = 0; i < this.text_field_names.length; i++) { 
            v = this.current_config[i];
            this[this.text_field_names[i]].setValue(v);
        } 
        // don't reset i value...
        dojo.forEach(this.radio_field_types, function(proto) {
          this._set_radio_values(proto, this.current_config[i]);
          i++; 
          },this); 
    },

    _cancel: function () {
      this._set_modified(false); 
      this._set_widget_values();
      if (this.current_config.length == 0) 
        this._set_visible(false); 
    },

    _validate_port_list: function(proto) {

        var val = this[proto + "_ports"].value; 
        if(val == "") { 
          var type = this._get_radio_value(proto);
          if(type == "some") {
            this._set_err_msg("Must specify at least one " + proto + " port.");
            return false; 
          }
          return true; 
        } 

        var port_list = val.split(",");
        for(var i = 0; i < port_list.length; i++) { 
          var p = port_list[i];
          if(p < 1 || p > 65535) {  
            this._set_err_msg("'" + p + "' is not a valid " + proto + " port.");            
            return false;
          } 
        } 
        return true; 
    },

    _set_err_msg : function(msg) { 
          dojo.byId("error_msg_div").innerHTML = msg; 
    }, 

    _done: function () {
            
        for(i = 0; i < this.text_field_names.length; i++) {
                var field_name = this.text_field_names[i];
                if(!this[field_name].validate()) {
                  this[field_name]._hasBeenBlurred = true; 
                  this[field_name].focus(); 
                  return; 
                }
        }
        if (this.ipv4_external_prefix.getValue() == "0.0.0.0") {   
          this._set_err_msg("0.0.0.0 is not a valid IP address");
          return false; 
        }

        var tcp_type = this._get_radio_value("tcp");
        var udp_type = this._get_radio_value("udp");
        var icmp_type = this._get_radio_value("icmp");
        var srcip_type = this._get_radio_value("srcip");
        if(srcip_type == "some" && this['ipv4_internal_prefix'].value == "") { 
          this._set_err_msg("Must specify an IP prefix for 'Hosts to NAT'"); 
          return false; 
        }
        if(tcp_type == "none" && udp_type == "none" && icmp_type == "none"){
          this._set_err_msg("NAT must be enabled for at least one protocol"); 
          return false; 
        }
        if (!this._validate_port_list("tcp"))
          return false; 
        if (!this._validate_port_list("udp"))
          return false;
        var rewrite_mac = this._get_radio_value("rewrite"); 
        if (rewrite_mac == "some" && this.mac_to_rewrite.getValue() == "") { 
            this._set_err_msg("Must specify a MAC for rewriting"); 
            return false; 
        }  

        this.current_config = []; 
        dojo.forEach(this.text_field_names, dojo.hitch(this,function(field_name) {
              this.current_config.push(this[field_name].value + ""); 
            }));
        dojo.forEach(this.radio_field_types, function(proto) { 
              this.current_config.push(this._get_radio_value(proto)); 
            }, this); 

      var cb = dojo.hitch(this, function() {
              // FIXME: make changes all or nothing?
              this._set_modified(false);

              var cb = dojo.hitch(this, "_add_new_policy_rule") 
              this._setup_policy_rule1(cb); 
          });
      var config = {}; 
      config[this.name] = this.current_config; 
      this.simple_config.submit_config("switch_nat_config", config,cb); 
    },

    policy_error: function() { 
      nox.ext.apps.coreui.coreui.UpdateErrorHandler.showError(
                              "Error while changing network policy", 
                        { header_msg : "Failed to Change NAT Configuration:", 
                          hide_retry : true 
                        });
    },  

    _setup_policy_rule1: function(cb) { 
          this._do_policy_xhr("GET", "/ws.v1/policy", 
            dojo.hitch(this,"_setup_policy_rule2",cb), {} ); 
    }, 

    _setup_policy_rule2: function(cb, response, ioArgs) {
        this.latest_policy_id = response["policy_id"]; 
        var url = "/ws.v1/policy/" + response["policy_id"] +  "/rules";

        this._do_policy_xhr("GET", url, cb, {} ); 
    },

  _generate_proto_text: function(proto,proto_num,type) {
        var result = "nwproto(" + proto_num + ")"; 
        if(type == "some") { 
          var port_str_list = ""; 
          if(this[proto + "_ports"] != null) 
            port_str_list = this[proto + "_ports"].getValue(); 
          var port_text_arr = [];
          if(port_str_list != "") { 
            var port_list = port_str_list.split(","); 
            for(var i = 0; i < port_list.length; i++) { 
              var p = port_list[i]; 
              port_text_arr.push("tpdst(" + p + ")"); 
            } 
          }
          var all_ports_txt = port_text_arr.join(" | "); 
          if(all_ports_txt != "")
            result = "(" + result + " ^ (" + all_ports_txt + "))";
        }
        return result; 
  }, 

  _generate_policy_text: function() {
   
        // IP proto values
        var ICMP_PROTO = 1; 
        var TCP_PROTO = 6; 
        var UDP_PROTO = 17;
        
        var front_text = "nat('" + this.name + "')";
        
        // For the MAC rewrite hack
        var rewrite_type = this._get_radio_value("rewrite");
        if(rewrite_type == "some") { 
          front_text = "nat('" + this.name + "','" + 
              this.mac_to_rewrite.getValue() + "')"; 
        }
        var prefix_type = this._get_radio_value("srcip");
        var prefix_str = "";
        if (prefix_type != "all") {
            prefix_str = this.ipv4_internal_prefix.getValue();
        }
        var udp_str_list = this.udp_ports.getValue();
      
        var tcp_type = this._get_radio_value("tcp");
        var udp_type = this._get_radio_value("udp");
        var icmp_type = this._get_radio_value("icmp");
        var proto_text_arr = [];
        var res = ""; 
        if(tcp_type != "none") { 
          res = this._generate_proto_text("tcp",TCP_PROTO,tcp_type);
          proto_text_arr.push(res);
        }
        if(udp_type != "none"){ 
          res = this._generate_proto_text("udp",UDP_PROTO,udp_type);
          proto_text_arr.push(res);
        }
        if(icmp_type != "none") { 
          res = this._generate_proto_text("icmp",ICMP_PROTO,icmp_type);
          proto_text_arr.push(res);
        }  
        var proto_rule_str = proto_text_arr.join(" | "); 
        var prefix_rule_str = (prefix_str.length > 0)  ?  
                      "subnetsrc('" + prefix_str + "')" : ""; 
        var right_side = proto_rule_str; 
        if(prefix_rule_str != "" && proto_rule_str != "") 
          right_side = prefix_rule_str + "^ (" + proto_rule_str + ")";
        if (right_side == "")
          right_side = "True"; 

        return front_text + " <= " + right_side; 
    }, 

    _add_new_policy_rule: function(response, ioArgs) {
    
        var front_text = "nat('" + this.name + "'";
        var policy_text = this._generate_policy_text(); 
        var new_rule = {
              "description" :   "NAT rule for location'" + this.name + "'",
              "actions" : [ { "args" : [], "type": "allow" } ],
              "condition" : { "pred": true, "args" : [] },
              "policy_id" : this.latest_policy_id,
              "user" : null,
              "timestamp" : null,
              "text" : policy_text,
              "priority" : 1,
              "comment" : "auto-generated by switchport page",
              "exception" : false,
              "expiration" : 0.0,
              "rule_type" : "nat",
              "protected" : true
          };
       
       
        // See if there's already a nat rule for this location
        var match_index = -1; 
        for(var i = 0; i < response.length; i++) {
           if (response[i].text == policy_text) 
             return; // policy is unchanged, we're done 
           if (response[i].text.indexOf(front_text) != -1) { 
              match_index = i; 
              break; 
           }
        }   
        if(match_index != -1) 
          response[i] = new_rule; // overwrite old role for this location
        else 
          response.push(new_rule);
        this._do_policy_xhr("POST", "/ws.v1/policy", 
            dojo.hitch(this, "_policy_change_done"), 
                    { policy_id : this.latest_policy_id,
                          rules : response }); 

    },
     
    _remove_policy_rule: function(response, ioArgs) { 
        var front_text = "nat('" + this.name + "'";
        var new_policy = []; 
        for(var i = 0; i < response.length; i++) {
           if (response[i].text.indexOf(front_text) == -1) { 
              new_policy.push(response[i]); 
           }
        }   
        this._do_policy_xhr("POST", "/ws.v1/policy", 
            dojo.hitch(this, "_policy_change_done"), 
                    { policy_id : this.latest_policy_id,
                          rules : new_policy }); 

    },

    _policy_change_done: function(response, ioArgs) { }, 
   
    _do_policy_xhr: function(method, url, onLoad, data) {
        nox.ext.apps.coreui.coreui.getUpdateMgr().xhr(method, {
            url: url,
            headers: { "content-type": "application/json" },
            postData: dojo.toJson(data),
            handleAs: "json", 
            load: onLoad, 
            error: this.policy_error, 
            timeout: 30000
        });
    },
 
    _set_visible : function(enabled) {
      if(enabled)
        x = "none", y = "block"; 
      else 
        x = "block", y = "none"; 
      dojo.style(dojo.byId("enabled_div"), {display: y}); 
      dojo.style(dojo.byId("disabled_div"), {display: x}); 
      dojo.style(dojo.byId("config_div"), {display:  y});
    },

    _radio_changed : function(proto, val, selected) {
      this._set_modified(true); 
      if (val == "some" || !selected) 
        return;
      if(proto == "srcip") 
        this.ipv4_internal_prefix.setValue(""); 
      else if(proto == "tcp") 
        this.tcp_ports.setValue(""); 
      else if(proto == "udp") 
        this.udp_ports.setValue(""); 
      else if(proto == "rewrite") 
        this.mac_to_rewrite.setValue(""); 
    }, 

    _textbox_changed : function(field_name) { 
      this._set_modified(true); 
      var radio_val = "some"; 
      var proto; 
      if (field_name == "ipv4_internal_prefix")
        proto = "srcip";
      else if (field_name == "tcp_ports") 
        proto = "tcp"; 
      else if (field_name == "udp_ports") 
        proto = "udp"; 
      else if (field_name == "mac_to_rewrite")
        proto = "rewrite";
      else  { 
        //  not all fields have a radio button
        return;
      } 
      this._set_radio_values(proto, radio_val); 
    }, 
    
    _set_modified : function(modified) {
      if(modified) {  
        x = "block";
      } else { 
        x = "none";
      }
     dojo.byId("error_msg_div").innerHTML = ""; 
     this.addBtn.attr('disabled', !modified);
     this.cancelBtn.attr('disabled', !modified);
    },

    _enable_nat : function() { 
      // we default to natting everything
      dojo.forEach(this.radio_field_types, function(proto) {
          if(proto == "rewrite") 
            this._set_radio_values(proto,"none"); 
          else 
            this._set_radio_values(proto, "all"); 
      }, this); 
      this._set_visible(true);
      this._set_modified(true); 
    }, 

    _disable_nat : function() {
      if(this.current_config.length > 0) {
        this.current_config = [];
        this.ipv4_external_prefix.setDisplayedValue("0.0.0.0");
        var cb = dojo.hitch(this, function(all_switches_config) { 
            var cb = dojo.hitch(this, "_remove_policy_rule") 
            this._setup_policy_rule1(cb); 
            this._finish_startup(all_switches_config);
            }); 
        config = {}; 
        config[this.name] = []; 
        this.simple_config.submit_config("switch_nat_config",config,cb); 
      }else { 
        this._cancel(); 
      }
    }, 

    startup: function () {
        this.inherited("startup", arguments);

        dojo.connect(this.addBtn, "onClick", this, "_done");
        dojo.connect(this.cancelBtn, "onClick", this, "_cancel");
        this._set_modified(false); 
        // setup general enable / disable links 
        dojo.byId("disable_link").onclick = dojo.hitch(this,"_disable_nat"); 
        dojo.byId("enable_link").onclick = dojo.hitch(this,"_enable_nat");

        // detect modifications to any field
        dojo.forEach(this.text_field_names, function(field_name) {
                dojo.connect(this[field_name].domNode,"keypress",
                            dojo.hitch(this,"_textbox_changed",field_name)); 
            }, this); 
        dojo.forEach(this.radio_field_types, function(proto) {
          dojo.forEach(["all","some","none"], function(x) { 
            var rbutton = dijit.byId(proto + "_" + x);
            if (rbutton != null) {  
              dojo.connect(rbutton,"onChange",
                dojo.hitch(this,"_radio_changed", proto, x)); 
            }
          },this); 
        },this);

        this.simple_config = nox.ext.apps.coreui.coreui.getSimpleConfig();
        var cb = dojo.hitch(this, "_finish_startup"); 
        this.simple_config.get_config_as_object("switch_nat_config", cb); 
    },

    _finish_startup : function(all_switches_config) {
        if(this.port_name == "of0") { 
          this._show_of0_error_msg(); 
          return;
        } 

        if(all_switches_config[this.name] != null) { 
          this.current_config = all_switches_config[this.name];
        } else
          this.current_config = []; 
        this._set_widget_values();
        this._set_modified(false); 
        this._set_visible(this.current_config.length > 0);
  }, 
  
  _show_of0_error_msg: function() { 
      dojo.style(dojo.byId("of0_error_msg"), {display: "block"}); 
      dojo.style(dojo.byId("main_content"), {display: "none"}); 
  }
});
