# Copyright 2008 (C) Nicira, Inc.
# 
# This file is part of NOX.
# 
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.
import nox.netapps.directory.discovered_directory as discovered
from nox.ext.apps.sepl.declare import *

# POLICY

set_priority(0)

#allow() <= hsrc(discovered.INTERNAL) # don't need this bc sepl automatically allows...but for dest?
c_action("authenticate_host") <= hsrc(discovered.UNAUTHENTICATED) # need to check that not internal?

cascade()

allow() <= apsrc('sepl_directory;wireless') ^ tpdst(8888) ^ hdst("sepl_directory;emerson")
#allow() <= hsrc('sepl_directory;mc-laptop-wifi') ^ tpdst(8888) ^ hdst("sepl_directory;emerson")
#c_action("http_redirect") <= apsrc('sepl_directory;wireless') ^ tpdst(80) # ^ usrc(sepl_directory.UNAUTHENTICATED)
c_action("http_redirect") <= apsrc('sepl_directory;wireless') ^ tpdst(80)  ^ usrc("sepl_directory;unauthenticated")
#c_action("http_redirect") <= hsrc('sepl_directory;mc-laptop-wifi') ^ tpdst(80) ^ usrc(sepl_directory.UNAUTHENTICATED)
#deny() <= hsrc('sepl_directory;mc-laptop-wifi') ^ tpdst(80)

cascade()

# allow ARP
allow() <= protocol('arp')
allow() <= protocol('dhcp6s') ^ (hdst("sepl_directory;gateway") | dldst("ff:ff:ff:ff:ff:ff"))
allow() <= protocol('dhcp6c') ^ hsrc("sepl_directory;gateway")
allow() <= protocol('dhcps') ^ (hdst("sepl_directory;gateway") | dldst("ff:ff:ff:ff:ff:ff"))
allow() <= protocol('dhcpc') ^ hsrc("sepl_directory;gateway")

# allow computers to ssh into anyone
allow() <= protocol('ssh') ^ in_group('sepl_directory;computers', HSRC)

# allow internal monitoring flows
allow() <= (tpsrc(1616) ^ hsrc("sepl_directory;badwater")) |  (tpdst(1616) ^ hdst("sepl_directory;badwater"))
allow() <= (tpsrc(1717) ^ hsrc("sepl_directory;badwater")) |  (tpdst(1717) ^ hdst("sepl_directory;badwater"))
allow() <= (tpsrc(1818) ^ hsrc("sepl_directory;badwater")) |  (tpdst(1818) ^ hdst("sepl_directory;badwater"))

# allow dns to leadville
allow() <= hdst("sepl_directory;leadville") ^ protocol('dns')
allow() <= hsrc("sepl_directory;leadville") ^ protocol('dns')

cascade()

# dissallow testing machines from communicating externally 
#deny() <= in_group('sepl_directory;testing', HSRC) | in_group('sepl_directory;testing', HDST)

# servers should be inbound-only
# deny() <= isConnRequest() ^ in_group('sepl_directory;servers', HSRC) 

# printers should be inbound-only
deny() <= isConnRequest() ^ in_group('sepl_directory;printers', HSRC) 

# laptops and mobile devices should be outbound-only
#deny() <= isConnRequest() ^ (in_group('sepl_directory;mobile', HDST) | in_group('sepl_directory;laptops', HDST))

cascade()

#deny unknown hosts
# deny() <= hsrc(sepl_directory.UNAUTHENTICATED) ^ usrc(sepl_directory.UNAUTHENTICATED)

cascade()

# allow known devices to communicate as long as they abide by the
# previous rules.
allow() <= in_group('sepl_directory;all', HSRC) 
allow() <= in_group('sepl_directory;all', HDST) 

cascade()

# default deny
deny() <= True

update_SEPL()
