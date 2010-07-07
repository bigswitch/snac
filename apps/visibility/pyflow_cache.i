%module "nox.ext.apps.visibility"

%{
#include "flow.hh"
#include "flow_cache_proxy.hh"
#include "flow_cache.hh"
#include "pyrt/pycontext.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%import "netinet/netinet.i"
%include "flow_cache_proxy.hh"

%include "common-defs.i"
%include "std_string.i"

%pythoncode
%{
  from nox.lib.core import Component

  class pyflow_cache(Component):
      """
      Python interface for the Flow_cache class in C++ 
      """  
      def __init__(self, ctxt):
          self.fc = flow_cache_proxy(ctxt)

      def configure(self, configuration):
          self.fc.configure(configuration)

      def install(self):
          pass

      def getInterface(self):
          return str(pyflow_cache)

      def get_all_flows(self, max_count=0):
          return self.fc.get_all_flows(max_count)

      def get_allowed_flows(self, max_count=0):
          return self.fc.get_allowed_flows(max_count)

      def get_denied_flows(self, max_count=0):
          return self.fc.get_denied_flows(max_count)

      def get_host_flows(self, hostname):
          return self.fc.get_host_flows(hostname)

      def get_policy_flows(self, policy_id, rule_id):
          return self.fc.get_policy_flows(policy_id, rule_id)

      def get_cur_policy_id(self):
          return self.fc.get_cur_policy_id()


  def getFactory():
        class Factory():
            def instance(self, context):
                return pyflow_cache(context)

        return Factory()
%}
