## -*- coding: utf-8 -*-
##
## cp_base.mako - base template for captive portal pages
##
## ---------------------------------------------------------------------------
## Base page layout
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    ${self.meta_tags()}
    <link rel="stylesheet" href="${r['default_css']}" type="text/css">
    <link rel="stylesheet" href="${r['custom_css']}" type="text/css">
    <script src="${r['js_lib']}" type="text/javascript"></script>
    <title>${self.page_title()}</title>
    ${self.head_ext()}
  </head>
  <body ${self.body_args()}>
    <div id="fullPageDiv">
${self.header()}
${next.body()}
${self.footer()}
    </div>
  </body>
</html>
\
## ---------------------------------------------------------------------------
## Default section parameters
<%def name="meta_tags()" filter="trim"></%def>\
\
<%def name="page_title()" filter="trim"></%def>\
\
<%def name="head_ext()" filter="trim"></%def>\
\
<%def name="body_args()" filter="trim"></%def>\
\
<%def name="header()" filter="trim">
  <%include file="cp_header.mako"/>
</%def>\
\
<%def name="footer()" filter="trim">
  <%include file="cp_footer.mako"/>
</%def>\
