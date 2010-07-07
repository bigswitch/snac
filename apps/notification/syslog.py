# Copyright 2008 (C) Nicira, Inc.

import logging
import os
import signal
import syslog

from nox.ext.apps.notification.notifier import Destination

log = logging.getLogger("notifier-syslog")

SYSLOG_CONF = '/etc/syslog.conf'
SYSLOG_PID = '/var/run/syslogd.pid'

class SyslogDestination(Destination):
    """
    A plugin to sends user log events to syslog.

    The plugin requires the following configuration parameters:
    - 'facility': the syslog facility to use.  Possible values: KERN, USER,
       MAIL, DAEMON, AUTH, LPR, NEWS, UUCP, CRON, LOCAL0 - LOCAL7.
    - 'priority': the syslog priority to use.  Possible values: EMERG, ALERT,
       CRIT, ERR, WARNING, NOTICE, INFO, DEBUG.
    - 'host': the remote host
    - 'template': the message template, '{msg}' gets subtituted with
       the event message.

    None of the parameters has any default values.
    """

    facilities = {
        "KERN" : syslog.LOG_KERN,
        "USER" : syslog.LOG_USER,
        "MAIL" : syslog.LOG_MAIL,
        "DAEMON" : syslog.LOG_DAEMON,
        "AUTH": syslog.LOG_AUTH,
        "LPR": syslog.LOG_LPR,
        "NEWS": syslog.LOG_NEWS,
        "UUCP": syslog.LOG_UUCP,
        "CRON": syslog.LOG_CRON,
        "LOCAL0": syslog.LOG_LOCAL0,
        "LOCAL1": syslog.LOG_LOCAL1,
        "LOCAL2": syslog.LOG_LOCAL2,
        "LOCAL3": syslog.LOG_LOCAL3,
        "LOCAL4": syslog.LOG_LOCAL4,
        "LOCAL5": syslog.LOG_LOCAL5,
        "LOCAL6": syslog.LOG_LOCAL6,
        "LOCAL7": syslog.LOG_LOCAL7
    }

    priorities = {
        "EMERG": syslog.LOG_EMERG,
        "ALERT": syslog.LOG_ALERT,
        "CRIT": syslog.LOG_CRIT,
        "ERR": syslog.LOG_ERR,
        "WARNING": syslog.LOG_WARNING,
        "NOTICE": syslog.LOG_NOTICE,
        "INFO": syslog.LOG_INFO,
        "DEBUG": syslog.LOG_DEBUG
    }

    def __init__(self, config):
        f = config['facility'][0]
        if self.facilities.has_key(f):
            self.facility = self.facilities[f]
            self.facility_name = f.lower()
            
        else:
            log.debug('Invalid facility ("%s"), defaulting to DAEMON.' % f)
            self.facility = self.facilities['DAEMON']
            self.facility_name = 'daemon'

        p = config['priority'][0]
        if self.priorities.has_key(p):
            self.priority = self.priorities[p]
        else:
            log.debug('Invalid priority ("%s"), defaulting to DAEMON.' % p)
            self.priority = self.priorities['INFO']

        if config.has_key('host'):
            self.remote_host = config['host'][0]
        else:
            self.remote_host = ''
        if config.has_key('template'):
            self.template = config['template'][0]
        else:
            self.template = '{msg}'

    def init(self):
        conf = open(SYSLOG_CONF, 'r')
        state = 'header'

        header = ''
        config = ''
        footer = ''

        CONFIG_HEADER = "### Policy Controller generated configuration begins here. Please don't edit! #\n"
        CONFIG_FOOTER = "### Policy Controller generated configuration ends here. ######################\n"

        # Use the magic marker to find the emitted part, if any
        for line in conf:
            if state == 'header':
                if line.find('### Policy Controller') == 0:
                    state = 'config'
                    continue

                header += line
                continue

            if state == 'config':
                if line.find('### Policy Controller') == 0:
                    state = 'footer'
                    continue
                continue

            if state == 'footer':
                footer += line
                continue

        conf.close()

        # Emit the configuration file
        f = open(SYSLOG_CONF, 'w')
        f.write(header)

        if self.remote_host != '':
            f.write(CONFIG_HEADER)
            config = "kern.*;%s.* @%s\n" % (self.facility_name, self.remote_host)
            f.write(config)
            f.write(CONFIG_FOOTER)

        f.write(footer)
        f.close()

        # HUP the syslog daemon to reload the configuration
        f = open(SYSLOG_PID)
        pid = int(f.readline())
        os.kill(pid, signal.SIGHUP)

        return self.remote_host != ''

    def log(self, event):
        msg = self.template
        msg = msg.replace("{msg}", event['msg'])

        syslog.syslog(self.priority | self.facility, msg.encode('utf-8'))

def get_plugin_factory():
    return ('Syslog', lambda config: SyslogDestination(config) )
