%module "nox.ext.apps.http_redirector"

%{
#include "flow.hh"
#include "http_redirector_proxy.hh"
#include "http_redirector.hh"
#include "redirected_flow_cache.hh"
#include "pyrt/pycontext.hh"
using namespace vigil;
using namespace vigil::applications;
%}

%import "netinet/netinet.i"

%include "common-defs.i"
%include "http_redirector_proxy.hh"
%include "std_string.i"

    struct Redirected_flow {
        const Flow flow;
        datapathid dpid;
        char payload_head[PAYLOAD_HEAD_SZ];
        bool is_initialized;
    }; 

%pythoncode
%{
  from nox.lib.core import Component

  class pyhttp_redirector(Component):
      """
      Python interface for the Bindings_Map class in C++ 
      """  
      def __init__(self, ctxt):
          self.hr = http_redirector_proxy(ctxt)

      def configure(self, configuration):
          self.hr.configure(configuration)

      def install(self):
          pass

      def getInterface(self):
          return str(pyhttp_redirector)

      def get_redirected_flow(self, cookie):
          return self.hr.get_redirected_flow(cookie)


  def getFactory():
        class Factory:
            def instance(self, context):
                return pyhttp_redirector(context)

        return Factory()
%}
