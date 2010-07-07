#!/usr/bin/python
#####################
# Topology Grabbing #
#####################

import sys,os
import httplib
import simplejson
import urllib

# Permit running this from src or miscws directory
if os.getcwd().endswith('miscws'):
    path = '/'.join(os.getcwd().split('/')[:-4])
else:
    path = os.getcwd()
# HACK
path = "/opt/nox/bin"
# /HACK

# Without this line, python can't find the NOX includes
sys.path.append(path)

from nox.apps.coreui.webserviceclient import PersistentLogin, NOXWSClient

class HostFiller:
    "Grab/set ui information"
    def __init__(self):
        loginmgr = PersistentLogin("admin","admin")
        self.wsc = NOXWSClient("127.0.0.1", 443, True, loginmgr)
        self.debug = True

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
        self.debug = True
        return False

    def demangle(self, mangled):
        return mangled.split(';')[-1]

    def get_discovered_hosts(self, url="/ws.v1/host/discovered"):
        return self.get_info(url)

    def get_host_info(self, mangled, url="/ws.v1/host/%s"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_host_active(self, mangled, url="/ws.v1/host/%s/active"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_host_interfaces(self, mangled,
                           url="/ws.v1/host/%s/active/interface"):
        return self.get_info(url % (mangled.replace(';','/')))

    def get_host_interface(self, mangled, interface,
                           url="/ws.v1/host/%s/interface/%s"):
        return self.get_info(url % (mangled.replace(';','/'), interface))

    def get_info(self, url):
        url = urllib.quote(url)
        if self.debug:  print url
        response = self.wsc.get(url)
        body = response.getBody()
        # hack so that the returned value 'true' is evaluated properly
        true,false = True,False
        if self.response_is_valid(response):
            return eval(body)
        return []

    def put_host_info(self, mangled, info, url="/ws.v1/host/%s"):
        return self.put_info(url % (mangled.replace(';','/')), info)

    def put_dchp_config(self, info, url="/ws.v1/config/dhcp_config"):
        return self.put_info(url, info)

    def put_info(self, url, info):
        url = urllib.quote(url)
        if self.debug:  print url, info
        response = self.wsc.putAsJson(info,url)
        body = response.getBody()
        if self.response_is_valid(response):
            return eval(body)
        return []

def macify(dpid):
    mac = "%012x" % dpid
    mac = [mac[2*x:2*x+2] for x in xrange(len(mac)/2)]
    return ":".join(mac)

def proceed_check(interactive=True):
    if not interactive: return
    selection = raw_input("Do these values look ok? ")
    if selection.lower() not in ['y','yes','yep','sure','ok']:
        print "Exiting, unacceptable values ..."
        exit(1)
    print "\n"

if __name__ == '__main__':
    print "\n"
    interactive = True
    h = HostFiller()
    h.debug = False
    info_file = 'hosts.info'
    import sets
    import re
    import random

    host_data = {}
    # Get info from discovered hosts
    for host in h.get_discovered_hosts():
        desired = {'dladdr':[],'nwaddr':[]}

        # static
        info = h.get_host_info(host)
        for netinfo in info['netinfos']:
            for d in desired:
                if d in netinfo:  desired[d].append(netinfo[d])

        # active
        if h.get_host_active(host):
            for interface in h.get_host_interfaces(host):
                info = h.get_host_interface(host,interface)
                for d in desired:
                    if d in info:  desired[d].append(info[d])

        data = {}
        for d,vals in desired.iteritems():
            # Remove duplicate entries
            vals = list(sets.Set(vals))
            if not vals:
               print " ** Warning: No %s for %s" % (d,host)
            elif len(vals) > 1:
                print " ** Warning: Multiple %s for %s" % (d,host)
                if interactive:
                    for i, val in enumerate(vals):
                        print " [%d] %s" % (i,val)
                    while True:
                        selection = raw_input(" Enter selection: ")
                        try:
                            index = int(selection)
                            data[d] = vals[index]
                            print " Using", vals[index]
                            print " --------"
                            break
                        except:
                            print " Invalid:", selection
                else:
                    preferred = 0
                    if d == 'nwaddr':
                        for i,val in enumerate(vals):
                            if val.startswith('192.168.1.'):
                                preferred = i
                    print " Using %s over any of %s" % (vals[preferred],
                                                        vals[0:preferred]+ \
                                                        vals[preferred+1:])
                    data[d] = vals[preferred]
            else:
                data[d] = vals[0]
        host_data[host] = data
        
    print "\n"
    print "===Host ip-mac from webservices==="
    for name,data in host_data.iteritems():
        print "%s :" % name,
        for d in data.itervalues():
            print d, "\t",
        print ""
    print "\n"
    
    proceed_check(interactive)

    host_names = {}
    input = open(info_file)
    for line in input.readlines():
        spline = line.split()
        if not spline:
            print " ** Warning: Skipping empty line"
            continue
        name,data = spline[0],spline[1:]
        if not data:
            print ' ** Warning: Skipping data-less host "%s"' % name
            continue
        tmp = {}
        # TODO replace with regex
        desired = {'nwaddr':'.', 'dladdr':':'}
        bad = False
        for item in data:
            found = False
            for d,exp in desired.iteritems():
                if exp in item:
                    tmp[d] = item
                    found = True
            if not found:
                print " ** Warning: Bad input from host data file"
                print '    In line "%s" - "%s" is not a %s' % \
                      (line.replace("\n",""), item, "/".join(desired.keys()))
                print '    Skipping host "%s"' % name
                bad = True
        if not bad:
            host_names[name] = tmp

    print "\n"
    print "===Host name-mapping from file==="
    for name,data in host_names.iteritems():
        print "%s :" % name,
        for d in data.itervalues():
            print d, "\t",
        print ""
    print "\n"
    
    proceed_check(interactive)

    desired = ["dladdr","nwaddr"]
    mangle_prefix = "Built-in;"
    pairs = []
    print "===Host name-matching==="
    # TODO this is mildly horrible, for several reasons
    for fname,fdata in host_names.iteritems():
        for wname,wdata in host_data.iteritems():
            for d in desired:
                # This allows for a potential funkybug if webservice
                # values somehow come up as f or file values as w
                if fdata.get(d,'f').lower() == wdata.get(d,'w').lower():
                    print "%s matches %s on %s (%s)" % \
                          (fname, wname, d, fdata.get(d))
                    pairs.append((wname,mangle_prefix+fname))
    # Remove duplicate entries
    pairs = list(sets.Set(pairs))
    # TODO should also do a mapping of both sets of data to one, resolve
    # conflicts, and use the merged for dhcp
    if not pairs:
        print "None"
    print "\n"

    print "===Planned mapping==="
    if not pairs:
        print "None"
        print "\nTerminating..."
        exit(1)
    for src,dst in pairs:
        print src, "=>", dst
        print "  ", host_data[src]
    print "\n"

    proceed_check(interactive)

    for src,dst in pairs:
        rename = {'name':dst}
        h.put_host_info(src,rename)

        default_mac = "00:00:00:00:00:00"
        default_ip = "0.0.0.0"
        size = 10**12
        config_prefix = "fixed_address-%d-" % int(random.random()*size)
        cp = config_prefix
        dir,name = dst.split(';')
        config = {cp+"hostname": name,
                  cp+"directory": dir,
                  cp+"hwaddr": host_data[src].get('dladdr',default_mac),
                  cp+"ip4addr": host_data[src].get('nwaddr',default_ip)}
        h.put_dchp_config(config)

    print "\nAdding hosts complete"
