/*
 */

#include "http_redirector_proxy.hh"
#include "pyrt/pycontext.hh"
#include "swigpyrun.h"

using namespace std;
using namespace vigil;
using namespace vigil::applications;

namespace vigil {
namespace applications {

http_redirector_proxy::http_redirector_proxy(PyObject* ctxt)
        : hr(0)
{
    PySwigObject* swigo = SWIG_Python_GetSwigThis(ctxt);
    if (!swigo || !swigo->ptr) {
        throw runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)swigo->ptr)->c;
}


void 
http_redirector_proxy::configure(PyObject* configuration) {
    c->resolve(hr);
}

void 
http_redirector_proxy::install(PyObject*) {
    //NOP
}

Redirected_flow 
http_redirector_proxy::get_redirected_flow(uint64_t flowid) {
    Redirected_flow *rf = hr->get_flow_cache().get_redirected_flow(flowid);
    if (rf == NULL) {
        return Redirected_flow();
    }
    return Redirected_flow(*rf);
}

} // namespcae applications
} // namespace vigil

