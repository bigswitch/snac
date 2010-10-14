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

<%inherit file="base.mako"/>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox.ext.apps.coreui/coreui/Progress.css";
</%def>

<%def name="dojo_requires()">
   ${parent.dojo_requires()}
   dojo.require("dijit.layout.ContentPane");
   dojo.require("dijit.layout.BorderContainer");
   dojo.require("dijit.Toolbar");
   dojo.require("dijit.form.Button");
   dojo.require("nox.ext.apps.coreui.coreui.Progress");
</%def>

##<%def name="pageheader()">
## NOX UI
##</%def>
<%def name="pageheader()">
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  ## Must define the wrapper function because highlight_current_section
  ## is not neccessarily defined until page is loaded.
  dojo.addOnLoad(function () {
      nox.ext.apps.coreui.coreui.base.highlight_current_section();
  });
</%def>

<%def name="pagemenu()">
  <div id="pagetoolbar" dojoType="dijit.Toolbar">
    %for s in siteConfig["sections"]:
      %if session.requestIsAllowed(request, s.required_capabilities):
        <a href="/${s.section_name}">
          <button dojoType="dijit.form.ToggleButton"
                  id="${s.section_name}Button" checked="false"
                  iconClass = "${s.section_icon}"
                  onClick='window.location.href="/${s.section_name}";'>
            ${s.section_name}
          </button>
    </a>
      %endif
    %endfor
  </div>
  <div class="appMeta">
    ## TBD: - Need to handle demangling the user name better.
    <span>user: ${session.user.username.split(";")[-1]}</span>
    <a href="/logout">
      <button dojoType="dijit.form.Button" id="logoutButton" iconClass ="logoutButtonIcon"
              onClick='window.location.href="/logout";'>Logout</button>
    </a>
  </div>
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.BorderContainer" design="headline" id="fullPageDiv">

  <div dojoType="dijit.layout.ContentPane" region="top" id="headerDiv">
    <div id="logoDiv"><span>Policy Manager (beta) ${self.pageheader()}</span></div>
    <div id="pagemenu">${self.pagemenu()}</div>
  </div>

  ${next.body()}

  
</div>
