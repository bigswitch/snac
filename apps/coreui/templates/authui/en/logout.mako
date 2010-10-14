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

<%inherit file="layout.mako"/>
<%def name="page_title()">Logout</%def>

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

<%namespace name="login" file="login.mako"/>

<%def name="dojo_requires()">
  ${login.dojo_requires()}
</%def>

## Disable the menu
<%def name="pagemenu()"></%def>

## ---------------------------------------------------------------------------
<div dojoType="dijit.layout.ContentPane" region="center" id="loginPageDiv">

  <h1>Logout Successful</h1>
  <p>You must login again to access the system.</p>

  ${login.login_form()}

</div>
