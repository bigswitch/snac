# Copyright 2008 (C) Nicira, Inc.

import logging
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, succeed

from nox.apps.bindings_storage.pybindings_storage \
    import pybindings_storage, Name
from nox.apps.configuration import Properties
from nox.apps.coreui import coreui
from nox.apps.pyrt.pycomponent import *
from nox.apps.storage import TransactionalStorage, TransactionalConnection
from nox.apps.user_event_log.pyuser_event_log import pyuser_event_log
from nox.apps.user_event_log.networkeventsws import make_entry
from nox.lib.core import *

log = logging.getLogger("notifier")

__all__ = [ "Destination" ]


class Destination:
    """
    Notification destinations are plugins, which provide best-effort
    logging interface towards external systems.
    """
    def __init__(self, params={}):
        pass

    def init(self):
        return True

    def log(self, event):
        raise NotImplementedError

class LogDestination(Destination):
    """
    Log destination for debugging purposes.
    """

    def __init__(self, params={}):
        # Nothing to do with the params
        pass

    def log(self, event):
        log.info('Network event: ' + str(event))

class Rule:
    """
    Matcher checkes whether an event matches to the configured
    criterion.
    """
    def matches(self, event):
        raise NotImplementedError

class CombinedRule(Rule):
    def __init__(self, definition):
        definition = definition.rstrip().lstrip()
        if definition.lower() == 'and':
            self.matches = self.__and
        else:
            self.matches = self.__or
        self.rules = []

    def addRule(self, rule):
        self.rules.append(rule)

    def __and(self, event):
        for rule in self.rules:
            if not rule.matches(event):
                return False

        return True

    def __or(self, event):
        for rule in self.rules:
            if rule.matches(event):
                return True

        return False

class FieldComparisonRule(Rule):
    def __init__(self, definition):
        definition = definition.rstrip().lstrip()
        self.field, op, self.value = definition.split(' ')
        try:
            # XXX: For now, map all numeric values to floats
            self.value = float(self.value)
        except ValueError:
            pass

        ops = {
            '<': lambda x, y: cmp(x, y) < 0,
            '<=': lambda x, y: cmp(x, y) <= 0,
            '>': lambda x, y: cmp(x, y) > 0,
            '>=': lambda x, y: cmp(x, y) >= 0,
            '==': lambda x, y: cmp(x, y) == 0,
            '!=': lambda x, y: cmp(x, y) != 0,
        }

        if not op in ops.keys():
            raise ValueError('Invalid op: ' + op)
        self.op = ops[op]

        if not self.field in [ 'app', 'timestamp', 'app', 'level', 'msg']:
            raise ValueError('Invalid field: ' + self.field)

    def matches(self, event):
        try:
            event_field_value = event.__getitem__(self.field)
            return self.op(event_field_value, self.value)
        except AttributeError, e:
            pass

        return False

class Filter:
    """
    """
    def __init__(self, matcher, destinations):
        self.m = matcher
        self.destinations = destinations

    def __call__(self, event):
        d = Deferred()
        d.callback(None)

        def report(result):
            pass

        if self.m.matches(event):
            l = []
            for destination in self.destinations:
                d = destination.log(event)
                if isinstance(d, Deferred):
                    l.append(d)

            dl = DeferredList(l, fireOnOneCallback=False,
                              fireOnOneErrback=False,
                              consumeErrors=True)
            dl.addCallback(report) # DeferredList never calls an errback
        else:
            pass

        return d

class Notifier(Component):
    """
    Event notifier periodically retrieves the latest user log events
    and feeds them to the configured plugins.

    The notifier reconfigures itself on any configuration changes.
    """

    EVENT_POLL_INTERVAL = 1.0
    prev_id = -1

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None
        self.filters = []
        self.plugin_factories = {}

    def getInterface(self):
        return str(Notifier)

    def install(self):
        self.uel = self.resolve(pyuser_event_log)
        self.storage = self.resolve(TransactionalStorage)

        # Scan for plugins
        component_path = 'nox/ext/apps/notification/'
        for mod in os.listdir(component_path):
            if mod.endswith('.py'):
                try:
                    p = __import__(component_path + mod[0:-3])
                    type, factory = p.get_plugin_factory()
                    self.plugin_factories[type] = factory

                except ImportError, e:
                    # Unable to import the plugin candidate,
                    # definitely a bug.
                    log.exception("Import error")
                except AttributeError, e:
                    # Unable to find factory function, not necessarily
                    # an error
                    log.debug("No factory found for '%s'." % mod)

        def prepare_next(result):
            reactor.callLater(self.EVENT_POLL_INTERVAL, self.check_events)
            
        return self.reconfigure_filters().\
            addCallback(prepare_next)

    def trigger_reconfiguration(self):
        self.pending_reconfiguration = True

        if not self.active_reconfiguration:
            log.debug("Configuration changed, triggering reconfiguration")

            self.active_reconfiguration = True
            reactor.callLater(0, self.reconfigure_filters)
        else:
            log.debug("Configuration changed, informing ongoing reconfiguration")

    def reconfigure_filters(self):
        # Read the configuration from the database and install a
        # trigger to detect any configuration changes in the database
        # When reconfiguring, merely replace the self.filter with a
        # new one
        log.debug("Entering reconfiguration phase")
        self.pending_reconfiguration = False
        self.active_reconfiguration = True

        p = Properties(self.storage, 'notifier_config')

        def get(p, tag):
            params = {}

            for key in p.keys():
                if not key.startswith(tag + '.'):
                    continue

                value = p[key]

                key = key[len(tag + '.'):]
                dot_i = key.find('.')
                n = int(key[0:dot_i])
                key = key[dot_i + 1:]
                
                if not params.has_key(n):
                    params[n] = { }

                params[n][key] = value
                
            return params

        def load(result, p):
            return p.load()

        def parse_plugins(ignore, p):
            filters = []

            # First parse the destinations and instantiate the new
            # plugins.  Let the plugin itself take care of the actual
            # parsing of key-value pairs.
            params = get(p, 'destination')
            destinations = {}
            for key in params.keys():
                n = params[key]
                if not n.has_key(u'name') or \
                        not n.has_key(u'type') or \
                        not self.plugin_factories.has_key(n[u'type'][0]):
                    continue

                try:
                    destinations[n['name'][0]] = \
                        self.plugin_factories[n['type'][0]](n)
                except:
                    log.exception('Unable to instantiate to a notifier plugin.')
            return destinations

        def init_plugins(destinations):
            initialized_destinations = {}

            def init_plugin(ignore, name, plugin):
                def initialized(ret):
                    if ret: initialized_destinations[name] = plugin

                def error(failure):
                    try:
                        failure.raiseException()
                    except:
                        log.exception("Unable to initialize a notifier plugin.")

                return succeed(None).\
                    addCallback(lambda ign: plugin.init()).\
                    addCallback(initialized).\
                    addErrback(error)

            d = succeed(None)

            for name in destinations.keys():
                d.addCallback(init_plugin, name, destinations[name])
                
            return d.addCallback(lambda ign: initialized_destinations)

        def parse_rules(destinations, p):
            # Then parse the rules
            params = get(p, 'rule')

            filters = []
            for key in params.keys():
                n = params[key]
                if not n.has_key('destination'): continue

                if not n.has_key('condition') or not n.has_key('expr'):
                    c = CombinedRule('and')
                else:
                    c = CombinedRule(n['condition'][0])
                    for single_expr in n['expr']:
                        c.addRule(FieldComparisonRule(single_expr.value))

                destination_instances = []
                for single_destination_name in n['destination']:
                    if destinations.has_key(single_destination_name.value):
                        destination_instances.\
                            append(destinations[single_destination_name.value])

                filters.append(Filter(c, destination_instances))

            # Once configured all new filters, take them in use
            self.filters = filters

        def finalize(result):
            # Another reconfiguration round, if the configuration has
            # changed meanwhile.
            if self.pending_reconfiguration:
                reactor.callLater(0, self.reconfigure_filters)
                log.info("Reconfigured, but doing it again: %d rule(s) configured.",
                         len(self.filters))
            else:
                self.active_reconfiguration = False
                log.info("Reconfigured: %d rule(s) configured.",
                         len(self.filters))

        def error(result):
            log.error("Can't refresh the configuration data: ")
            log.error(result)
            finalize(None)

        return p.addCallback(self.trigger_reconfiguration).\
            addCallback(load, p).\
            addCallback(parse_plugins, p).\
            addCallback(init_plugins).\
            addCallback(parse_rules, p).\
            addCallbacks(finalize, error)

    def check_events(self):
        d = Deferred()
        d.callback(None)

        max_id = self.uel.get_max_logid()

        if self.prev_id < max_id:
            dl = []
            for id in xrange(self.prev_id + 1, max_id + 1):
                d.addCallback(self.fetch_event, id)

            self.prev_id = max_id

        def prepare_next(result):
            reactor.callLater(self.EVENT_POLL_INTERVAL, self.check_events)

        return d.addCallback(prepare_next)

    def fetch_event(self, ignore, id):
        d = Deferred()
        process_ = lambda logid, ts, app, level, msg, src_names, dst_names:\
            self.process_event(logid, ts, app, level, msg, 
                               src_names, dst_names, d)

        self.uel.get_log_entry(id, process_)
        return d

    def process_event(self, logid, ts, app, level, msg, src_names,dst_names,
                      defer):
        """
        Feed the event through the filters, for parallel
        processing.
        """
        entry = make_entry(logid, ts, app, level, msg, src_names, dst_names)
        l = []
        for f in self.filters:
            try:
                r = f(entry)
                if isinstance(r, Deferred):
                    l.append(r)
            except Exception, e:
                self.report([(False, e)])

        dl = DeferredList(l, fireOnOneCallback=False,
                          fireOnOneErrback=False,
                          consumeErrors=True)
        dl.addCallback(self.report) # DeferredList never calls an errback
        dl.addCallbacks(defer.callback, defer.errback)

        #process_ = lambda logid, ts, app, level, msg, src_names, dst_names:\
        #    process(logid, ts, app, level, msg, src_names, dst_names, d)
        #
        #self.uel.get_log_entry(id, process_)
        #return d

    def report(self, results):
        for result in results:
            if not result[0]:
                # Unfortunatively, we can't print out the exact
                # Failure (and included stack trace) due to a bug
                # in Twisted mail library.  It'll result in an
                # exception within the library:
                #
                # ...
                #     self.printTraceback(file, elideFrameworkCode,
                #                         detail='brief')
                #   File "/usr/lib/python2.5/site-packages/twisted/python/
                #         failure.py", line 337, in printTraceback
                #     w("%s: %s: %s\n" % (hasFrames, self.type, self.value))
                #   File "/usr/lib/python2.5/site-packages/twisted/mail/
                #         smtp.py", line 165, in __str__
                #     return '\n'.join(res)
                # exceptions.TypeError: sequence item 2: expected string,
                #                       instance found
                #
                log.error("Sending an event to a filter failed: " +
                          str(result))
            else:
                log.debug("Successfully sent an event to a filter: " +
                          str(result))

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return Notifier(ctxt)

    return Factory()
