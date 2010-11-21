%module "nox.ext.apps.restracker"

%{
#include "flow.hh"
#include "restracker_proxy.hh"
#include "restracker.hh"

#include "pyrt/pycontext.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%import "netinet/netinet.i"

%include "common-defs.i"
%include "restracker_proxy.hh"
%include "std_string.i"

%pythoncode
%{
  from nox.lib.core import Component

  class pyrestracker(Component):
      """
      Python interface for restracker class in C++ 
      """  
      def __init__(self, ctxt):
          self.rt = restracker_proxy(ctxt)

      def configure(self, configuration):
          self.rt.configure(configuration)

      def install(self):
          pass

      def getInterface(self):
          return str(pyrestracker)

      def get_host_counts(self):
        return self.rt.get_host_counts()


  def getFactory():
        class Factory:
            def instance(self, context):
                return pyrestracker(context)

        return Factory()
%}
