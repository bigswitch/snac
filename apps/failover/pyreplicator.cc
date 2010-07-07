/* Copyright 2008 (C) Nicira, Inc. */
#include "pyreplicator.hh"

#include <boost/bind.hpp>

#include "pyrt/pycontext.hh"
#include "pyrt/pyglue.hh"
#include "pyrt/pyrt.hh"
#include "threads/cooperative.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::replicator;

static Vlog_module lg("pyreplicator");

typedef boost::intrusive_ptr<PyObject> PyObject_ptr;

PyStorage_replicator::PyStorage_replicator(PyObject* ctxt)
    : replicator(0)
{
    PySwigObject* swigo = SWIG_Python_GetSwigThis(ctxt);
    if (!swigo || !swigo->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)swigo->ptr)->c;

    c->resolve(replicator);
}

static void take_snapshot(Storage_replicator* replicator, const string& dest,
                          bool unique, const PyObject_ptr& cb) {
    const string path = replicator->snapshot(dest, unique);

    Co_critical_section critical;

    PyObject* args = PyTuple_New(1);
    PyTuple_SET_ITEM(args, 0, to_python(path));

    PyObject* ret = PyObject_CallObject(cb.get(), args);
    if (ret == 0) {
        const string exc = pretty_print_python_exception();
        lg.err("Python callback invocation failed:\n%s", exc.c_str());
    }

    Py_DECREF(args);
    Py_XDECREF(ret);
}

PyObject*
PyStorage_replicator::snapshot(const string& dest, bool unique, PyObject* cb) {
    try {
        if (!cb || !PyCallable_Check(cb)) {
            throw runtime_error("Invalid callback");
        }
        
        const PyObject_ptr cptr = PyObject_ptr(cb, true);

        // Since snapshotting may block, execute it within a timer to
        // avoid re-entering Python runtime from C++ during blocking.
        c->post(boost::bind(&take_snapshot, replicator, dest, unique, cptr));
        
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}
