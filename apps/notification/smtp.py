# Copyright 2008 (C) Nicira, Inc.

import StringIO

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.mail.smtp import SMTPSenderFactory

from nox.ext.apps.notification.notifier import Destination

class SMTPDestination(Destination):
    """
    A plugin to sends user log events to a SMTP smart relay.

    The plugin requires the following configuration parameters:
    - 'from': the from email address
    - 'to': a list of email addresses to send the notification to
    - 'smtp_host': the SMTP relay host name or IP
    - 'smtp_port': the SMTP relay port

    - 'template': the message template, '{msg}' gets subtituted with
       the event message.

    None of the parameters has any default values.
    """    
    #    'from_address': "nox@nicira.com",
    #    'to_address': ("alert@nicira.com"),
    #    'smtp_host' : "127.0.0.1",
    #    'smtp_port' : 25,
    #    'template' : "Subject: NOX network event\n{msg}"

    def __init__(self, config):
        self.from_address = config['FROM'][0]
        self.to_address = config['TO'][0]
        self.smtp_host = config['SMTP_HOST'][0]
        self.smtp_port = config['SMTP_PORT'][0]
        self.template = config['TEMPLATE'][0]

    def log(self, event):
        msg = self.template
        msg = msg.replace("{msg}", event['msg'])

        d = Deferred()
        factory = SMTPSenderFactory(self.from_address, self.to_address,
                                    StringIO(msg), d, retries=3, timeout=5)
        reactor.connectTCP(self.smtp_host, self.smtp_port, factory)
        return d

def get_plugin_factory():
    return ('SMTP', lambda config: SMTPDestination(config) )
