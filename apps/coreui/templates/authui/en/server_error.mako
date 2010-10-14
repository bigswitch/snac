## -*- coding: utf-8 -*-

## Copyright 2008 (C) Nicira, Inc.
##
## This file is part of NOX.
##
## NOX is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## NOX is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with NOX.  If not, see <http://www.gnu.org/licenses/>.

<%
  request.setResponseCode(500)
%>
<%inherit file="layout.mako"/>
<%def name="page_title()">Internal Server Error</%def>

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

<%def name="dojo_requires()">
  // Deliberately overriding base.mako requires to avoid endless redirects
  dojo.require("dojo.parser");
  dojo.require("nox.ext.apps.coreui.coreui.base");
  dojo.require("dijit.layout.ContentPane");
  dojo.require("dijit.layout.BorderContainer");
</%def>

## Disable the menu
<%def name="pagemenu()"></%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" region="center" id="loginPageDiv">

  <h1>${page_title()}</h1>

  <p>An internal server error has occurred.  Please contact your system
  adminstrator for assistance.</p>

## TBD: include information about the error somewhere that won't be
## TBD: displayed to the user but is accessible to a developer.

</div>
