## -*- coding: utf-8 -*-

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">${ptype}</%def>

<%def name="head_js()">
  ${parent.head_js()} 
  dojo.addOnLoad(function () {
      // Make the spinner hide on this page 
      // by dropping all reoccurring updates that may happen in the 
      // background.  This is ok, as these pages use no auto-updating
      // via the UpdateManager (but the nox version update causes the 
      // spinner to still be visible). 
      nox.webapps.coreui.coreui.getUpdateMgr()._recurring_updates = [];  
  }); 
</%def> 

## take any parameters in the URL and pass them on to the iframe
<%!
import urllib
%> 
<% 
flat_args = {} 
for k in request.args.keys(): 
  flat_args[k] = request.args[k][-1]
%> 

## This just inherits the layout of a standard page (i.e., header, footer 
## and left-sidebar, and renders an iframe within the content section

<iframe id="listframe" height="575px" width="100%" 
src="/Monitors/${ptype}listOnly?${urllib.urlencode(flat_args)}" > 
 Error: could not load list of ${ptype}.  
</iframe> 
