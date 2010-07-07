#ifndef RESTRACKER_PROXY_HH
#define RESTRACKER_PROXY_HH

#include <Python.h>

#include "restracker.hh"
#include "pyrt/pyglue.hh"

using namespace std;

namespace vigil {
namespace applications {

class restracker_proxy{
public:
    restracker_proxy(PyObject* ctxt);

    void configure(PyObject*);
    void install(PyObject*);

    PyObject* get_host_counts();

protected:   
    restracker* rt;
    container::Component* c;
}; // class restracker_proxy

} // namespcae applications
} // namespace vigil

#endif //  RESTRACKER_PROXY_HH
