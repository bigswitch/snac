#ifndef CONTROLLER_PYPF_HH
#define CONTROLLER_PYPF_HH 1

#include <Python.h>

#include "buffer.hh"
#include "pf.hh"

#include "netinet++/ethernetaddr.hh"
#include "netinet++/ipaddr.hh"

namespace vigil {
namespace applications {

class PyPF {
public:
    PyPF(PyObject* ctxt);

    void configure(PyObject*);

    void install();

    bool get_fingerprints(ethernetaddr& eth, ipaddr& ipa, pf_results&);
    
    PyObject* get_all_fingerprints(); // for debugging 


private:
    pf *p;
    container::Component* c;
};

}
}

#endif
