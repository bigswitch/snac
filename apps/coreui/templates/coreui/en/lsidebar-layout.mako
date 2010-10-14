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

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "${self.dojo_root()}/dojox/grid/resources/nihiloGrid.css";
</%def>

<%def name="dojo_requires()">
   ${parent.dojo_requires()} dojo.require("dijit.Menu");
   dojo.require("nox.ext.apps.coreui.coreui.Search");
   //dojo.require("nox.ext.apps.coreui.coreui.NetworkStatusIndicator");
   dojo.require("nox.ext.apps.snackui.snackmonitors.NetworkOverviewData");
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  ## Must define the wrapper function because highlight_current_sidebar_link
  ## is not neccessarily defined until page is loaded.
  var footerData = null;

  footerUpdate = function () {
      var t = document.createTextNode(footerData.getValue("version"));
      var n = dojo.byId("footer-version");
      n.replaceChild(t, n.firstChild);
      t = document.createTextNode(footerData.getValue("active_admins"));
      n = dojo.byId("footer-admin-cnt");
      n.replaceChild(t, n.firstChild);
  }

  dojo.addOnLoad(function () {
      nox.ext.apps.coreui.coreui.base.highlight_current_sidebar_link();
      footerData = new nox.ext.apps.snackui.snackmonitors.NetworkOverviewData({
          updateList: [ "serverstat" ]
      });
      nox.ext.apps.coreui.coreui.getUpdateMgr().userFnCall({
          purpose: "Update footer bar data.",
          fn: function () {
              footerData.update({
                  onComplete: footerUpdate,
                  errorHandlers: {}    // TBD: - better error handler?
            });
          },
          recur: true
      });
  });
</%def>

<%def name="lsidebar()">
Sidebar contents need to be defined by inherited template.
</%def>

<%def name="module_header()"></%def>

<%

# sorted list of the different search types and an indication
# of whether that search type is the default
search_options_list = [ "Host Names", "Host IPs", "Host MACs", 
                        "Host Locations", "User Names", "Location Names",                               "Switch Names" ]                          

try: 
  selected_search_type = session.selected_search_type
except AttributeError:
  selected_search_type = "Host Names" # default 

%> 

## ---------------------------------------------------------------------------
<div dojoType="dijit.layout.ContentPane" region="left" id="lsidebar">
    <div dojoType="dijit.layout.BorderContainer">
        <div dojoType="dijit.layout.ContentPane" region="center">
           <form dojoType="nox.ext.apps.coreui.coreui.Search" id="searchBox">
                <div dojoType="dijit.Menu" style="display: none;">
                  % for option in search_options_list: 
                    % if option == selected_search_type: 
                    <div dojoType="dijit.CheckedMenuItem" checked="true">${option}</div>
                    % else: 
                    <div dojoType="dijit.CheckedMenuItem">${option}</div>
                    %endif 
                  % endfor 
                </div>
            </form>
            ${self.lsidebar()}
        </div>
        ## dummy markup for blank network status area
        <div dojoType="dijit.layout.ContentPane" region="bottom">
          <div id="networkStatusContainer">
            <div id="networkStatusType" dojoType="dijit.layout.ContentPane" class="networkStatusNormal">
              <table cellspacing="0" class="networkStatusTitleBar">
                <tr>
                  <td class="statusContainer">
                    <span class="networkStatusTitle"></span>
                  </td>
                </tr>
              </table>
            </div>
          </div>
        </div>
        ## when network status indicator is enabled, dummy markup above
        ## should be removed.
		<!-- <div id="networkStatusContainer" dojoType="nox.ext.apps.coreui.coreui.NetworkStatusIndicator" region="bottom"></div> -->
    </div>
</div>

<div dojoType="dijit.layout.ContentPane" id="page_content" region="center">
    <div dojoType="dijit.layout.BorderContainer" design="headline">
        <div dojoType="dijit.layout.ContentPane" id="module_header" region="top">
            <div id ="module-titlebar">
                <h1 id="page-title" class="HeaderBar">${self.page_title()}</h1>
                <div jsid="progress" id="progress" dojoType="nox.ext.apps.coreui.coreui.Progress"></div>
            </div>
            ${self.module_header()}
        </div>
        <div dojoType="dijit.layout.ContentPane" id="module_content" region="center">
            ${next.body()}
        </div>

        <div dojoType="dijit.layout.ContentPane" region="bottom" id="footerBar">
          <div id="footerContent">
            <table class="footerLayoutContainer">
              <tr>
                <td><span class="networkName"><span id="header-netname">${siteConfig["network_name"]}</span> Network</span><span class="activeAdmins" href=""><span id="footer-admin-cnt">1</span> Active Admins</span></td>
                <td align="right">Version: <span id="footer-version">-</span></td>
              </tr>
            </table>
          </div>
        </div>

    </div>
</div>
