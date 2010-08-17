import logging
import simplejson

from nox.lib.core import *

from nox.webapps.webservice  import webservice

from nox.ext.apps.restracker.pyrestracker import pyrestracker

lg = logging.getLogger('restrackerws')

class pyrestrackerws(Component):
    """Webservice for internal resource tracking"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def getInterface(self):
        return str(pyrestrackerws)

    def _get_rt_host(self, request, arg):
        l = self.prt.get_host_counts()
        return simplejson.dumps(l)

    def install(self):
        self.prt  = self.resolve(pyrestracker)

        ws  = self.resolve(str(webservice.webservice))
        print 'WS', ws
        v1  = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/restracker
        rtpath = ( webservice.WSPathStaticString("restracker"), )

        # /ws.v1/restracker/host
        rthostpath = rtpath + \
                     ( webservice.WSPathStaticString("host"), )
        reg(self._get_rt_host, "GET", rthostpath,
            """Get number of packets per host for the current 10 second slice""")

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return pyrestrackerws(ctxt)

    return Factory()
