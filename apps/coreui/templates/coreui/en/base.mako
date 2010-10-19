<!--
Copyright 2008 (C) Nicira, Inc.

This file is part of NOX.

NOX is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

NOX is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with NOX.  If not, see <http://www.gnu.org/licenses/>.

-->
## -*- coding: utf-8 -*-

<%def name="page_title()">Please set a page title!!!</%def>

## These must be false for production!!!
<%def name="debugOn()">false</%def>
<%def name="debugAtAllCosts()">false</%def>

<%def name="dojo_root()">/static</%def>
<%def name="dojo_imports()">
  @import "${self.dojo_root()}/dojo/resources/dojo.css";
  @import "${self.dojo_root()}/dijit/themes/nihilo/nihilo.css";

  @import "/static/nox/ext/apps/coreui/coreui/base.css";
</%def>
<%def name="dojo_requires()">
  dojo.require("dojo.parser");
  dojo.require("dijit.dijit");
  dojo.require("nox.ext.apps.coreui.coreui.noxcore");
</%def>

<%def name="head()"></%def>
<%def name="head_css()"></%def>
<%def name="head_js()"></%def>

## ---------------------------------------------------------------------------
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
            "http://www.w3.org/TR/html4/strict.dtd">
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">

    <style type="text/css">
        ${self.dojo_imports()}
    </style>

    <script type="text/javascript" src="${self.dojo_root()}/dojo/dojo.js"
      djConfig="parseOnLoad: true, isDebug: ${self.debugOn()}, debugAtAllCosts: ${self.debugAtAllCosts()}, usePlainJson: true"></script>

<!--
  <script type="text/javascript" src="/static/nox/ext/apps/coreui/coreui/_UpdatingStore.js"></script>
--> 
    <script type="text/javascript">
        ${self.dojo_requires()}
        ${self.head_js()}
    </script>

    ${self.head()}

    <style type="text/css">
      ${self.head_css()}
    </style>

    <title>${siteConfig["network_name"]} Network ${self.page_title()}</title>

  </head>

  <body class="nihilo nox">
    <input type="hidden" id="network_name" value="${siteConfig["network_name"]}" > 
    ${next.body()}
  </body>
</html>
