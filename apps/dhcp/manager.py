# Copyright 2008 (C) Nicira, Inc.

"""
A component to restart the local ISC DHCP daemon whenever the
configuration has changed in the configuration database.
"""

import logging
import os
import simplejson
import StringIO

from signal import SIGKILL

from twisted.internet import defer, protocol, reactor
from twisted.python.failure import Failure

from nox.ext.apps.configuration.properties import Properties
from nox.webapps.webservice  import webservice
from twisted.python.failure import Failure
from nox.ext.apps.storage.transactional_storage import TransactionalStorage
from nox.ext.apps.dhcp.config import DHCPConfig
from nox.ext.apps.local_config.local_config import local_config
from nox.ext.apps.local_config.interface_change_event import interface_change_event
from nox.lib.core import *

log = logging.getLogger('nox.ext.apps.dhcp.manager')

CONFIG_KEY_CONFFILE = 'conffile'
CONFIG_KEY_INITSCRIPT = 'initscript'
CONFIG_SECTION = 'dhcp_config'

DEFAULTS = {
    'ddns-update-style' : [ 'none' ],
    'default-lease-time' : [ int(86400) ],
    'max-lease-time' : [ int(604800) ],
    'log-facility' : [ 'local7' ],
    'option_domain-name-servers' : [ '0.0.0.0' ]

    #'subnet-0-subnet' : [ '192.168.0.1' ],
    #'subnet-0-netmask' : [ '255.255.255.0' ],
    #'subnet-0-range-start' : [ '192.168.0.128' ],
    #'subnet-0-range-end' : [ '192.168.0.254' ],
    #'subnet-0-option routers' : [ '192.168.1.1' ],
    #'subnet-0-option domain-name' : [ 'nicira.com' ],
    #'subnet-0-option domain-name-servers' : [ '192.168.0.1' ],
}

class DHCPManager(Component):
    conffile = '/etc/dhcp3/dhcpd.conf'
    initscript = '/etc/init.d/dhcp3-server'
    timeout = 30.0 # seconds to wait for restart script to complete
    daemon_check_interval = 60.0 # interval between 'initscript status' calls

    """
    # of restarts requests.
    """
    restart = 0
    check = 0
    script_running = False
    daemon_running = False
    timer = None
    previous_error = ''

    def getInterface(self):
        return str(DHCPManager)

    def configure(self, configuration):
         for param in configuration['arguments']:
            if param.find('=') != -1:
                key, value = param[:param.find('=')], param[param.find('=')+1:]
            else:
                key, value = param, ''

            if key == CONFIG_KEY_CONFFILE:
                self.conffile = value
            elif key == CONFIG_KEY_INITSCRIPT:
                self.initscript = value

    def install(self):
        self.cfg = self.resolve(local_config)
        self.storage = self.resolve(TransactionalStorage)
        self.register_for_bootstrap_complete(self.changed)
        self.register_handler(interface_change_event.static_get_name(),
                              self.changed)

        ws = self.resolve(str(webservice.webservice))
        v1 = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/nox
        noxpath = ( webservice.WSPathStaticString("nox"), )

        # /ws.v1/nox/stat
        noxstatpath = noxpath + ( webservice.WSPathStaticString("dhcp"), )

        reg(self.get_dhcp_status, "GET", noxstatpath, """Get DHCP status""")

        # Store the defaults to the database, if necessary.
        p = Properties(self.storage, CONFIG_SECTION, DEFAULTS)
        return p.begin().\
            addCallback(lambda ign: p.commit())

    def err(self, failure, request, fn_name, msg):
        log.error('%s: %s' % (fn_name, str(failure)))
        return webservice.internalError(request, msg)

    def get_dhcp_status(self, request, arg):
        try:
            if self.daemon_running:
                return simplejson.dumps(['active'])
            else:
                return simplejson.dumps(['inactive', self.previous_error])
        except Exception, e:
            return self.err(Failure(), request, "get_dhcp_status",
                            "Could not retrieve DHCP status.")

    def changed(self, *args):
        """
        Restart the DHCP server to guarantee its using the
        configuration in the database. Note, this is called on runtime
        whenever the database configuration changes.
        """
        log.debug("Scheduling for immediate restart.")
        self.schedule('restart', 0)
        return CONTINUE

    def __tickle(self):
        if not self.script_running and self.restart > 0:
            self.restart = 0
            self.check = 0
            self.script_running = True
            reactor.callLater(0, self.reconfigure)

        elif not self.script_running and self.check > 0:
            self.check = 0
            self.script_running = True
            reactor.callLater(0, self.check_daemon)

    def schedule(self, type_, delay):
        # Restart request overrides any previous call, but check
        # request only an earlier check call.
        if type_ == 'restart' or self.restart == 0:
            if self.timer:
                self.timer.cancel()
                self.timer = None

        def call():
            self.timer = None
            self.__tickle()

        if type_ == 'restart': self.restart += 1
        elif type_ == 'check': self.check += 1
        else: assert(False)

        self.timer = reactor.callLater(delay, call)

    def reconfigure(self):
        """
        Load the configuration and restart the daemon.
        """
        log.debug('Reconfiguring and restarting the DHCP daemon...')

        # Don't set the daemon running status here, but let the status
        # check take care of that.

        p = Properties(self.storage, CONFIG_SECTION)
        p.addCallback(self.changed).\
            addCallback(lambda trigger: p.load()).\
            addCallback(self.emit_config, p).\
            addCallback(self.restart_daemon).\
            addErrback(self.restart_error)

    def restart_error(self, failure):
        delay = 3
        log.debug('Retrying to restart in %d seconds.', delay)
        self.script_running = False

        self.schedule('restart', delay)

        log.exception(failure)

    def emit_config(self, ign, p):
        config = DHCPConfig(self.cfg)
        config.load(p)
        s = config.emit()

        f = open(self.conffile, 'w') # erases the existing file
        f.write(s)
        f.flush()
        os.fsync(f.fileno())
        f.close()

        return config

    def set_daemon_running(self, status):
        """
        Set the daemon status and optionally notify the network event
        log. Can return a deferred, but can't ever return/throw an
        error.
        """
        if status:
            log.debug("The DHCP daemon is running")
        else:
            log.debug("The DHCP daemon is NOT running")

        self.daemon_running = status

        # XXX: write the network log

        return defer.succeed(None)

    def check_daemon(self):
        """
        Check whether DHCP daemon is running or not.
        """
        log.debug("Checking for the DHCP daemon status.")

        d = defer.Deferred()
        args = ( self.initscript, 'status' )
        env = dict(os.environ)

        process = reactor.spawnProcess(OutputGrabber(d), self.initscript,
                                       args=args, env=env)

        def try_restart(ign, status):
            self.script_running = False

            if not status:
                log.debug("Scheduling for immediate restart.")
                self.schedule('restart', 0)
            else:
                log.debug("Scheduling the next status check.")
                self.schedule('check', self.daemon_check_interval)

        def complete(output, timer):
            try:
                timer.cancel()
            except:
                pass

            # Use heuristics to determine whether the script succeeded
            # or not.
            running = output.find('is running') != -1

            return defer.succeed(running).\
                addCallback(self.set_daemon_running).\
                addCallback(try_restart, running)

        def abort(process, d):
            log.error("Script timeout while checking DHCP daemon status. " + 
                      "Killing the script.")
            try:
                process.signalProcess(SIGKILL)
            except:
                log.exception("Unable to kill the script process.")

            # Don't call errback here, but let the process die and
            # complete function above handle the error.

            #d.errback(Failure(RuntimeError('Init script timeout (check)')))

        def error(failure):
            log.exception(failure)

            return defer.succeed(False).\
                addCallback(self.set_daemon_running).\
                addCallback(try_restart, False)

        timer = reactor.callLater(self.timeout, abort, process, d)

        return d.addCallback(complete, timer).\
            addErrback(error)

    def restart_daemon(self, config):
        d = defer.Deferred()
        if len(config.subnets):
            log.debug("Restarting the daemon.")

            restarting = True
            args = ( self.initscript, 'restart' )
        else:
            log.debug("Stopping the daemon.")

            restarting = False
            args = ( self.initscript, 'stop' )
        env = dict(os.environ)

        process = reactor.spawnProcess(OutputGrabber(d), self.initscript,
                                       args=args, env=env)

        def complete(output, timer, restarting):
            try:
                timer.cancel()
            except:
                pass
            self.script_running = False

            # Use heuristics to determine whether the script succeeded
            # or not.
            if restarting:
                i = output.find('tarting')
                if i == -1:
                    self.previous_error = output
                    raise RuntimeError('DHCP daemon did not restart:\n%s' % \
                                           output)

                if output.find('fail', i) != -1:
                    self.previous_error = output
                    raise RuntimeError('DHCP daemon did not restart:\n%s' % \
                                           output)

                self.previous_error = ''
                log.debug('DHCP daemon restarted successfully. Scheduling ' + 
                          'for immediate status check.')
                self.schedule('check', 0)
            else:
                log.debug('DHCP daemon stopped successfully.')

        def abort(process, d):
            log.error("Script timeout while restarting daemon. " + 
                      "Killing the script.")
            try:
                process.signalProcess(SIGKILL)
            except:
                log.exception("Unable to kill the script process.")

            # Don't call errback here, but let the process die and
            # complete function above handle the error.

            #d.errback(Failure(RuntimeError('Init script timeout (restart)')))

        timer = reactor.callLater(self.timeout, abort, process, d)

        return d.addCallback(complete, timer, restarting)

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
        def instance(self, ctxt): return DHCPManager(ctxt)

    return Factory()
