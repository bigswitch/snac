#include "pyndb.hh"

#include <stdexcept>

#include "pyrt/pycontext.hh"
#include "pyrt/pyrt.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications;

/* Have a unique name since the file is included into SWIG generated
   wrapper file, which potentially includes other C++ source files as
   well. */

namespace {

Vlog_module pyndblog("pyndb");

}

namespace vigil {
namespace applications {

PyNDB::PyNDB(PyObject* ctxt)
    : ndb(0) {

    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw runtime_error("Unable to access Python context.");
    }
    
    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void
PyNDB::configure(PyObject* configuration) {
    c->resolve(ndb);    
    //ndb->get_commit_period();
}

void 
PyNDB::install(PyObject*) {

}

PyObject* PyNDB::create_table(PyObject* py_args) {
    if (!py_args || !PyTuple_Check(py_args) || 
        PyTuple_Size(py_args) != 4) {
        PyErr_SetString(PyExc_TypeError, 
                        "create_table() takes exactly 4 arguments.");
        return 0;
    }

    PyObject* py_table = PyTuple_GetItem(py_args, 0);
    PyObject* py_columns = PyTuple_GetItem(py_args, 1);
    PyObject* py_indices = PyTuple_GetItem(py_args, 2);
    PyObject* py_callback = PyTuple_GetItem(py_args, 3);

    if (!PyString_Check(py_table) || 
        !PyDict_Check(py_columns) || 
        !PyList_Check(py_indices) || 
        !PyCallable_Check(py_callback)) {
        PyErr_SetString(PyExc_TypeError, 
                        "create_table() got invalid arguments.");
        return 0;
    }

    // Ignore the non-optimal copying since the table creation is a
    // rare event.

    list<pair<string, Op::ValueType> > columns =
        from_python<list<pair<string, Op::ValueType> > >(py_columns);
    list<list<string> > indices =
        from_python<list<list<string> > >(py_indices);
    if (columns.empty() || (indices.empty() && PyList_Size(py_indices) != 0)) {
        PyErr_SetString(PyExc_TypeError, 
                        "create_table() got invalid table/index definition.");
        return 0;
    }

    // Pre-create the callback arguments so that callback can return,
    // even in case of out-of-memory conditions.
    PyObject* py_callback_args = PyTuple_New(1);
    PyObject* py_result = PyInt_FromLong(NDB::GENERAL_ERROR);
    if (!py_result || !py_callback_args) {
        Py_XDECREF(py_result);
        Py_XDECREF(py_callback_args);
        PyErr_SetString(PyExc_MemoryError, 
                        "create_table() unable to allocate callback arguments.");
        return 0;
    }

    // Steals the reference.
    PyTuple_SetItem(py_callback_args, 0, py_result);

    if (pyndblog.is_dbg_enabled()) {
        pyndblog.dbg("Executing a PyCreateTable.");
    }

    NDB::Callback f = boost::bind(&PyNDB::py_return, this, 
                                  py_callback, py_callback_args, _1);
    Py_INCREF(py_callback);
    ndb->create_table(string(PyString_AsString(py_table)), 
                      columns, indices, f);
    Py_RETURN_NONE;
}

PyObject* PyNDB::drop_table(PyObject* py_args) {
    if (!py_args || !PyTuple_Check(py_args) || 
        PyTuple_Size(py_args) != 2) {
        PyErr_SetString(PyExc_TypeError, "drop_table() takes exactly 2 arguments.");
        return 0;
    }

    PyObject* py_table = PyTuple_GetItem(py_args, 0);
    PyObject* py_callback = PyTuple_GetItem(py_args, 1);

    if (!PyString_Check(py_table) || 
        !PyCallable_Check(py_callback)) {
        PyErr_SetString(PyExc_TypeError, "drop_table() got invalid arguments.");
        return 0;
    }

    // Pre-create the callback arguments so that callback can return,
    // even in case of out-of-memory conditions.
    PyObject* py_callback_args = PyTuple_New(1);
    PyObject* py_result = PyInt_FromLong(NDB::GENERAL_ERROR);
    if (!py_result || !py_callback_args) {
        Py_XDECREF(py_result);
        Py_XDECREF(py_callback_args);
        PyErr_SetString(PyExc_MemoryError, 
                        "drop_table() unable to allocate callback arguments.");
        return 0;
    }

    // Steals the reference.
    PyTuple_SetItem(py_callback_args, 0, py_result);

    if (pyndblog.is_dbg_enabled()) {
        pyndblog.dbg("Executing a PyDropTable.");
    }

    NDB::Callback f = boost::bind(&PyNDB::py_return, this, 
                                  py_callback, py_callback_args, _1);
    Py_INCREF(py_callback);
    ndb->drop_table(string(PyString_AsString(py_table)), f);

    Py_RETURN_NONE;
}

PyObject* PyNDB::execute(PyObject* py_args) {
    if (!py_args || !PyTuple_Check(py_args) || 
        PyTuple_Size(py_args) != 4) {
        PyErr_SetString(PyExc_TypeError, "execute() takes exactly 4 arguments.");
        return 0;
    }

    PyObject* py_type = PyTuple_GetItem(py_args, 0);
    PyObject* py_ops = PyTuple_GetItem(py_args, 1);
    PyObject* py_deps = PyTuple_GetItem(py_args, 2);
    PyObject* py_callback = PyTuple_GetItem(py_args, 3);

    if (!PyString_Check(py_type) || 
        !PyList_Check(py_ops) || 
        !PyList_Check(py_deps) || 
        !PyCallable_Check(py_callback)) {
        PyErr_SetString(PyExc_TypeError, "execute() got invalid arguments.");
        return 0;
    }

    // Pre-create the callback arguments so that callback can return,
    // even in case of out-of-memory conditions.
    PyObject* py_callback_args = PyTuple_New(1);
    PyObject* py_result = PyInt_FromLong(NDB::GENERAL_ERROR);
    if (!py_result || !py_callback_args) {
        Py_XDECREF(py_result);
        Py_XDECREF(py_callback_args);
        PyErr_SetString(PyExc_MemoryError, 
                        "execute() unable to allocate callback arguments.");
        return 0;
    }

    // Steals the reference.
    PyTuple_SetItem(py_callback_args, 0, py_result);

    string type(PyString_AsString(py_type));

    if (type == "get") {
        if (pyndblog.is_dbg_enabled()) {
            pyndblog.dbg("Executing a PyGet.");
        }       
        boost::shared_ptr<list<boost::shared_ptr<GetOp> > > p1 = 
            from_python<boost::shared_ptr<list<boost::shared_ptr<GetOp> > > >(py_ops);
        NDB::Callback f = boost::bind(&PyNDB::execute_2, this, 
                                      py_callback,
                                      py_ops,
                                      py_callback_args,
                                      p1, 
                                      _1);
        Py_INCREF(py_callback);
        Py_INCREF(py_ops);
        ndb->execute(*p1, f);
        
    } else if (type == "put") {
        if (pyndblog.is_dbg_enabled()) {
            pyndblog.dbg("Executing a PyPut.");
        }
        boost::shared_ptr<list<boost::shared_ptr<PutOp> > > p1 = 
            from_python<boost::shared_ptr<list<boost::shared_ptr<PutOp> > > >(py_ops);
        boost::shared_ptr<list<boost::shared_ptr<GetOp> > > p2 = 
            from_python<boost::shared_ptr<list<boost::shared_ptr<GetOp> > > >(py_deps);
        NDB::Callback f = boost::bind(&PyNDB::py_return, this, 
                                      py_callback,
                                      py_callback_args,
                                      _1);
        Py_INCREF(py_callback);
        ndb->execute(*p1, *p2, f);

    } else {
        PyErr_SetString(PyExc_TypeError, "execute() takes only Put or Get.");
        return 0;
    }

    Py_RETURN_NONE;
}

void 
PyNDB::execute_2(PyObject* py_callback,                   
                        PyObject* py_gets,
                        PyObject* py_callback_args,
                        const boost::shared_ptr<list<boost::shared_ptr<GetOp> > >& g,
                        NDB::OpStatus result) {
    // Inject the results, if any, into the Python objects.
    if (result == NDB::OK) {
        if (pyndblog.is_dbg_enabled()) {
            pyndblog.dbg("Injecting the results into Python parameter objects.");
        }

        list<boost::shared_ptr<GetOp> >::iterator get = g->begin();     
        int j = 0;
        while (get != g->end()) {
            PyObject *op = PyList_GetItem(py_gets, j);

            PyObject *k = to_python(string("results"));
            PyObject *v = to_python((*get)->get_results());
            if (!k || !v) {
                Py_XDECREF(k);
                Py_XDECREF(v);
                result = NDB::GENERAL_ERROR;
                break;
            }
            PyDict_SetItem(op, k, v);
            Py_DECREF(k);
            Py_DECREF(v);
            
            ++get; ++j;
        }
    } else {
        if (pyndblog.is_dbg_enabled()) {
            pyndblog.dbg("Nothing to inject into Python parameter objects.");
        }
    }

    Py_DECREF(py_gets);
    PyObject* r = PyInt_FromLong(result);
    PyObject* t = PyTuple_New(1);
    if (!r || !t) {
        Py_XDECREF(r);
        Py_XDECREF(t);
        t = py_callback_args;
    } else {
        Py_DECREF(py_callback_args);
        PyTuple_SetItem(t, 0, r); // Steals the reference.
    }

    PyObject* v = PyObject_CallObject(py_callback, t);
    if (v == 0) {
        pyndblog.err("Python callback invocation failed:\n%s",
                     pretty_print_python_exception().c_str());
    }

    Py_DECREF(py_callback);
    Py_DECREF(t);
    Py_XDECREF(v);
}

void 
PyNDB::py_return(PyObject* py_callback, 
                        PyObject* py_callback_args, 
                        NDB::OpStatus result) {
    PyObject* r = PyInt_FromLong(result);
    PyObject* t = PyTuple_New(1);
    if (!r || !t) {
        Py_XDECREF(r);
        Py_XDECREF(t);
        t = py_callback_args;
    } else {
        Py_DECREF(py_callback_args);
        PyTuple_SetItem(t, 0, r); // Steals the reference.
    }

    PyObject* v = PyObject_CallObject(py_callback, t);
    if (v == 0) {
        pyndblog.err("Python callback invocation failed:\n%s",
                     pretty_print_python_exception().c_str());
    }

    Py_DECREF(py_callback);
    Py_DECREF(t);
    Py_XDECREF(v);
}

} // namespace applications
} // namespace vigil
