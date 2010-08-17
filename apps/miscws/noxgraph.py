#!/usr/bin/python
#####################
# Topology Grabbing #
#####################

import sys,os
import httplib
import simplejson
import urllib
from topograph import *

# Permit running this from src or miscws directory
if os.getcwd().endswith('miscws'):
    path = '/'.join(os.getcwd().split('/')[:-4])
else:
    path = os.getcwd()

# Without this line, python can't find the NOX includes
sys.path.append(path)

from nox.webapps.webserviceclient import PersistentLogin, NOXWSClient

class Controller(Point):
    def __init__(self):
        Point.__init__(self)
        self.fill = "red"

class Switch(Point):
    def __init__(self):
        Point.__init__(self)
        self.fill = "yellow"

class Host(Point):
    def __init__(self):
        Point.__init__(self)
        self.fill = "white"

class TopologyGrabber:
    "Grab ui information"
    def __init__(self):
        loginmgr = PersistentLogin("admin","admin")
        self.wsc = NOXWSClient("127.0.0.1", 443, True, loginmgr)

    def response_is_valid(self,response):
        contentType = response.getContentType()
        """
        assert response.status == httplib.OK, \
               "Request error %d (%s) : %s" % \
               (response.status, response.reason, response.getBody())
        assert contentType == "application/json", \
               "Unexpected content type: %s : %s" % \
               (contentType, response.getBody())
        """
        if not response.status == httplib.OK:
            print "Request error %d (%s) : %s\n\t" % \
                   (response.status, response.reason, response.getBody()),
        elif not contentType == "application/json":
            print "Unexpected content type: %s : %s\n\t" % \
                   (contentType, response.getBody()),
        else:    return True
        return False

    def demangle(self, mangled):
        return mangled.split(';')[-1]

    def get_links(self, url="/ws.v1/link"):
        return self.get_info(url)

    def get_hosts(self, url="/ws.v1/host"):
        return self.get_info(url)

    def get_host_info(self, mangled, url="/ws.v1/host/%s"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_host_locations(self, mangled, url="/ws.v1/host/%s/active/location"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_location_switch(self, mangled, url="/ws.v1/location/%s/config"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_switches(self, url="/ws.v1/switch"):
        return self.get_info(url)

    def get_switch_info(self, mangled, url="/ws.v1/switch/%s"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_info(self, url):
        url = urllib.quote(url)
        # print url # Handy debugger
        response = self.wsc.get(url)
        body = response.getBody()
        if self.response_is_valid(response):
            return eval(body)
        return []


# Implements d[e] += 1
def d_up(dict,entry):
    dict[entry] = dict.get(entry,0) + 1

def macify(dpid):
    mac = "%012x" % dpid
    mac = [mac[2*x:2*x+2] for x in xrange(len(mac)/2)]
    return ":".join(mac)

if __name__ == '__main__':
    t = Topograph()
    g = TopologyGrabber()

    # TODO This could be streamlined, figure out how to do it while
    # preserving clarity of process

    # Get hosts/switches
    # Uni-directional dictionaries, mangled name->dpid
    unknown_dpid = 0
    hosts = {}
    for host in g.get_hosts():
        if g.demangle(host) == "internal":  continue

        if not host:
            print 'Blank host name in host-list'
            continue
        host_info = g.get_host_info(host)
        if not host_info:
            print 'No information available for host %s' % host
            continue

        infos = host_info["netinfos"]
        dpid = None
        for info in infos:   dpid = dpid or info.get("dladdr",None)

        unknown_dpid += 1
        if dpid == None:  dpid = unknown_dpid
        else:             dpid = int(dpid.replace(':',''),16)
        hosts[host] = dpid

    switches = {}
    for switch in g.get_switches():
        if not switch:
            print 'Blank switch name in switch-list'
            continue
        if not g.get_switch_info(switch):
            print 'No information available for switch [%s]' % \
                  g.demangle(switch)
            continue

        dpid = g.get_switch_info(switch)["dpid"]
        switches[switch] = int(dpid)

    # Get links for hosts/switches
    #TODO Someday deal with ports...
    links = []
    linked = {}
    for host,dpid in hosts.iteritems():
        for loc in g.get_host_locations(host):
            data = g.get_location_switch(loc)
            switch = data["switch_name"]
            if switch not in switches:
                print "Host [%s]'s location refers to unlisted switch [%s]" % \
                      (g.demangle(host), g.demangle(switch))
                continue
            links.append([dpid,switches[switch],g.demangle(loc)])
            d_up(linked,dpid)
            d_up(linked,switches[switch])

    for link in g.get_links():
        links.append([link["dpid1"],link["dpid2"],"interswitch"])
        d_up(linked,link["dpid1"])
        d_up(linked,link["dpid2"])

    # For today...
    # Ignore directional linking
    consolidated = {}
    for link in links:
        d_up(consolidated,tuple(sorted(link)))
    links = consolidated.keys()

    # Create nodes
    # Keep node dpid->index reference dictionary
    principals = {'host': (hosts,Host), 'switch': (switches,Switch)}
    index = {}
    for name,(members,constructor) in principals.iteritems():
        for member, dpid in members.iteritems():
            if dpid not in linked:
                print "Unlinked %s: %s (%s)" % \
                      (name.title(), g.demangle(member), macify(dpid))
                continue
            index[dpid] = len(t.points)
            t.points.append(constructor())
            t.points[index[dpid]].name = g.demangle(member)
            t.points[index[dpid]].dpid = dpid

    # Create links
    for a,b,i in links:
        try:  t.links.append(Link(t.points[index[a]], t.points[index[b]], i))
        except KeyError:
            unknown = lambda dpid: (dpid not in index) and "(unknown) " or ""
            print "Won't Link %s%s to %s%s via %s" % (unknown(a), macify(a), \
                                                      unknown(b), macify(b), i)
    # Prepare for output
    for x in xrange(1000):  t.adjust()
    t.to_html()
