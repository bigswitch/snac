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
<%def name="page_title()">Access denied!</%def>

<%namespace name="login" file="login.mako"/>

<%def name="dojo_requires()">
  ${login.dojo_requires()}
</%def>

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

## Disable the menu
<%def name="pagemenu()"></%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" region="center" id="loginPageDiv">

  <h1>Access Denied</h1>
  
% if hasattr(session, 'user') : 
  <p><span class="errormsg">You are logged in as user
    ${session.user.username}.  That user is not allowed to perform the
    action you have requested.</span></p>
% else : 
  <p><span class="errormsg">You must be logged in to view this page.</span></p>
% endif

  <p>If you would like to change users, please login again.  Otherwise
  you can use the browser back button to return to where you were
  before.</p>

  ${login.login_form()}

</div>
