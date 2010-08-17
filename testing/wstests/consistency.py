#!/usr/bin/python
#######################
# Consistency Testing #
#######################

import sys,os
import httplib
import simplejson
import urllib

# Permit running from the packaged version
path = "/opt/nox/bin"

# Without this line, python can't find the NOX includes
sys.path.append(path)

from nox.webapps.webserviceclient import PersistentLogin, NOXWSClient

class ConsistencyTester:
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
        #self.debug = True
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


def d_up(dict,key,inc=1):
    dict[key] = dict.get(key,0) + inc

def d_down(dict,key):
    d_up(dict,key,-1)

def wsmangle(mangled):
    return mangled.replace(';','/')

def demangle(mangled):
    return mangled.split(';')

def d_cmp(d1,d2):
    if not ((type(d1) is dict) and (type(d2) is dict)):
        print "Not both dictionaries"
        return False
    if len(d1) != len(d2):
        print "Dictionaries are different lengths, %d != %d" % \
               (len(d1), len(d2))
        return False
    for k,v in d1.iteritems():
        if (type(v) is dict and not d_cmp(v,d2.get(k))) or \
           (v != d2.get(k,not v)):
            print "[%s] - %s != %s" % (k,v,d2.get(k))
            return False
    return True

def macify(dpid): 
    mac = "%012x" % dpid 
    mac = [mac[2*x:2*x+2] for x in xrange(len(mac)/2)] 
    return ":".join(mac) 


if __name__ == '__main__':
    ct = ConsistencyTester()
    ct.debug = False


    # soft assert
    def sass(assertion,errback,*errargs):
        try:
            assert assertion
        except:
            errback(*errargs)

    problems = {}
    # mo' problems
    def mop(what):
        d_up(problems,what)
    # sho' problems
    def shop():
        for p,num in problems.iteritems():
            print "Failed %d times trying to %s" % (num, p)

    # components
    problems = {}
    components = ct.get_info('/ws.v1/nox/components')
    id = components['identifier']
    version = ct.get_info('/ws.v1/nox/version')
    uptime = ct.get_info('/ws.v1/nox/uptime')
    for listed in components['items']:
        assert listed['version'] == version
        assert listed['uptime'] <= uptime
        assert listed['state'] == listed['required_state']
        name = listed[id]
        direct = lambda item: ct.get_info('/ws.v1/nox/component/%s/%s' % \
                                           (name,item))
#        sass(listed['version'] == direct('version'),\
#            mop,"compare listed and direct version")
#        sass(listed['uptime'] == direct('uptime'),\
#            mop,"compare listed and direct uptime")
        status = direct('status')
        assert name == status['name']
        assert status['state'] == status['required_state']
        # TODO dependency availability
    shop()


    # entity_counts
    listed = ct.get_info('/ws.v1/bindings/entity_counts')
    direct = {'active':{},'unregistered':{},'total':{}}
    principals = ['switch', 'location', 'host', 'user']
    plural = {'switch':'switches', 'location':'locations', \
               'host':'hosts','user':'users'}
    for principal in principals:
        pinfo = ct.get_info('/ws.v1/%s' % principal)
        pl = plural[principal]
        direct['total'][pl] = len(pinfo)
        active = 0
        registered = 0
        for p in pinfo:
            if ct.get_info('/ws.v1/%s/%s/active' % \
                            (principal, wsmangle(p))):
                active += 1

            if principal == 'switch':
                if ct.get_info('/ws.v1/%s/%s/approval' % \
                               (principal, wsmangle(p))):
                    registered += 1
            elif principal != 'host':
                registered += 1
                
        direct['active'][pl] = active
        if principal != 'host':
            direct['unregistered'][pl] = len(pinfo) - registered
        else:
            direct['unregistered'][pl] = \
                len(ct.get_info('/ws.v1/host/discovered'))
        
    assert d_cmp(listed,direct)


    # links
    links = ct.get_info('/ws.v1/link')
    dpids = {}
    for link in links:
        d_up(dpids,link['dpid1'])
        d_up(dpids,link['dpid2'])
    switches = ct.get_info('/ws.v1/switch')
    for sname in switches:
        dpid = ct.get_info('/ws.v1/switch/%s/config' % wsmangle(sname))['dpid']
        if dpid in dpids: del dpids[dpid]
    assert dpids == {}, "Links contain non-switch dpids: %s" % \
                         "\n\t".join([""]+["%s: %d" % (macify(d),n) for \
                                           d,n in dpids.iteritems()])

    
    # directory summation
    principals = ['switch', 'location', 'host', 'user']
    directory_info = ct.get_info('/ws.v1/directory/instance')
    id = directory_info['identifier']
    directories = [directory[id] for directory in directory_info['items']]
    for principal in principals:
        listed = ct.get_info('/ws.v1/%s' % principal)
        direct = []
        for directory in directories:
            direct.extend(ct.get_info('/ws.v1/%s/%s' % (principal,directory)))
        assert listed == direct


    # active bindings: host/user/location appear on conjugates
    principals = ['host', 'user', 'location']
    for p1_type in principals:
        for p2_type in principals:
            if p1_type == p2_type:  continue
            p1_list = ct.get_info('/ws.v1/%s' % p1_type)
            for p1 in p1_list:
                if not ct.get_info('/ws.v1/%s/%s/active' % \
                                    (p1_type, wsmangle(p1))):
                    continue
                p2_expected = ct.get_info('/ws.v1/%s/%s/active/%s' % \
                                           (p1_type,wsmangle(p1),p2_type))
                for p2 in p2_expected:
                    assert ct.get_info('/ws.v1/%s/%s/active' % \
                                        (p2_type,wsmangle(p2)))
                    assert p1 in ct.get_info('/ws.v1/%s/%s/active/%s' % \
                                              (p2_type,wsmangle(p2),p1_type))


    # TODO host interface matches info from location
    

    # group of principal is principal of group
    principals = ['host', 'location', 'switch', 'user']
    for principal in principals:
        pinfo = ct.get_info('/ws.v1/%s' % principal)
        for p in pinfo:
            ginfo = ct.get_info('/ws.v1/%s/%s/group' % \
                                (principal,wsmangle(p)))
            for g in ginfo:
                assert p in ct.get_info('/ws.v1/group/%s/%s/principal' % \
                                         (principal,wsmangle(g)))


    # TODO - give each of these their own instance, dependencies, etc.
    # that will work well. for many things =)
