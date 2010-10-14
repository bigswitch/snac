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

<%inherit file="lsidebar-layout.mako"/>

<%def name="lsidebar()">
  <ul class="lsidebar">
    %for m in MonitorsRegistry.list():
      %if MonitorsRegistry[m].name != None:
      <li><a href="/Monitors/${MonitorsRegistry[m].id}">${MonitorsRegistry[m].name}</a></li>
      %endif
    %endfor
  </ul>
</%def>


<%def name="monitor_header()"></%def>
<%def name="module_header()">${self.monitor_header()}</%def>

## ---------------------------------------------------------------------------

${next.body()}
