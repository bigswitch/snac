# Copyright 2008 (C) Nicira, Inc.
#
# This file is part of NOX.
#
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from nox.netapps.tests import unittest
from nox.netapps.storage import Storage
from nox.netapps.storage import TransactionalStorage, TransactionalConnection
from nox.netapps.configuration.properties import Properties
from nox.netapps.tests.pyunittests.properties_test import DeleteSection
from nox.ext.apps.notification.notifier import Notifier

import logging
log = logging.getLogger('notifier_test')

from nox.ext.apps.notification.notifier import Destination

class NotifierTestDestination(Destination):
    def __init__(self, config):
        self.from_address = config['FROM'][0]
        self.to_address = config['TO'][0]
        self.smtp_host = config['SMTP_HOST'][0]
        self.smtp_port = config['SMTP_PORT'][0]
        self.template = config['TEMPLATE'][0]

    def log(self, event):
        msg = self.template
        msg = msg.replace("{msg}", event['msg'])
        self.d.callback(None)
        
class NotifierTestCase(unittest.NoxTestCase):

    def getInterface(self):
        return str(NotifierTestCase)

    def setUp(self):
        self.storage = self.ctxt.resolve(str(TransactionalStorage))
        self.notifier = self.ctxt.resolve(str(Notifier))
        return DeleteSection(self.storage, 'NOTIFIER')()

    def tearDown(self):
        pass

    def refresh(self):
        def factory(config):
            self.plugin = NotifierTestDestination(config)            
            return self.plugin
        self.notifier.plugin_factories['TEST'] = factory

        new_config = [
            # Destination definition
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.NAME',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'EMAIL',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.TYPE',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'TEST',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.FROM',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'NOX@NICIRA.COM',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.TO',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'NOX@NICIRA.COM',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.SMTP_HOST',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'LOCALHOST',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.SMTP_PORT',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_INT,
                'VALUE_INT' : 25,
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'DESTINATION.1.TEMPLATE',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'Database configured template {msg}',
            },
            # Rule definition
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'RULE.1.CONDITION',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'AND',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'RULE.1.EXPR',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'app == FOO',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'RULE.1.EXPR',
                'VALUE_ORDER' : 1,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'level > 8',
            },
            {
                'SECTION' : 'NOTIFIER',
                'KEY' : 'RULE.1.DESTINATION',
                'VALUE_ORDER' : 0,
                'VALUE_TYPE' : Storage.COLUMN_TEXT,
                'VALUE_STR' : 'EMAIL',
            },
            ]

        from nox.netapps.tests.pyunittests.properties_test import DeleteSection
        deleter = DeleteSection(self.storage, 'NOTIFIER')
        d = deleter()
        self.connection = None

        def get_connection(result):
            return self.storage.get_connection()

        def begin(r):
            result, self.connection = r
            return self.connection.begin(TransactionalConnection.EXCLUSIVE)

        def insert_config(ignore, new_config):
            d = Deferred()
            d.callback(None)

            def put_row(result, row):
                return self.connection.put('PROPERTIES', row)

            for row in new_config:
                d.addCallback(put_row, row)

            return d

        def commit(ignore):
            return self.connection.commit()

        def rollback(failure):
            if self.connection and \
                    self.connection.get_transaction_mode() == \
                    TransactionalConnection.EXCLUSIVE:
                return self.connection.rollback().\
                    addCallback(lambda x: failure)
            else:
                return failure

        def wait(ignore):
            """
            Wait a moment to let the notifier to reconfigure itself
            before injecting any events into it.
            """
            d = Deferred()

            def timeout():
                d.callback(None)

            reactor.callLater(0.100, timeout)
            return d

        def inject(result):
            d = Deferred()
            self.plugin.d = Deferred()
            self.notifier.process_event(1, 12345, 'FOO', 9, 'foo bar', 
                                        {}, {}, d)
            
            def error():
                self.plugin.d.errback(Failure('Event injection did not work'))

            def abort(result):
                reactor.cancelCallLater(self.timer)

            def wait_for_processing(result):
                self.timer = reactor.callLater(10, error)
                return self.plugin.d.addCallback(abort)

            return d.addCallback(wait_for_processing)

        return d.addCallback(get_connection).\
            addCallback(begin).\
            addCallback(insert_config, new_config).\
            addCallback(commit).\
            addCallback(wait).\
            addCallback(inject).\
            addErrback(rollback)

def suite(ctxt):
    pyunit = __import__('unittest')

    suite = pyunit.TestSuite()
    suite.addTest(NotifierTestCase("refresh", ctxt))
    return suite
