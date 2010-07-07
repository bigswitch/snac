## -*- coding: utf-8 -*-
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  </head>
<body>
<%def name="page_title()">Policy Quick Debug</%def>

<p> Welcome to policy debug. </p> 
<%

from nox.ext.apps import sepl
from nox.ext.apps.sepl import compile

policy = args['policy']
do_record = None
if 'record' in request.args: 
  if request.args['record'][-1] == 'start': 
    do_record = True
  if request.args['record'][-1] == 'stop': 
    do_record = False

if do_record is not None: 
  for r in policy.rules.values(): 
    policy.set_record_rule_senders(r.global_id, do_record) 

num_rules =  len(policy.rules)
context.write("<p>num rules: %s</p>" % num_rules)
if num_rules > 0: 
  stats0 = policy.get_rule_stats(policy.rules.values()[0].global_id)
  context.write("<p>Recording violating MACs? : %s</p>" % stats0["record_senders"])

%>
<form>
<input type="hidden" name="record" value="start"> 
<input type="submit" value="Start Recording">
</form>
<form>
<input type="hidden" name="record" value="stop"> 
<input type="submit" value="Stop Recording">
</form>
<form>
<input type="hidden" name="record" value=""> 
<input type="submit" value="Refresh Page">
</form>


<table> 
<tr><td>Rule</td><td>Hits</td><td>Recorded Macs</td>
<%

ordered = policy.rules.values()
ordered.sort(None, compile.PyRule.get_order)
for rule in ordered:
  context.write("<tr>")
  context.write("<td>%s</td>" % rule.ustr())
  stats = policy.get_rule_stats(rule.global_id)
  stats['sender_macs'] = [ str(eth) for eth in stats['sender_macs'] ]
  context.write("<td>%s</td>" % stats["count"])
  context.write("<td>%s</td>" % stats["sender_macs"])
  context.write("</tr>")
%> 
</table> 

<br/>
<form>
<%
def write_form_line(name):
    context.write("%s: <input type=\"text\" name=\"%s\" value=\"%s\">\n" % (name, name, args.get(name, '')))
write_form_line("dpsrc")
write_form_line("inport")
write_form_line("dlsrc")
write_form_line("nwsrc")
write_form_line("dldst")
write_form_line("nwdst")
%>
<input type="submit" value="Get Names">
</form>

<%

def write_row(name, value):
    if isinstance(value, list):
       value = ", ".join(value)
    context.write("  <tr><td>%s</td><td>%s</td></tr>\n" % (name, value))
           
def write_conn(conn, addr_groups):
    context.write("<table>\n")
    write_row("Location:", conn['location'])
    write_row("Hostname:", conn['host'])
    write_row("Host groups:", conn['hostgroups'])
    users = conn['users']
    for user in users:
        write_row("Username:", user[0])
        write_row("User groups:", user[1])
    write_row("Addr groups:", addr_groups)
    context.write("</table>\n")
    context.write("<hr/>\n")

if args.has_key('name_err'):
    context.write("%s\n" % args['name_err'])
elif args['names'] != None:
    names = args['names']
    if names['src'] != None:
        context.write("<hr/>\n")
        context.write("Source connector:\n")
        context.write("<hr/>\n")
        write_conn(names['src'], names['src_addr_groups'])
    if names['dsts'] != None:
        context.write("Destination connectors:\n")
        context.write("<hr/>\n")
        for dst in names['dsts']:
            write_conn(dst, names['dst_addr_groups'])
%>
</body></html>
## ---------------------------------------------------------------------------

