## -*- coding: utf-8 -*-
##
## auth_base.mako - base template for captive portal auth pages
##
## ---------------------------------------------------------------------------
## Base page layout
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    ${self.meta_tags()}
    <link rel="stylesheet" href="/static/nox/ext/apps/userauthportal/default.css" type="text/css" media="screen">
    <script src="/static/nox/ext/apps/userauthportal/cp.js" type="text/javascript"></script>
    <title>${self.page_title()}</title>
    ${self.head_style()}
  </head>
  <body ${self.body_args()}>
% if is_popup:
    <div id="fullPageDiv">
% else:
    <div id="popupPageDiv">
%endif
      ${self.preheader()} \
      ${self.header()}    \
      ${next.body()}      \
      ${self.footer()}    \
      ${self.postfooter()}
    </div>
  </body>
</html>
\
## ---------------------------------------------------------------------------
## Default section parameters
<%def name="meta_tags()" filter="trim"></%def> \
<%def name="page_title()" filter="trim"></%def>   \
<%def name="head_style()" filter="trim">
  <style type="text/css" media="screen">
    body {
% if is_popup:
       padding-top: 2px;
% else:
       padding-top: 18px;
% endif
    }
    ${c.css}
  </style> 
</%def> \
<%def name="body_args()" filter="trim"></%def>  \
<%def name="preheader()" filter="trim"></%def>  \
<%def name="header()" filter="trim"><%include file="auth_header.mako"/></%def> \
<%def name="footer()" filter="trim"><%include file="auth_footer.mako"/></%def> \
<%def name="postfooter()" filter="trim"></%def> \
\
## ---------------------------------------------------------------------------
## Common functions
<%def name="ses_post_form_inputs()" filter="trim">
  % for param in flowparams.keys():
    <input type="hidden" name="${param}" value="${flowparams[param]}">
  % endfor
</%def> \
\
<%def name="ses_get_query_attrs()" filter="trim">
  ${'&'.join(["%s=%s"%(k, v) for k,v in flowparams.items()])}
</%def> \
