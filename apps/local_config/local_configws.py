import os
import logging
import StringIO

from twisted.internet import defer, protocol, reactor

from nox.lib.core    import *
from nox.webapps.webservice import webservice

from nox.ext.apps.local_config.local_config import *

from nox.webapps.webservice.webservice import json_parse_message_body
from nox.webapps.webservice.webservice import NOT_DONE_YET,WSPathArbitraryString
from nox.webapps.webservice.web_arg_utils import *

from twisted.python.failure import Failure

import simplejson

lg = logging.getLogger('local_configws')

class local_configws(Component):

    shutdown_scripts = {
        'system' : ('/sbin/shutdown', '-h', 'now')
        #'process' : ('/etc/init.d/nox', 'stop')
    }

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def get_hostname(self, request, arg):
        return simplejson.dumps(self.cfg.get_hostname())

    def install(self):

        self.cfg = self.resolve(local_config)

        ws  = self.resolve(str(webservice.webservice))

        v1  = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/nox/local_config/hostname
        #nox_local_config_hostname = ( webservice.WSPathStaticString("nox"),
        #                              webservice.WSPathStaticString("local_config"),
        #                              webservice.WSPathStaticString("hostname"), )
        #reg(self.get_hostname, "GET", nox_local_config_hostname,
        #        """Get server hostname""")

        # GET /ws.v1/nox/local_config/active/interface/<interface>
        nox_local_config = ( webservice.WSPathStaticString("nox"),
                             webservice.WSPathStaticString("local_config"),
                             webservice.WSPathStaticString("active"),
                             webservice.WSPathStaticString("interface") )
        reg(self.get_interfaces, "GET", nox_local_config, """Get active interfaces""")

        # GET /ws.v1/nox/local_config/interface/<interface>
        nox_local_config = ( webservice.WSPathStaticString("nox"),
                             webservice.WSPathStaticString("local_config"),
                             webservice.WSPathStaticString("interface"),
                             WSPathValidInterfaceName(self) )
        reg(self.get_interface, "GET", nox_local_config, """Get interface config""")

        # PUT /ws.v1/nox/local_config/interface/<interface>
        # fmt:
        # {
        #    "name": "eth0",
        #    "dhcp" : false, # if set, all address fields are ignored
        #    "ip4dns": "192.168.1.14",
        #    "ip4mask": "255.255.255.0",
        #    "ip4addr": "192.168.1.18",
        #    "ip4bcast": "192.168.1.255",
        #    "hwaddr": "00:a0:cc:28:a9:94",
        #    "ip4gw": "192.168.1.1"
        # }
        nox_local_config = ( webservice.WSPathStaticString("nox"),
                             webservice.WSPathStaticString("local_config"),
                             webservice.WSPathStaticString("interface"),
                             WSPathValidInterfaceName(self) )
        reg(self.put_interface, "PUT", nox_local_config, """Put interface config""")

        # PUT /ws.v1/nox/local_config/shutdown
        # fmt: 'system' or 'process'
        nox_shutdown = ( webservice.WSPathStaticString("nox"),
                         webservice.WSPathStaticString("local_config"),
                         webservice.WSPathStaticString("shutdown") )
        reg(self.shutdown, "PUT", nox_shutdown, """Shutdown the system/process""")

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        return webservice.internalError(request, msg)

    def get_interfaces(self, request, arg):
        try:
            iflist = self.cfg.get_interfaces()
            ifnames = []
            for item in iflist:
                ifnames.append(item.name)

            return simplejson.dumps(ifnames)
        except Exception, e:
            return self.err(Failure(), request, "get_interfaces",
                            "Could not retrieve active interface information.")

    def get_interface(self, request, arg):
        try:
            name = arg["<interface>"]

            iflist = self.cfg.get_interfaces()
            ifnames = []
            for item in iflist:
                if item.name == name:
                    request.write(simplejson.dumps(item.get_dict()))
                    request.finish()
                    return NOT_DONE_YET

            return webservice.internalError(request, "Could not look up interface %s." % name)
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_interface",
                            "Could not retrieve interface information.")

    def put_interface(self, request, arg):
        try:
            intf = cfg_interface()
            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            try:
                if not 'name' in content:
                    return webservice.badRequest(request, "Cannot configure interface: Name parameter not present.")
                intf.name = str(content['name'])
                if 'hwaddr' in content:
                    intf.hwaddr = str(content['hwaddr'])
                if 'ip4addr' in content:
                    intf.ip4addr = str(content['ip4addr'])
                if 'ip4mask' in content:
                    intf.ip4mask = str(content['ip4mask'])
                if 'ip4bcast' in content:
                    intf.ip4bcast = str(content['ip4bcast'])
                if 'ip4gw' in content:
                    intf.ip4gw = str(content['ip4gw'])
                if 'ip4dns' in content:
                    intf.ip4dns = str(content['ip4dns'])
                if 'dhcp' in content:
                    intf.dhcp = content['dhcp']
            except Exception, e:
                f = Failure()
                lg.error("put_interface_config: error reading interface information from request:" + str(f))
                return webservice.badRequest(request,"Cannot configure interface: invalid content parameters.")
            self.cfg.set_interface(intf)
            return simplejson.dumps(True)
        except Exception, e:
            return self.err(Failure(), request, "put_interface_config",
                            "Could not configure interface.")

    def shutdown(self, request, arg):
        try:
            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, 
                                             "Unable to parse message body.")

            if not content in self.shutdown_scripts:
                return webservice.badRequest(request, "Cannot shutdown '%s'." % 
                                             content)

            d = defer.Deferred()
            args = self.shutdown_scripts[content]
            env = dict(os.environ)

            process = reactor.spawnProcess(OutputGrabber(d), 
                                           self.shutdown_scripts[content][0],
                                           args=args, env=env)

            def success(output):
                lg.debug("Shutdown completed:\n%s" % output)

            def error(failure):
                lg.error("Shutdown did not complete:\n%s" % str(failure))

            d.addCallback(success).\
                addErrback(error)

            return simplejson.dumps(True)
        except Exception, e:
            return self.err(Failure(), request, "shutdown",
                            "Could not shutdown the system/process.")

    def getInterface(self):
        return str(local_configws)

class OutputGrabber(protocol.ProcessProtocol):
    """
    Grab stdout and stderr of a child process to a string.
    """
    def __init__(self, d):
        self.d, self.s = d, StringIO.StringIO()

    def outReceived(self, t):
        self.s.write(t)

    errReceived = outReceived

    def processEnded(self, reason):
        self.d.callback(self.s.getvalue())

class WSPathValidInterfaceName(webservice.WSPathComponent):
  def __init__(self, ws):
      webservice.WSPathComponent.__init__(self)
      self.ws = ws

  def __str__(self):
      return "<interface>"

  def extract(self, pc, data):
      if pc == None:
          return webservice.WSPathExtractResult(error="End of requested URI")
      try:
          interfaces = self.ws.cfg.get_interfaces()
          for item in interfaces:
              if item.name == pc:
                  return webservice.WSPathExtractResult(value=pc)
      except Exception, e:
          pass
      e = "Invalid interface name '" + pc + "'."
      return webservice.WSPathExtractResult(error=e)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return local_configws(ctxt)
    return Factory()
