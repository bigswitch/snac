#include "pydirmanager.hh"
#include "swigpyrun.h"
#include "pyrt/pycontext.hh"

namespace vigil {
namespace applications {

PyDirectoryManager::PyDirectoryManager(PyObject *ctxt)
    : dm(NULL)
{
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void
PyDirectoryManager::configure(PyObject* configuration)
{
    c->resolve(dm);
}

void
PyDirectoryManager::install()
{}


bool
PyDirectoryManager::set_py_dm(PyObject *pydm)
{
    return dm->set_py_dm(pydm);
}

#define SET_CREATE_IMPL(fn_name)              \
bool                                          \
PyDirectoryManager::fn_name(PyObject *pyfn)   \
{                                             \
    return dm->fn_name(pyfn);                 \
} 

SET_CREATE_IMPL(set_create_dp)
SET_CREATE_IMPL(set_create_eth)
SET_CREATE_IMPL(set_create_ip)
SET_CREATE_IMPL(set_create_cidr)
SET_CREATE_IMPL(set_create_cred)


}
}

