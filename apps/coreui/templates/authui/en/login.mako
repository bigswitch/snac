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
<%def name="page_title()">Login</%def>

<%def name="dojo_requires()">
  // Deliberately overriding base.mako requires to avoid endless redirects
  dojo.require("dojo.parser");
  dojo.require("nox.ext.apps.coreui.coreui.base");
  dojo.require("dijit.layout.ContentPane");
  dojo.require("dijit.layout.BorderContainer");
  dojo.require("dijit.form.Button");
  dojo.require("dijit.form.TextBox");
</%def>

## don't include noxcore.js
<%def name="include_noxcore()"></%def> 

<%def name="head_js()"> 
${parent.head_js()} 
   dojo.addOnLoad(function () {
      // if this template is loaded within an iframe, we should
      // actually redirect the entire window to the login page, 
      // preserving the correct last page.   
      if(top.location != document.location) { 
        top.location = document.location.pathname + "?last_page=" + 
          encodeURIComponent(top.location.pathname + 
                      top.location.search);
        
      } 
   }); 
</%def>


## Disable the menu
<%def name="pagemenu()"></%def>

## Login form used here and on the access denied and logout pages.
<%def name="login_form()">
  <script type="text/javascript" >
      dojo.addOnLoad(function () {
          dijit.byId("username").focus();
          var w = dijit.byId("last_page");
          if (w.value == "") {
              var page = nox.ext.apps.coreui.coreui.base.get_url_param("last_page"); 
              dijit.byId("last_page").setValue(page);
          }
      });
  </script>

  <form name="login" action="/login" method="post">
    <table align="center">
      <tr>
        <td align="right">Username:</td>
        <td><input id="username" type="text" name="username" tabindex="1" dojoType="dijit.form.TextBox"/></td>
      </tr>
      <tr>
        <td align="right">Password:</td>
        <td><input id="password" type="password" name="password" tabindex="2" dojoType="dijit.form.TextBox"/></td>
      </tr>
      <tr>
        <td align="right" colspan="2"><button type="submit" tabindex="3" dojoType="dijit.form.Button">Login</button></td>
      </tr>
    </table>
    <input dojoType="dijit.form.TextBox" type="hidden" id="last_page" name="last_page" value="${last_page}"/>
   </form>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" region="center" id="loginPageDiv">

  <h1>Login Required</h1>
  <p>Please login to gain access to the system.</p>

  % if login_failed == True:
  <p><span class="errormsg">Incorrect login, please try again.</span></p>
  % endif

  ${login_form()}

</div>
