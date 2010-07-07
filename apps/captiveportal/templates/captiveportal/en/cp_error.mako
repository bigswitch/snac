## -*- coding: utf-8 -*-
##
## cp_error.mako - captive portal page displayed when an
##                 unexpected error occurs
##  
<div id="error">
  <div class="errorMsg">
      An unexpected error has occurred.
  </div>
  <div class="errorMsg">
      If you are experiencing network problems, please contact your network
      administrator.
  </div>
  % if msg:
    <div class="serverMsg">
        Error Details: ${msg}
    </div>
  % endif
</div>
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
% if p('org_name') is not None:
${p('org_name')} Network Authentication Error
% else:
Network Authentication Error
% endif
</%def>\
