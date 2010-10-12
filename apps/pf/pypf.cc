#include "pypf.hh"

#include <stdexcept>

#include "pyrt/pycontext.hh"

using namespace std;
using namespace vigil::applications;

PyPF::PyPF(PyObject* ctxt) 
    : p(0), c(0) {
    
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void
PyPF::configure(PyObject* configuration) {
    c->resolve(p);    
}

void 
PyPF::install() {
    
}

bool
PyPF::get_fingerprints(ethernetaddr& eth, ipaddr& ipa, pf_results& res)
{
    return p->get_fingerprints(eth, ipa, res);
}
    
PyObject * 
PyPF::get_all_fingerprints()
{
    return to_python_list(p->get_all_fingerprints());
}
