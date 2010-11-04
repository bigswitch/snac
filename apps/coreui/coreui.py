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
import base64
import os
import logging
import mimetypes

from OpenSSL import crypto, SSL

from twisted.web import static, server, resource
from twisted.internet import defer, reactor, ssl
from twisted.internet.ssl import ContextFactory
from twisted.web.util import redirectTo

from nox.ext.apps.configuration.properties import Properties
from nox.coreapps.pyrt.pycomponent import *
from nox.ext.apps.storage.transactional_storage import TransactionalStorage
from nox.lib.core import *

lg = logging.getLogger('coreui')

class coreui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def getInterface(self):
        return str(coreui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return coreui(ctxt)

    return Factory()

