/* Copyright 2008 (C) Nicira, Inc. */
%module "nox.ext.apps.sepl.pyseplenforcer"

%{
#include "pysepl_enforcer.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%include "common-defs.i"

%import "authenticator/flow_util.i"
%include "pysepl_enforcer.hh"

%pythoncode
%{
    from nox.lib.core import Component

    class PySeplEnforcer(Component):
        def __init__(self, ctxt):
            self.enforcer = PySepl_enforcer(ctxt)

        def configure(self, configuration):
            self.enforcer.configure(configuration)

        def getInterface(self):
            return str(PySeplEnforcer)

        def set_most_secure(self, most_secure):
            self.enforcer.set_most_secure(most_secure)

        def add_rule(self, pri, expr, action):
            return self.enforcer.add_rule(pri, expr, action)

        def build(self):
            self.enforcer.build()

        def change_rule_priority(self, id, priority):
            return self.enforcer.change_rule_priority(id, priority)

        def delete_rule(self, id):
            return self.enforcer.delete_rule(id)

        def reset(self):
            self.enforcer.reset()

    def getFactory():
        class Factory():
            def instance(self, context):
                return PySeplEnforcer(context)

        return Factory()

%}
