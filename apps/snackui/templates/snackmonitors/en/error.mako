## -*- coding: utf-8 -*-
<%inherit file="monitors-layout.mako"/>

<%def name="page_title()">Server Error</%def>


<%def name="head_js()">
  dojo.addOnLoad(function () {
        nox.webapps.coreui.coreui.UpdateErrorHandler.showError("${msg}", {
          header_msg : "${header_msg}", 
          hide_retry : true 
        });  
  }); 
</%def> 
