## -*- coding: utf-8 -*-
##
## cp_success.mako - captive portal page displayed in main window
##                   after successfull authentication
## 
<div id="heading">
  <div id="successMsg">
    <H1>Log in successful</H1>
  </div>
% if username:
  <div id="successStatusMsg">
    You are now logged in as '${username}'.
  </div>
%endif
</div>

<div id="redirMsg">
%if rurl != '':
  <div>
    In a moment, you should be redirected to your <A href="${rurl}">original destination</A> [${rurl_disp}].
  </div>
  <div>
    If you are not redirected, you can click <A href="${rurl}">here</A>, or reissue your request.
  </div>
%else:
    Please reissue your request to continue to your original destination.
%endif
</div>
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
% if p('org_name') is not None:
${p('org_name')} Network Authentication Successful
% else:
Network Authentication Successful
% endif
</%def>\
\
<%def name="meta_tags()" filter="trim">
%if rurl != '':
  <meta http-equiv="refresh" content="2;url=${rurl}">
%endif
</%def>\
