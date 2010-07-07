/* Proxy class to expose http_redirector.hh to Python.
 * This file is only to be included from the SWIG interface file
 * (http_redirector_proxy.i)
 */

#ifndef HTTP_REDIRECTOR_PROXY_HH__
#define HTTP_REDIRECTOR_PROXY_HH__

#include <Python.h>

#include "http_redirector.hh"
#include "pyrt/pyglue.hh"

using namespace std;

namespace vigil {
namespace applications {

class http_redirector_proxy{
public:
    http_redirector_proxy(PyObject* ctxt);

    void configure(PyObject*);
    void install(PyObject*);

    Redirected_flow get_redirected_flow(uint64_t flowid);

protected:   
    Http_redirector* hr;
    container::Component* c;
}; // class http_redirector_proxy

} // namespcae applications
} // namespace vigil

#endif //  HTTP_REDIRECTOR_PROXY_HH__
