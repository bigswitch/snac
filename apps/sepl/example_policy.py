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
# Trivial example using reactor timer method to countdown from three

import nox.apps.directory.discovered_directory as discovered
from nox.ext.apps.sepl.declare import *

# all rules in the default policy should be protected
# except those that need to allow administrators to add
# new IP subnets because we do not yet have subnet groups
set_protected(True) 

set_priority(0)

set_rule_type('auth') # simple rule-types until full policy UI is done
#set_rule_type('comm')

set_description("\"Discovered\" auto-authentication")
set_comment("For hosts not previously authenticated, create a \"discovered\" identity and autoauthenticate it.  If this rule is removed, traffic to all hosts not authenticated by one of the previous rules will be denied.")
authenticate_host() <= hsrc("discovered;unauthenticated")
cascade()

set_description("Allow all broadcasts")
set_comment("Required for many types of service discovery.")
allow() <= dldst("ff:ff:ff:ff:ff:ff") | nwdst("255.255.255.255")
cascade()

set_description("Allow all ARP packets")
set_comment("Required to allow hosts to find each other's MAC addresses.")
allow() <= protocol('arp')
cascade()

# Disable this for networks this for now in favor of a less stringent policy
#set_description("Allow DHCP to DHCP servers")
#set_comment("Require that DHCP replies come from hosts in the DHCP Servers group.")
#allow() <= ((protocol('dhcpc')
#             ^ (dldst("ff:ff:ff:ff:ff:ff")
#                | in_group("Built-in;DHCP Servers", "HDST")))
#            | (protocol('dhcps')
#               ^ in_group("Built-in;DHCP Servers", "HSRC")))
set_description("Allow all DHCP") 
allow() <= (protocol('dhcpc') | protocol('dhcps')) ^ nwproto(17) # udp only
cascade()

set_description("Allow DNS to DNS servers")
set_comment("Unauthenticated hosts must be able to resolve DNS names so web requests can be redirectored to the captive portal.")
allow() <= protocol('dns') ^ (in_group("Built-in;DNS Servers", "HSRC")
                | in_group("Built-in;DNS Servers", "HDST"))
cascade()

set_description("Allow LDAP server queries from controller")
set_comment("Depending on configuration, the controller may require connectivity to external LDAP servers to verify users, hosts, or other entities.  This rule ensures such connectivity is available.")
allow() <= ((in_group("Built-in;Controllers", "HSRC")
             ^ in_group("Built-in;LDAP Servers", "HDST"))
            | (in_group("Built-in;LDAP Servers", "HSRC")
               ^ in_group("Built-in;Controllers", "HDST")))
# TBD: - Can we add protocol("ldap") to this rule?  That is:
#allow() <= (protocol("ldap")
#            ^ ((in_group("Built-in;Controllers", "HSRC")
#                ^ in_group("Built-in;LDAP Servers", "HDST"))
#               | (in_group("Built-in;LDAP Servers", "HSRC")
#                ^ in_group("Built-in;Controllers", "HDST"))))

cascade()

set_description("Allow unrestricted access to selected servers")
set_comment("Hosts in this group will be allowed unrestricted access to the network.")
allow() <= (in_group("Built-in;Unrestricted Servers", "HSRC")
            | in_group("Built-in;Unrestricted Servers", "HDST"))
cascade()

#set_rule_type('hauth')

# set_description("802.1x authentication by location")
# set_comment("Switch ports for which 802.1x authentication is required.")
# authenticate_802.1x() <= (hsrc("discovered;unauthenticated")
#                           ^ in_group("Built-in;802.1x Locations", "LOCSRC"))
# TBD: - enable this rule in the future.
# cascade()

# set_description("Authentication of registered address by location")
# set_comment("Switch ports for which registered address authentication is required.")
# authenticate_registered() <= (hsrc("discovered;unauthenticated")
#                               ^ in_group("Built-in;Registered Address Locations", "LOCSRC"))
#cascade()

# set_description("802.1x authentication by switch")
# set_comment("Switches for which 802.1x authentication is required on any port.")
# authenticate_802.1x() <= (hsrc("discovered;unauthenticated")
#                           ^ in_group("Built-in;802.1x Switches", "SWSRC")
# TBD: - enable this rule in the future.
# cascade()

# set_description("Authentication of registered addresses by switch")
# set_comment("Switches for which registered address authentication is required on on any port.")
# authenticate_regisered() <= (hsrc("discovered;unauthenticated")
#                              ^ in_group("Built-in;Registered Address Switches", "SWSRC")
# TBD: - enable this rule in the future.
# cascade()


# The "comm.hath" rule-type should only be set on the next rule.  It is
# used by the UI code to find the rule before which host authentication
# rules need to be inserted.
#set_rule_type("comm.hauth")

set_description("Deny unauthenticated hosts")
set_comment("If a host was not successfully authenticated, deny traffic from it.  See the host authentication rules policy to determine how a host is authenticated.  Rather than modifying this rule, it is preferred to adjust the host authentication rules to prevent traffic from being dropped.")
deny() <= hsrc("discovered;unauthenticated")
cascade()

#set_rule_type("comm")

set_description("Allow specified locations to connect to captive portal for user authentication")
set_comment("User authentication via the captive portal requires HTTP to be allowed between the user and the captive portal.")
allow() <= (((in_group("Built-in;User Auth Portal Locations", "LOCSRC")
              | in_group("Built-in;User Auth Portal Switches", "SWSRC"))
             ^ (tpdst(80) | tpdst(443)) ^ in_group("Built-in;User Auth Portals", "HDST"))
            | (in_group("Built-in;User Auth Portals", "HSRC") ^
            (tpsrc(80) | tpsrc(443))))
cascade()

set_protected(False) 
set_description("Allow specified IP subnets to connect to captive portal for user authentication")
allow() <= ((subnetsrc('0.0.0.0/32') ^ (tpdst(80) | tpdst(443)) 
              ^ in_group("Built-in;User Auth Portals", "HDST"))
            | (in_group("Built-in;User Auth Portals", "HSRC") ^
            (tpsrc(80) | tpsrc(443))))


cascade()
set_protected(True) 

#set_rule_type('uauth')

set_description("Redirect unauthenticated users at the specified locations to the captive portal")
http_redirect() <= (usrc("discovered;unauthenticated") ^ tpdst(80) 
                ^ (in_group("Built-in;User Auth Portal Locations", "LOCSRC") | 
                   in_group("Built-in;User Auth Portal Switches", "SWSRC")))
cascade()

set_protected(False) 
set_description("Redirect unauthenticated users in the specified IP subnets to the captive portal")
http_redirect() <=  tpdst(80) ^ usrc("discovered;unauthenticated") ^ subnetsrc("0.0.0.0/32") 
cascade()

set_protected(True) 
# The "comm.uath" rule-type should only be set on the next rule.  It is
# used by the UI code to find the rule before which user authentication
# rules need to be inserted.
#set_rule_type("comm.uauth")

set_comment("If a user was not successfully authenticated, deny traffic from him/her.")
set_description("Deny unauthenticated users in the specified IP subnet")
deny() <= usrc("discovered;unauthenticated") ^ subnetsrc('0.0.0.0/32')

cascade()

set_description("Deny unauthenticated users at the specified locations")
deny() <= (usrc("discovered;unauthenticated") 
                ^ (in_group("Built-in;User Auth Portal Locations", "LOCSRC") | 
                   in_group("Built-in;User Auth Portal Switches", "SWSRC")))

cascade()
set_rule_type("comm")

set_description("Allow all traffic")
set_comment("To minimize disruptions, this rule allows all traffic not specifically dropped by a previous rule.  For a more secure network this rule can be deleted.")
allow() <= True
cascade()

#set_description("Deny all traffic")
#set_comment("Deny all traffic not specifically allowed by a previous rule. In the default policy, there is an allow all rule immediately previous to this one that will result in no traffic ever hitting this rule.  If that rule is removed, this will deny any traffic not specifically allowed.")
#deny() <= True
