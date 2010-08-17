## -*- coding: utf-8 -*-
<%inherit file="base.mako"/>

<%def name="head_css()"> 
  @import "/static/nox/ext/apps/snackui/snackmonitors/PrincipalList.css";
</%def> 

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

<%def name="dojo_requires()">
   ${parent.dojo_requires()} 
   dojo.require("dijit.layout.ContentPane");
   dojo.require("dijit.layout.BorderContainer");
   dojo.require("dijit.form.Button");
   dojo.require("dijit.Tooltip");
   dojo.require("nox.netapps.directory.directorymanagerws.PrincipalListFilter"); 
   dojo.require("nox.netapps.directory.directorymanagerws._Principal"); 
</%def>

<%def name="head_js()">
  ${parent.head_js()} 
  //HACK: within an iframe, we don't have our own Progress widget
  // for reporting errors.  Thus, we must use the one from the outer frame. 
  dojo.addOnLoad(function () {
          nox.webapps.coreui.coreui.UpdateErrorHandler.showError =
              top.nox.webapps.coreui.coreui.UpdateErrorHandler.showError;

  }); 
  
  // because we are in an iframe, links will only change the content of
  // that iframe.  if we want to change the link of the entire page, we 
  // must use this function, which refers to the outermost window
  function change_main_page(url) { 
    top.location = url; 
  } 
</%def>

## we have a couple def's for content that is sprinkled into all of the 
## principal list pages

<%def name="clear_btn_html()"> 
<button id="clear_btn" dojoType="dijit.form.Button" style="float: left;">
<img src="/static/nox/webapps/coreui/coreui/images/clearFilterButton.png" alt="Clear Filters" />
<span dojoType="dijit.Tooltip" connectId="clear_btn" label="Clear Filters"></span> 
</button>
</%def> 
<%def name="refresh_link()">
<span style="float: right; size: 110em;"><a href="javascript:pFilter._apply_filter()"> refresh results </a></span> 
<br>
<br> 
</%def> 

<%def name="status_select_box()"> 
<select id="filter_active"> 
<option value="" ${status_selected[0]}> </option>
<option value="true" ${status_selected[1]}> active </option>
<option value="false" ${status_selected[2]}> inactive </option>
</select>
</%def> 

## main body table comes from the underlying template, then we add the 
## footer to support pagination 

${next.body()} 

% if len(p_list) > 0: 
  <br> 
  % if start == 0: 
  &nbsp;&lt;&lt;&nbsp;  &nbsp;&lt;&nbsp;  
  % else: 
  <a onclick="javascript:pFilter.change_page(0)"> &nbsp;&lt;&lt;&nbsp; </a> 
  <a onclick="javascript:pFilter.change_page(${start - count})"> &nbsp;&lt;&nbsp; </a>
  % endif

  &nbsp;  ${first_res_num}-${start + num_rows} of ${total} results &nbsp;

  % if start + count >= total: 
  &nbsp;&gt;&nbsp; &nbsp;&gt;&gt;&nbsp;  
  % else: 
  <a onclick="javascript:pFilter.change_page(${start + count})">&nbsp;&gt;&nbsp; </a>
  <a onclick="javascript:pFilter.change_page(${ ((total-1)/count) * count})"> 
  &nbsp;&gt;&gt;&nbsp; </a>
  % endif
%else:
  <br> 
  % if ptype == "switch":  
    <center><h2> No switches found. </h2></center> 
  %else: 
    <center><h2> No ${ptype}s found. </h2></center>
  % endif 
% endif
<input type="hidden" id="filter_start" value="${start}"> 
<input type="hidden" id="filter_count" value="${count}"> 
<input type="hidden" id="filter_sort_attr" value="${sort_attr}"> 
<input type="hidden" id="filter_sort_desc" value="${sort_desc_str}"> 

