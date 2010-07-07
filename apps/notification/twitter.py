# Copyright 2008 (C) Nicira, Inc.

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList

from nox.ext.apps.notification.notifier import Destination

class TwitterDestination(Destination):
    """
    Sends user log events to a Twitter stream, whatever it is.
    """

    def __init__(self, filter):
        Destination.__init__(self, filter)

    def log(self, event):
        pass

#def get_plugin_factory():
#    return ('Twitter', lambda config: TwitterDestination(config) )
