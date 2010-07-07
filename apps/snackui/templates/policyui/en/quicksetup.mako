## -*- coding: utf-8 -*-

<%inherit file="policy-layout.mako"/>
<%def name="page_title()">Policy Quick Setup</%def>

<%def name="dojo_imports()">
  ${parent.dojo_imports()}
  @import "/static/nox/ext/apps/snackui/policyui/quicksetup.css";
</%def>

## ---------------------------------------------------------------------------


<p>The policy manager comes with a default communications policy
containing a set of rules required for most networks.  The behavior of
most of the default rules is determined by group membership.  This
page provides a link to each such group and describes how membership
in the group affects network behavior.  Additionally, if the default
policy has been modified, it shows rules or groups which are no longer
present and provides the ability to recreate them.</p>

<table id="quicksetup-groups">
  <tr>
    <th>Group Name</th>
    <th>Effect on Default Policy</th>
    <th>Status</th>
  </tr><tr>
    <td></td>
    <td></td>
    <td></td>
  </tr><tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
</table>
