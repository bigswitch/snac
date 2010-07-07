# Handle debian interface configuration.  Specifically,
#
# Interfacing with ifconfig/ifup/ifdown
# Generating /etc/net/interface
#

from twisted.internet import protocol, reactor, defer

from nox.lib.netinet.netinet import ipaddr 

from nox.ext.apps.local_config.local_config import cfg_interface

import re
import os
import copy
import socket

lg = None

class IfInterface (cfg_interface) :

    def __init__(self, text):
        cfg_interface.__init__(self)
        self.process_text(text)

    def process_first_line(self, line):

        # assume first line has if name and type
        self.name = line.split(' ')[0] 
        
        line = line[len(self.name):].strip()

        p = re.compile('Link encap:\w+')
        encap = ''
        try:
            encap = p.search(line).group()
        except Exception, e:
            lg.error('could not find ifconfig encap line')
            raise Exception('Improper format')

        line = line[len(encap):].strip()
        self.encap = encap.split(':')[1]
        if self.encap.lower() == "ethernet":
            if line.find('HWaddr') == -1:
                # TODO: issue warning
                lg.error('ifconfig Ethernet line has no HWaddr')
                raise Exception('Improper format')
            self.hwaddr = line.split(' ')[1]    

    def process_inet_line(self, line):        
        p = re.compile('inet addr:[0-9]+\.[0-9]+.[0-9]+.[0-9]+')
        addr = ""
        try:
            addr = p.search(line).group()
            self.ip4addr = addr.split(':')[1]    
        except Exception, e:
            lg.error('could not find inet addr')
            raise Exception('could not find inet addr')
        addr = ''
        p = re.compile('Bcast:[0-9]+\.[0-9]+.[0-9]+.[0-9]+')
        try:
            addr = p.search(line).group()
            self.ip4bcast = addr.split(':')[1]    
        except Exception, e:
            pass
        addr = ''
        p = re.compile('Mask:[0-9]+\.[0-9]+.[0-9]+.[0-9]+')
        try:
            addr = p.search(line).group()
            self.ip4mask = addr.split(':')[1]    
        except Exception, e:
            pass

    def process_text(self, text):
        self.process_first_line(text[0])
        for line in text[1:]:
            line = line.strip()
            if line.startswith('inet addr'):
                self.process_inet_line(line)

            
class IfconfigListProcessProtocol(protocol.ProcessProtocol):

    ops = ["ifconfig", "-a"]

    def __init__(self, ifconfig_path, cb):
        self.ifpath = ifconfig_path
        self.interfaces = []
        self.data = ''
        self.cb   = cb
        ret = reactor.spawnProcess(self, self.ifpath, IfconfigListProcessProtocol.ops, {})

    def connectionMade(self):
        pass

    def process_if_chunk(self, chunk):    
        try:
            newif = IfInterface(chunk)
            self.interfaces.append(newif)
        except Exception, e:
            lg.error(str(e))
            pass

    def outReceived(self, data):
        # accumulate results until process closes connection
        self.data = self.data + data

    def outConnectionLost(self):
        data = self.data.split('\n')

        chunk = []
        for line in data:
            if line.strip() != '':
                chunk.append(line)
            else:
                if len(chunk) != 0:
                    self.process_if_chunk(copy.deepcopy(chunk))
                    chunk = []
        if len(chunk) != 0:
            self.process_if_chunk(copy.deepcopy(chunk))

        for iface in self.interfaces:
            lg.debug("found interface "+ iface.name+ " : "+ iface.ip4addr)

        self.cb(self.interfaces)    

class IfconfigSetProcessProtocol(protocol.ProcessProtocol):

    def __init__(self, ifconfig_path, interface, cb = None):
        self.ifpath = ifconfig_path
        self.cb   = cb
        # e.g.
        # ifconfig eth1 10.0.0.3 netmask 255.0.0.0 broadcast 10.255.255.255 
        ops = ['ifconfig', interface.name, interface.ip4addr, 'netmask',
               interface.ip4mask, 'broadcast', interface.ip4bcast]
        ret = reactor.spawnProcess(self, self.ifpath, ops, {})

    def connectionMade(self):
        pass

    def outReceived(self, data):
        # accumulate results until process closes connection
        # XXX: improve the error handling
        lg.error(data)

    def outConnectionLost(self):
        if self.cb:
            self.cb(True)    

class RouteSetGateway(protocol.ProcessProtocol):

    def __init__(self, _rpath, interface, cb = None):
        self.rpath = _rpath
        self.cb   = cb

        if not hasattr(interface, 'ip4gw') or interface.ip4gw == '':
            return

        # e.g.
        # route add default gw 192.168.1.1 dev eth0 
        ops = ['route', 'add', 'default', 'gw',  interface.ip4gw, 'dev'
               , interface.name]

        ret = reactor.spawnProcess(self, self.rpath, ops, {})

    def connectionMade(self):
        pass

    def outReceived(self, data):
        lg.error(data)

    def outConnectionLost(self):
        if self.cb:
            self.cb(True)    

class deb_net_config:

    route_cmd       = '/sbin/route'
    route_table     = '/proc/net/route'
    ifconfig_path   = '/sbin/ifconfig'
    interfaces_path = '/etc/network/interfaces'
    
    def create_new_interfaces_file(self):
        import shutil 
        import time
        import sys

        first_line = '#  Created by SNAC'

        if not os.path.isfile(deb_net_config.interfaces_path):
            lg.error('Could not find interfaces config file: '+
                      deb_net_config.interfaces_path)
            return    

        # if not NOX generated, lets create an original backup    
        try:
            line = open(deb_net_config.interfaces_path).readline()
            if not line.startswith(first_line):
                backup = deb_net_config.interfaces_path+'.orig.bak'
                shutil.copy(deb_net_config.interfaces_path, backup) 
            else:    
                backup = deb_net_config.interfaces_path+'.nox.bak'
                shutil.copy(deb_net_config.interfaces_path, backup) 
        except Exception, e:
            lg.error('Backing up '+
                      deb_net_config.interfaces_path +
                      " " + str(e))

        fd = None
        try:
             #fd = sys.stdout
             fd = open(deb_net_config.interfaces_path, 'w')
        except Exception, e:    
            lg.error('Opening: '+
                      deb_net_config.interfaces_path +
                      " " + str(e))
            return            
            
        fd.write(first_line + '\n')
        fd.write('#  Created on : ' + time.ctime() + '\n')
        fd.write("""\

# The loopback network interface
auto lo
iface lo inet loopback

""")
        for interface in self.interfaces:
            if interface.name == 'lo':
                continue
            fd.write("\n")
            fd.write("allow-hotplug " + interface.name + "\n")
            if interface.dhcp:
                fd.write("iface " + interface.name + " inet dhcp\n")
            else:    
                fd.write("iface " + interface.name + " inet static\n")
                fd.write("\taddress " + interface.ip4addr + "\n")
                fd.write("\tnetmask " + interface.ip4mask + "\n")
                if interface.ip4gw != "":
                    fd.write("\tgw " + interface.ip4gw + "\n")
                if interface.ip4dns != "":
                    fd.write("\tdns-nameservers " + interface.ip4dns + "\n")
        
        #fd.close()


    def set_interface(self, interface):

        old_if = None
        for i in range(0, len(self.interfaces)):
            intf = self.interfaces[i]
            if intf.name == interface.name:
                old_if = intf
                self.interfaces[i] = interface
        if not old_if:        
            lg.error('Attempting to set unknown interface '+interface.name)


        # Set interface using ifconfig
        IfconfigSetProcessProtocol(deb_net_config.ifconfig_path, interface)
        if interface.ip4gw != '':
            try:
                RouteSetGateway(deb_net_config.route_cmd, interface)
            except Exception,e :
                print e

        # Update /etc/network/interfaces
        self.create_new_interfaces_file()

    def if_table_created(self, res):
        lg.debug('created ndb interface table')

        def err(res):
            lg.error('unable to add row ' + str(res))

        # for each interface (except lo) add to interface table
        for interface in self.interfaces:
            if interface.name == 'lo':
                continue
            row = {'host' : self.hostname,
                   'name' : interface.name,
                   'ip'   : interface.ip4addr,
                   'mask' : interface.ip4mask,
                   'gw'   : interface.ip4gw,
                   'bcast' : interface.ip4bcast }
            d = self.config.storage.put(self.if_table_name, row)
            d.addErrback(err)
                                    

    def fill_gateways(self):                                
        """Go through local routing table and pull out the default route 
        """

        try:

            if not os.path.isfile(deb_net_config.route_table):
                lg.error('Could not locate routing table: '+
                          deb_net_config.route_table)
                return    
            fd = open(deb_net_config.route_table)
            if not fd:
                lg.error('Could not open routing table: '+
                          deb_net_config.route_table)
                return    
            lines = fd.readlines()
            fd.close()
            if len(lines) <= 1:
                return
            lines = lines[1:]    

            for line in lines:
                line = line.split('\t')
                ifname = line[0]
                if int(line[1],16) == 0:
                    gw = ipaddr(int(line[2], 16))
                    gw.addr = socket.ntohl(gw.addr)
                    lg.debug('found gateway' + ifname + str(gw))
                    for intf in self.interfaces:
                        if intf.name == ifname:
                            intf.ip4gw = str(gw)
                            return

        except Exception, e:
            lg.error(str(e))
            
    def gethostname(self):
        return socket.gethostname()

    def received_interfaces(self, if_list):

        self.interfaces = if_list
        self.fill_gateways()

        # create NDB table to store interface 
        def err(res):
            lg.error('Could not create interface table '+str(res))
        d = self.config.storage.create_table(self.if_table_name, 
                                         { 'host'  : str,
                                           'name'  : str,
                                           'ip'    : str,
                                           'mask'  : str,
                                           'gw'    : str,
                                           'bcast' : str},
                                           ())
        d.addCallback(self.if_table_created)                                    
        d.addErrback(err)
        return d


    # =================================================================    
    # deb_net_config.__init__
    # =================================================================    

    def __init__(self, config):
        global lg
        lg = config.lg


        self.config = config

    def init(self):
        self.if_table_name = 'local_interfaces'
        self.interfaces    = []
        self.hostname   =   self.gethostname() 

        if not os.access(deb_net_config.ifconfig_path, os.X_OK): 
            config.lg.error("Unable to execute "+deb_net_config.ifconfig_path+" check permissions?")
            return

        r = defer.Deferred()

        def callback(if_list):
            d = self.received_interfaces(if_list)

            def done(ign):
                r.callback(None)

            d.addCallback(done)
            
        # read all interfaces
        IfconfigListProcessProtocol(deb_net_config.ifconfig_path, callback)
        return r
