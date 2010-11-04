## -*- coding: utf-8 -*-

<%inherit file="lsidebar-layout.mako"/>

<%def name="lsidebar()">
  <ul class="lsidebar">
    <%
         from nox.ext.apps.dhcp.manager import DHCPManager
         dhcp_enabled = siteConfig["webserver"].resolve(str(DHCPManager))
    %>

    <li><a href="/Settings/Controller">Policy Controller</a></li>
    <li><a href="/Settings/Directories">Directories</a></li>
    <li><a href="/Settings/CaptivePortal">Captive Portal</a></li>
    % if dhcp_enabled:
         <li><a href="/Settings/DHCP">DHCP</a></li>
    % endif
    <li><a href="/Settings/Logs">Debug Log &amp; System Restore</a></li>
  </ul>
</%def>

## ---------------------------------------------------------------------------

${next.body()}

