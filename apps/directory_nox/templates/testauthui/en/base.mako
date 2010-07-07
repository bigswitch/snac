##
## base.mako - base template for cdbauth pages
##
## ---------------------------------------------------------------------------
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
            "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    ${self.meta_refresh()}
    <script type="text/javascript">${self.head_js()}</script>
    <title>${self.page_title()}</title>
    <link rel="stylesheet" href="/static/base.css" type="text/css" media="screen"/>
    <style type="text/css">
      body {
        padding-top: 18px;
        background-color: #dee;
        font-family: Verdana, Arial, sans-serif;
      }
    </style>
  </head>
  <body>
      ${self.header()}

      ${next.body()}

      ${self.footer()}
  </body>
</html>

## Defaults
<%def name="meta_refresh()" filter="trim"></%def>
<%def name="page_title()" filter="trim">Please set a page title!!!</%def>
<%def name="head_js()" filter="trim"></%def>
<%def name="header()" filter="trim"><%include file="header.mako"/></%def>
<%def name="footer()" filter="trim"><%include file="footer.mako"/></%def>

