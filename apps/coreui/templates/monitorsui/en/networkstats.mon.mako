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

<%inherit file="monitors-layout.mako"/>
<%def name="page_title()">Network Statistics</%def>

<%def name="head_css()">
  ${parent.head_css()}
</%def>

<%def name="head_js()">
  ${parent.head_js()}
  dojo.addOnLoad(init_page);
</%def>

## ---------------------------------------------------------------------------

<div dojoType="dijit.layout.ContentPane" id="monitor_content" region="center">

  <table>
    <tr>
      <td class="label">Registered Switches:</td>
      <td id="registered_switches_field">0</td>
    </tr>
    <tr>
      <td class="label">Unregistered Switches:</td>
      <td id="unregistered_switches_field">0</td>
    </tr>
    <tr>
      <td class="label">Total Tx Packets:</td>
      <td id="total_tx_pkts_field">0</td>
    </tr>
    <tr>
      <td class="label">Total Tx Bytes:</td>
      <td id="total_tx_bytes_field">0</td>
    </tr>
    <tr>
      <td class="label">Total Rx Packets:</td>
      <td id="total_rx_pkts_field">0</td>
    </tr>
    <tr>
      <td class="label">Total Rx Bytes:</td>
      <td id="total_rx_bytes_field">0</td>
    </tr>
    <tr>
      <td class="label">Total Active Flows:</td>
      <td id="total_active_flows_field">0</td>
    </tr>
  </table>

</div>
