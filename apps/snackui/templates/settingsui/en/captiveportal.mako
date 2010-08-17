## -*- coding: utf-8 -*-

<%inherit file="settings-layout.mako"/>
<%def name="page_title()">Captive Portal Settings</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/webapps/coreui/coreui/ItemInspector.css";
  @import "/static/nox/ext/apps/snackui/settingsui/directories.css";
</%def>

<%def name="dojo_requires()">
  ${parent.dojo_requires()}
  dojo.require("dijit.form.ComboBox");
  dojo.require("dijit.form.TextBox");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.Dialog");
  dojo.require("nox.webapps.coreui.coreui.simple_config"); 
  dojo.require("dijit.TitlePane");
  

</%def>

<%def name="head_js()">

  function host_from_url(url) { 
    try { 
      var arr = url.split("/");
      return arr[2]; 
    } catch(e) { 
      console_log("error parsing URL: " + url_elem.value); 
    }
    return "unknown"; 
  }
  function url_from_host(host) { 
    return "https://" + host + "/cp/";
  } 


  function after_load() { 
    // change redir_url from URL to just a DNS/Name or IP:
    var f = document.getElementById('main_form');
    f.server_name.value = host_from_url(f.redir_url.value); 
    updatePreview(); 
  }

  function before_save() { 
      var f = document.getElementById('main_form');
      f.redir_url.value = url_from_host(f.server_name.value); 
  } 

  // assumes the 'redir_url' field is a hostname, not a url
  function updatePreview(){
    iframeurl = document.getElementById('main_form').redir_url.value;
    if (iframeurl) {
        iframeurl = iframeurl + "?preview=1";
    }
    else {
        iframeurl = "about:blank";
    }
    document.getElementById('previewIframe').src=iframeurl;
  }
  
  var f = function() { 
    nox.webapps.coreui.coreui.getSimpleConfig().fill_form_from_config("main_form", after_load);
  } 
  dojo.addOnLoad(f);
</%def>

<%def name="head_css()">
  tr {
    vertical-align : top;
  }
</%def>
## ---------------------------------------------------------------------------

<div dojoType="dijit.TitlePane" title="Main Captive Portal Settings">
        <button dojoType="dijit.form.Button">
          Commit Changes
          <script type="dojo/method" event="onClick">
            before_save();             
            nox.webapps.coreui.coreui.getSimpleConfig().submit_form_with_callback("main_form", updatePreview);
          </script>
        </button> 
        <span id="simple_config_status"></span>  
    <p>Please note: No changes are sent to the server until 
        &ldquo;Commit Changes&rdquo; is clicked.</p>
    <br> 
    <br> 
  <form id="main_form"> 
  <input type="hidden" name="section_id" value="captive_portal_settings" /> 
   <table class="item-inspector">
   <tr> 
   <td class="item-inspector-label" align="top" > Captive Portal Web Server:</td>
   <td><input type="text" name="server_name" value="" size="39"/>  </td>
   <input type="hidden" name="redir_url" value="" />
   </tr>
   <tr>
   <td  class="item-inspector-label"  > Authentication Timeout (Minutes):</td> 
   <td><input type="text" name="hard_timeout_minutes" value="" size="4"/>  </td>
   </tr>
   <tr>
   <td  class="item-inspector-label"  > Authentication Idle Timeout (Minutes):</td> 
   <td><input type="text" name="soft_timeout_minutes" value="" size="4"/>  </td>
   </tr>
   <tr>
   <td  class="item-inspector-label"  > Organization Name:</td><td> <input type="text" name="org_name" value="" size="39"/> </td> 
   </tr>
   <tr>
   <td  class="item-inspector-label" > Banner Message:</td> <td> <textarea cols="45" rows="5" name="banner"> 
    </textarea> 
   </td>
   </tr>
   <tr> 
  <td  class="item-inspector-label"  > Custom CSS: </td> 
  <td> <textarea cols="45" rows="7" name="custom_css" > </textarea> 
   </tr>
   </table> 
  </form> 
</div> 
<div dojoType="dijit.TitlePane" title="Modify Captive Portal Banner Image">

        <button dojoType="dijit.form.Button">
          Upload Image 
          <script type="dojo/method" event="onClick">
            dijit.byId("change_image_dialog").show(); 
          </script>
        </button> 
    
</div> 
<div dojoType="dijit.TitlePane" title="Current Portal Page">
     <iframe id="previewIframe" src="about:blank" width="90%" height="400">
       Preview is not supported by your web browser.
     </iframe>
</div>  
## popup to modify the captive portal image  -----------------------------------
 
  <div id="change_image_dialog" dojoType="dijit.Dialog">
    <form id="image_form" method="post" enctype="multipart/form-data"> 
      <input type="hidden" name="section_id" value="captive_portal_settings" /> 
      <label for="file">New Portal Image: </label>
      <input type="file" name="banner_image"> 
        <br/>  
        <button dojoType="dijit.form.Button" id="submit_add">
          Upload File
          <script type="dojo/method" event="onClick">
            nox.webapps.coreui.coreui.getSimpleConfig().submit_file_form("image_form", updatePreview); 
            dijit.byId("change_image_dialog").hide(); 
          </script>
        </button>
        </form> 
  </div>
