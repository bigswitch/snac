## -*- coding: utf-8 -*-
<%inherit file="base.mako"/>

<%def name="page_title()"></%def>
<%def name="head_js()">
  ${parent.head_js()} 
  dojo.addOnLoad(function () {
        top.nox.ext.apps.coreui.coreui.UpdateErrorHandler.showError("${msg}", {
          header_msg : "${header_msg}", 
          hide_retry : true 
        });  
  }); 
</%def> 

