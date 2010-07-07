# Proxy to handle client-level redirects.  
#
# - Binds to a server port (tcp)
# - On client connection, if the request is for something other than the
#   captive portal, sends a redirect to the captive portal 
# - Requests to captive portal are forwarded to the captive port.
#
# This is intended to be used with policy rules that intercept
# communication to a standard HTTP proxy and rewrite the header to point
# to the redir proxy.  Take for example the following topology:
#
#                               192.168.1.18
#                        +---------<nox>
#                        |              
#   <client> -------- <switch> --------- <proxy>
#                                      192.168.1.14
#
# The FSL rules would look as follows:
#
# http_proxy_redirect('00:a0:cc:28:a9:94', '192.168.1.18', '9999') <=
# usrc('discovered;unauthenticated') ^ nwdst('192.168.1.14') ^
# tpdst(3128)
#
# http_proxy_undo_redirect('00:1A:92:40:AC:05', '192.168.1.14', '3128')
# <= nwsrc('192.168.1.18') ^ tpsrc(9999)
#
# This assumes that NOX's MAC address is: 00:a0:cc:28:a9:94 
# and the proxie's MAC address is: 00:1A:92:40:AC:05
#

import logging

from nox.lib.core import Component 

from nox.apps.storage import TransactionalStorage
from nox.apps.configuration.properties import *
from twisted.web import static, server, resource
from twisted.internet import defer, reactor
from twisted.internet.protocol import ServerFactory, Protocol, ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred
from random import Random
import string
import urllib
import time

lg = logging.getLogger('redirproxy')

DEFAULT_REDIR_PORT = 9999
MAX_COOKIE_AGE_SEC = 60 * 5
STALE_CHECK_INTERVAL_SEC = 30

def write_gateway_error(t): 
  t.write("HTTP/1.0 501 Gateway error\r\n")
  t.write("Content-Type: text/html\r\n")
  t.write("\r\n")
  t.write('''<H1>Could not connect</H1>''')

# Note: the terms 'local' and 'remote' in this file are relative to a
# client authenticating via captive portal.  Thus, a 'local connection'
# is between the client and the proxy, while the 'remote connection' is
# between the proxy and the captive portal.  This can be confusing, since
# the connection between the proxy and the captive portal is actually over
# the loopback, since both of them are currently NOX component.  Sorry. 

class RemoteConnection(Protocol): 
    
    def __init__(self, d, local_conn):
      local_conn.remote_conn = self
      self.local_conn = local_conn
      self.d = d

    def connectionMade(self):
      self.local_conn.transport.write('HTTP/1.0 200 Connection established\r\n')
      self.local_conn.transport.write('Proxy-agent NOX Simple Proxy\r\n')
      self.local_conn.transport.write('\r\n') 
      # tell the local connection that it can stop buffering data
      # and instead send it directly via the RemoteConnection
      self.d.callback("success") 

    def connectionLost(self,reason): 
      lg.debug('captive portal server disconnected')
      self.local_conn.transport.loseConnection() 

    def dataReceived(self, data): 
      self.local_conn.transport.write(data) 


class RemoteConnectionFactory(ClientFactory): 
    
    def __init__(self, local_conn, d):
       self.local_conn = local_conn
       self.d = d

    def buildProtocol(self, addr):
        return RemoteConnection(self.d, self.local_conn)

    def clientConnectionFailed(self, connector, reason):
        lg.error("redirproxy remote connection failed") 
        write_gateway_error(self.local_conn.transport) 
        self.local_conn.transport.loseConnection()


# a simple twisted protocol class to handle 
# SSL HTTP proxy requests that use the 'CONNECT' method
class LocalConnection(LineReceiver):
    def __init__(self):
        self.method = None
        self.remote_conn = None
        self.remote_ready = False
        self.buffered_data = "" 

    def lineReceived(self,line):
        try: 
          if self.method is None: 
            arr = line.split()
            self.method = arr[0]
            if self.method == "GET" or self.method == "POST" \
                                    or self.method == "PUT":
              # this is regular HTTP, send it a redirect to the captive portal
              peer = self.transport.getPeer()
              cookie =  ''.join( Random().sample( \
                              string.letters+string.digits, 20) )
              # store the cookie -> IP mapping with main component 
              self.factory.redirproxy.addCookie(cookie, peer.host) 
              redir_url = self.factory.redirproxy.redir_url + "?rurl=" + \
                        urllib.quote_plus(arr[1]) + "&proxy_cookie=" + \
                        urllib.quote_plus(cookie)
              self.sendRedirectAndClose(redir_url) 
            elif self.method == "CONNECT":
              # we don't actually want to proxy, just connect to local HTTPS
              host = '127.0.0.1'
              port = '443'
              d = Deferred()
              reactor.connectTCP(host, int(port), 
                  RemoteConnectionFactory(self,d))
              d.addCallback(self.remote_conn_success)
            else: 
              raise Exception("invalid method '%s'" % self.method) 
          # if self.method is set, it must be set to 'CONNECT',
          # so we should keep reading in header lines until we get a 
          # blank line, then switch to raw mode to proxy the SSL content
          elif line == "": 
            # switch to raw mode
            self.setRawMode()  
        except Exception, e:
            import traceback
            traceback.print_exc(e)
            write_gateway_error(self.transport)  
            self.transport.loseConnection()

    def rawDataReceived(self,data): 
      # write remaining data to   
      if not self.remote_ready:
        if len(self.buffered_data) > 10000: 
          # don't buffer infinitely. since the only valid use of
          # this connection is HTTPS and the ClientHello message is
          # small, there should be no need to buffer much data
          self.transport.loseConnection()
          return

        self.buffered_data += data
      else: 
        self.remote_conn.transport.write(data) 

    def remote_conn_success(self,res):
        self.remote_ready = True
        self.remote_conn.transport.write(self.buffered_data)

    def sendRedirectAndClose(self,url): 
      self.transport.write("HTTP/1.0 307 Temporary Redirect\r\n")
      self.transport.write("Content-Type: text/html\r\n")
      self.transport.write("Location: %s\r\n" % url)
      self.transport.write("\r\n")
      self.transport.write("<H1>Click <a href='%s'> here </a> to login to the network</a></H1>" % url)
      self.transport.loseConnection() 
    
    def connectionLost(self,reason): 
      if not self.remote_conn is None:
        self.remote_conn.transport.loseConnection() 
     

class redirproxy(Component):

    def __init__(self,ctxt):
        Component.__init__(self, ctxt)
        self.cookie_cache = {} 
        self.cookie_times = {} 

    def addCookie(self,cookie, ip_str): 
        self.cookie_cache[cookie] = ip_str
        self.cookie_times[cookie] = time.time() 

    def getIPFromCookie(self,cookie): 
        return self.cookie_cache.get(cookie,None) 
        
    def cleanCookies(self): 
      now = time.time()
      for c,ts in self.cookie_times.items():
        if (now - ts) > MAX_COOKIE_AGE_SEC: 
          del self.cookie_times[c]
          del self.cookie_cache[c]
      self.post_callback(STALE_CHECK_INTERVAL_SEC,self.cleanCookies) 

    def configure(self, conf):
        self.port = DEFAULT_REDIR_PORT
        args = conf['arguments']
        if len(args) > 0:
            try:
                self.port = int(args[0]) 
            except:
                lg.error('Unable to convert arg to int for port '+args[0])
        lg.debug('Binding to port ' + str(self.port))        

    # We need to grab new url if configuration changes
    def _config_update_cb(self):

        def properties_loaded(res):
            if not 'redir_url' in self.props:
                lg.error('redir_url not defined in configuration properties')
                self.redir_url = '(contact admin)'
            else:
                self.redir_url = str(self.props['redir_url'][0])

        lg.debug("Configuration updated")
        d = self.props.begin()
        d.addCallback(lambda x : self.props.load())
        d.addCallback(lambda x : self.props.commit())
        d.addCallback(properties_loaded)
        d.addCallback(lambda x: self.props.addCallback(self._config_update_cb))
        return d

    def install(self):
        self.post_callback(MAX_COOKIE_AGE_SEC + 1,self.cleanCookies) 
        self.storage = self.resolve(TransactionalStorage)
        if self.storage is None:
            raise Exception("Unable to resolve required component: '%s'" %
                            str(TransactionalStorage))

        def properties_loaded(res):

            if not 'redir_url' in self.props:
                lg.error('redir_url not defined in configuration properties')
                self.redir_url = '(contact admin)'
            else:
                self.redir_url = str(self.props['redir_url'][0])

            f = ServerFactory()
            f.protocol = LocalConnection
            f.redirproxy = self
            self.port = reactor.listenTCP(self.port, f)


        # Load captive web-portal properties so we know who to redirect to
        # I don't want to copy this, but otherwise we get import errors
        # because of circular dependancies
        PROPERTIES_SECTION = "captive_portal_settings"
        self.props = Properties(self.storage, PROPERTIES_SECTION)

        #properties requires an exclusive transaction for a load
        d = self.props.begin()
        d.addCallback(lambda x : self.props.load())
        d.addCallback(lambda x : self.props.commit())
        d.addCallback(properties_loaded)
        d.addCallback(lambda x: self.props.addCallback(self._config_update_cb))
        return d

    def getInterface(self):
        return str(redirproxy)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return redirproxy(ctxt)

    return Factory()
