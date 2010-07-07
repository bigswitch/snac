## -*- coding: utf-8 -*-

<%inherit file="lsidebar-layout.mako"/>

<%def name="lsidebar()">
  <ul class="lsidebar">
<!--    <li><a href="/Policy/QuickSetup">Quick Setup</a></li> -->
    <li><a href="/Policy/Rules?view=auth">System Policy</a></li>
    <li><a href="/Policy/Rules?view=comm">Site Policy</a></li>
<!--    <li><a href="/Policy/HostAuthRules">Host Authentication Rules</a></li>
    <li><a href="/Policy/UserAuthRules">User Authentication Rules</a></li> --> 
  </ul>
</%def>

## ---------------------------------------------------------------------------

${next.body()}

