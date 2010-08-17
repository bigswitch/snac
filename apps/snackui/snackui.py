"""Dummy component to bring up SNACK UI through dependencies."""

from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

class snackui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def install(self):
        pass

    def getInterface(self):
        return str(snackui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return snackui(ctxt)

    return Factory()

