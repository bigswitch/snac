## -*- coding: utf-8 -*-

<%def name="page_title()">Policy Quick Debug</%def>

<p> Welcome to Restracker Debug. </p> 

<%
from nox.ext.apps.restracker.pyrestracker import pyrestracker 

counts = rt.get_host_counts()
context.write("<p>num hosts: %s</p>" % len(counts))


%>

<table> 
<tr><td>DPID</td><td>Inport</td><td>Mac</td><td>Count</td>
<%

def comp(a,b):
    return b[3] - a[3]

counts.sort(comp)    

for host in counts:
  context.write("<tr>")
  context.write("<td>%s</td>" % host[0])
  context.write("<td>%s</td>" % host[1])
  context.write("<td>%s</td>" % host[2])
  context.write("<td>%s</td>" % host[3])
  context.write("</tr>")
%> 
</table> 
