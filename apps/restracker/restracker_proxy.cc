/*
 */

#include "restracker_proxy.hh"
#include "pyrt/pycontext.hh"

#include "netinet++/ethernetaddr.hh"

#include "swigpyrun.h"

using namespace std;
using namespace vigil;
using namespace vigil::applications;

namespace vigil {
namespace applications {

restracker_proxy::restracker_proxy(PyObject* ctxt)
        : rt(0)
{
    PySwigObject* swigo = SWIG_Python_GetSwigThis(ctxt);
    if (!swigo || !swigo->ptr) {
        throw runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)swigo->ptr)->c;
}


void 
restracker_proxy::configure(PyObject* configuration) {
    c->resolve(rt);
}

void 
restracker_proxy::install(PyObject*) {
    //NOP
}

PyObject* 
restracker_proxy::get_host_counts()
{
    PyObject* hostlist = PyList_New(0);

    for(restracker::HostMap::iterator outer= rt->hosts.begin();
            outer != rt->hosts.end(); ++outer){
        for(hash_map<uint64_t,int>::iterator inner = outer->second.begin();
            inner != outer->second.end(); ++inner){
            PyObject* item = Py_BuildValue("s i s i",
                    datapathid::from_host(outer->first & 0x00ffffffffffffffULL).string().c_str(),
                    (int)((outer->first >> 48) &  0xff),
                    ethernetaddr(inner->first).string().c_str(),
                    inner->second );
            if(!item){
                PyErr_Print();
                continue;
            }
            if (PyList_Append(hostlist, item) ){
                PyErr_Print();
                Py_DECREF(item);
            }
        }
    }

    return hostlist;
}

} // namespcae applications
} // namespace vigil

