# Copyright 2008 (C) Nicira, Inc.

import logging
import os
import re
import simplejson
import StringIO

from os import stat
from signal import SIGKILL
from stat import ST_SIZE

from twisted.internet import defer, protocol, reactor
from twisted.python.failure import Failure
from twisted.web import server, static

from nox.lib.core import *

from nox.apps.coreui.authui import UIResource
from nox.apps.coreui import webservice

lg = logging.getLogger('logws')

NOX_DUMP = '/tmp/nox-dump.tar'

class logws(Component):
    """Web service interface info about logs"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.timeout = 30 * 60 # if we can't dump in 30 minutes, we
                               # are doomed anyway.

        # XXX: wildcards are not supported currently, only exact file
        # and directory names.
        self.locations = [ 
            '/var/log' 
        ]
        self.status = '--'

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        return webservice.internalError(request, msg)

    def install(self):
        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/nox
        noxpath = ( webservice.WSPathStaticString("nox"), )

        # /ws.v1/nox/dump/status
        noxdumpstatuspath = noxpath + \
            ( webservice.WSPathStaticString("dump"), 
              webservice.WSPathStaticString("status") )
        reg(self.get_dump_status, "GET", noxdumpstatuspath,
            """Get current NOX dump status""")
        reg(self.put_dump_status, "PUT", noxdumpstatuspath,
            """Initiate the NOX dump process""")

        # /ws.v1/nox/dump/file
        noxdumpstatuspath = noxpath + \
            ( webservice.WSPathStaticString("dump"), 
              webservice.WSPathStaticString("dump.tar.gz") )
        reg(self.get_dump_file, "GET", noxdumpstatuspath,
            """Get NOX dump file""")

    def put_dump_status(self, request, arg): 
        try:
            self.dump()
            return simplejson.dumps('success');
        except Exception, e:
            return self.err(Failure(), request, "put_dump_status",
                            "Could not initiate dump process.")

    def get_dump_status(self, request, arg):
        try:
            return simplejson.dumps(self.status);
        except Exception, e:
            return self.err(Failure(), request, "get_dump_status",
                            "Could not dump NOX status.")

    def dump(self):
        """
        Fork a dump
        """
        if self.status == 'dumping':
            return
            
        self.status = 'dumping'

        d = defer.Deferred()
        tar = '/bin/tar'
        args = [ tar, 'cfz', NOX_DUMP ]
        for path in self.locations:
            args.append(path)

        env = dict(os.environ)

        process = reactor.spawnProcess(OutputGrabber(d), tar,
                                       args=args, env=env)

        def success(output, timer):
            lg.debug('Completed: ' + output)
            timer.cancel()
            self.status = 'complete'

        def abort(process, d):
            # Spawned init script is not complete yet, just kill it.
            process.signalProcess(SIGKILL)
            d.errback(Failure(RuntimeError('Init script timeout')))

        timer = reactor.callLater(self.timeout, abort, process, d)

        d.addCallback(success, timer)
        d.addErrback(self.dump_error)

    def dump_error(self, failure):
        lg.exception(failure)
        self.status = 'error'
        
    def get_dump_file(self, request, arg):
        try:
            request.setHeader('content-type', 'application/x-tar')
            request.setHeader('content-encoding', 'gzip')
        
            if request.method == 'HEAD':
                return ''

            self.status = '--'

            statinfo = stat(NOX_DUMP)
            size = statinfo[ST_SIZE]
            f = open(NOX_DUMP, 'rb')
            
            static.FileTransfer(f, size, request)
            return server.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_dump_file",
                            "Could not retrieve dump file.")

    def getInterface(self):
        return str(logws)

class LogRes(UIResource, static.File):
    required_capabilities = set([ "viewsettings" ] )

    def __init__(self, component, file):
        UIResource.__init__(self, component)
        static.File.__init__(self, file)

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

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return logws(ctxt)

    return Factory()
