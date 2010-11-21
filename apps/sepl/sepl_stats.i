/* Copyright 2008 (C) Nicira, Inc. */
%module "nox.ext.apps.sepl.pyseplstats"

%{
#include "pysepl_stats.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%include "common-defs.i"
%include "std_list.i"

%import "netinet/netinet.i"

%template(ethlist) std::list<ethernetaddr>;

%include "pysepl_stats.hh"

%pythoncode
%{
    from nox.lib.core import Component

    class PySeplStats(Component):
        def __init__(self, ctxt):
            self.stats = PySepl_stats(ctxt)

        def configure(self, configuration):
            self.stats.configure(configuration)

        def getInterface(self):
            return str(PySeplStats)

        def set_record_rule_senders(self, id, record):
            self.stats.set_record_rule_senders(id, record)

        def get_rule_stats(self, id):
            return self.stats.get_rule_stats(id)

        def clear_stats(self):
            self.stats.clear_stats()

        def remove_entry(self, id):
            self.stats.remove_entry(id)

        def increment_allows(self):
            self.stats.increment_allows()

        def get_allows(self):
            return self.stats.get_allows()

        def clear_allows(self):
            self.stats.clear_allows()

        def increment_denies(self):
            self.stats.increment_denies()

        def get_denies(self):
            return self.stats.get_denies()

        def clear_denies(self):
            self.stats.clear_denies()

    def getFactory():
        class Factory:
            def instance(self, context):
                return PySeplStats(context)

        return Factory()

%}
