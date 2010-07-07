#ifndef CONTROLLER_PYNDBGLUE_HH
#define CONTROLLER_PYNDBGLUE_HH 1

#include <Python.h>

#include <iostream>
#include <list>

#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>

#include "ndb.hh"
#include "pyrt/pyglue.hh"

/**
 * Glue for Python and C++ network database communication.  This file
 * is to be included only from the SWIG interface file (.i).
 */
namespace vigil {
namespace applications {

struct InvalidationCallback {
    InvalidationCallback(PyObject* p) 
        : py_callback(p) {
        Py_INCREF(py_callback);
    }
    
    void callback() const {
        if (PyCallable_Check(py_callback)) {
            PyObject_CallObject(py_callback, NULL);
            // TODO: error checking
        }
    }
    
    ~InvalidationCallback() {
        Py_XDECREF(py_callback);
    }
    
    PyObject* py_callback;
};

/**
 * When it comes to resolving a component dependency, the stub relies
 * on the PyComponent instance it gets a pointer to within PyContext.
 */
class PyNDB {
public:
    PyNDB(PyObject* ctxt);

    void configure(PyObject*);

    void install(PyObject*);

    PyObject* create_table(PyObject*);

    PyObject* drop_table(PyObject*);

    PyObject* execute(PyObject*);

private:
    void execute_2(PyObject*,
                   PyObject*,
                   PyObject*,
                   const boost::shared_ptr<std::list<boost::shared_ptr<GetOp> > >&,
                   NDB::OpStatus);

    void py_return(PyObject*, 
                   PyObject*,
                   NDB::OpStatus);    

    NDB* ndb;
    container::Component* c;
};

} // namespace applications

/**
 * Conversion functions from C++ types to Python types. Operations are
 * converted into Python dictionaries.
 */

template <>
inline
PyObject*
to_python<Op::Row_ptr>(const Op::Row_ptr& kv)
{
    PyObject *dict = PyDict_New();
    if (!dict) {
        return 0;
    }
    for (std::list<boost::shared_ptr<Op::KeyValue> >::const_iterator i = 
             kv->begin();
         i != kv->end(); 
         ++i) {

        boost::shared_ptr<Op::KeyValue> k = *i;
        
        PyObject *key = to_python(k->key);
        if (!key) {
            Py_DECREF(dict);
            return 0;
        }

        PyObject *value;
        switch (k->type) {
        case Op::NONE:
            value = Py_None; Py_INCREF(value);
            break;

        case Op::INT:
            value = to_python(k->int_val);
            break;

        case Op::DOUBLE:
            value = to_python(k->double_val);
            break;

        case Op::TEXT:
            value = to_python(k->text_val);
            break;

        case Op::BLOB:
            {
                value = PyBuffer_New(k->blob_len);
                if (value) {
                    Py_ssize_t len;
                    int segments = 
                        PyBuffer_Type.tp_as_buffer->bf_getsegcount(value, &len);
                    uint8_t *blob_val = k->blob_val;
                    for (int segment = 0; segment < segments; ++segment) {
                        void *s;
                        int l = PyBuffer_Type.tp_as_buffer->
                            bf_getwritebuffer(value, segment, &s);
                        memcpy(s, blob_val, l);
                        blob_val += l;
                    }
                }
            }

            break;
        default:
            std::cerr << "vigil::to_python<std::list<Op::KeyValue>>() " 
                "Type error! type not serializable"
                      << std::endl;
            value = 0;
            break;
        }

        if (!value) {
            Py_DECREF(key);
            Py_DECREF(dict);
            return 0;
        }
        
        PyDict_SetItem(dict, key, value);
        Py_DECREF(key);
        Py_DECREF(value);
    }

    return dict;
}

template <>
inline
PyObject*
to_python<Op::Results_ptr>(const Op::Results_ptr& p) {
    using namespace std;

    PyObject* rows;
    if (p.get()) {
        rows = PyList_New(0);
        for (list<Op::Row_ptr>::iterator i = p->begin(); 
             i != p->end(); 
             ++i) {
            PyObject* row = to_python(*i);
            if (PyList_Append(rows, row)) {
                Py_DECREF(row);
                Py_DECREF(rows);
                throw runtime_error("to_python: unable to append to a list.");
            }
            Py_DECREF(row);
        }
    } else {
        rows = Py_None; Py_INCREF(rows);
    }

    return rows;
}

/**
 * Conversion functions from Python to C++ types.
 */
template <>
inline
Op::Row_ptr
from_python<Op::Row_ptr>(PyObject *columnsvalues) {
    using namespace std;
    boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > q;        
    
    if (!PyDict_Check(columnsvalues)) {
        return q;
    }

    q.reset(new list<boost::shared_ptr<Op::KeyValue> >);
    PyObject* columnsvalues_keys = PyDict_Keys(columnsvalues);
    
    for (int j = 0; j < PyList_Size(columnsvalues_keys); j++) {
        PyObject *k = PyList_GetItem(columnsvalues_keys, j);
        PyObject *v = PyDict_GetItem(columnsvalues, k);
        
        if (PyString_Check(v)) {
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k)),
                                    string(PyString_AsString(v))));
            q->push_back(kv);
            
        } else if (PyInt_Check(v)) {
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k)),
                                    (int64_t)PyInt_AsLong(v)));
            q->push_back(kv);

        } else if (PyLong_Check(v)) {
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k)),
                                    (int64_t)PyLong_AsLongLong(v)));
            q->push_back(kv);

        } else if (PyFloat_Check(v)) {
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k)),
                                    PyFloat_AsDouble(v)));
            q->push_back(kv);

        } else if (PyBuffer_Check(v)) {
            // XXX: Unnecessary copying below.
            Py_ssize_t len;
            int segs = 
                PyBuffer_Type.tp_as_buffer->bf_getsegcount(v, &len);

            uint8_t blob[len];
            uint8_t* dst = blob;
            for (int n = 0; n < segs; ++n) {
                void *s;
                int l = PyBuffer_Type.tp_as_buffer->
                    bf_getreadbuffer(v, n, &s);
                memcpy(dst, s, l);
                dst += l;
            }
            
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k)),
                                    len, blob));
            q->push_back(kv);
 
        } else if (v == Py_None) {
            boost::shared_ptr<Op::KeyValue> 
                kv(new Op::KeyValue(string(PyString_AsString(k))));
            q->push_back(kv);

        } else {
            // Unknown type, ignore.
        }
    }
    Py_DECREF(columnsvalues_keys);

    return q;
}

template <>
inline
Op::Results_ptr
from_python<Op::Results_ptr>(PyObject *py_results) {
    using namespace std;

    boost::shared_ptr<list<Op::Row_ptr> > 
        r(new list<Op::Row_ptr>);

    if (!PyList_Check(py_results)) {
        return r;
    }

    for (int i = 0; i < PyList_Size(py_results); ++i) {
        // Python side always returns a list (of dictionaries).
        PyObject *py_row = PyList_GetItem(py_results, i);

        boost::shared_ptr<std::list<boost::shared_ptr<Op::KeyValue> > > row =
            from_python<boost::shared_ptr<std::list<boost::shared_ptr<Op::KeyValue> > > >(py_row);

        r->push_back(row);
    }

    return r;
}


template <>
inline
boost::shared_ptr<std::list<boost::shared_ptr<GetOp> > >
from_python<boost::shared_ptr<std::list<boost::shared_ptr<GetOp> > > >(PyObject* py_gets) {
    using namespace std;

    boost::shared_ptr<list<boost::shared_ptr<GetOp> > > 
        gets(new list<boost::shared_ptr<GetOp> >);

    for (int i = 0; i < PyList_Size(py_gets); ++i) {
        PyObject* py_get = PyList_GetItem(py_gets, i);

        PyObject* py_table_key = to_python(string("table"));
        PyObject* py_callback_key = to_python(string("callback"));
        PyObject* py_columnsvalues_key = to_python(string("columnsvalues"));
        PyObject* py_results_key = to_python(string("results"));

        PyObject* py_table = PyDict_GetItem(py_get, py_table_key);
        PyObject* py_callback = PyDict_GetItem(py_get, py_callback_key);
        PyObject* py_columnsvalues = PyDict_GetItem(py_get, py_columnsvalues_key);
        PyObject* py_results = PyDict_GetItem(py_get, py_results_key);

        Py_DECREF(py_table_key);
        Py_DECREF(py_callback_key);
        Py_DECREF(py_columnsvalues_key);
        Py_DECREF(py_results_key);

        if (!py_table || !py_callback || !py_columnsvalues || !py_results) {
            gets.reset();
            return gets;
        }

        boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > 
            q = from_python<boost::shared_ptr<std::list<boost::shared_ptr<Op::KeyValue> > > >(py_columnsvalues);
        boost::shared_ptr<applications::InvalidationCallback> 
            ic(new applications::InvalidationCallback(py_callback));

        boost::shared_ptr<GetOp> 
            get(new GetOp(string(PyString_AsString(py_table)),
                          q,
                          boost::bind(&applications::InvalidationCallback::callback, 
                                      ic)));
        if (py_results != Py_None) {
            Op::Results_ptr results = from_python<Op::Results_ptr>(py_results);
            get->set_results(results);
        }

        gets->push_back(get);
    }

    return gets;
}

template <>
inline
boost::shared_ptr<std::list<boost::shared_ptr<PutOp> > >
from_python<boost::shared_ptr<std::list<boost::shared_ptr<PutOp> > > >(PyObject* py_puts) {
    using namespace std;

    boost::shared_ptr<list<boost::shared_ptr<PutOp> > > 
        puts(new list<boost::shared_ptr<PutOp> >);

    for (int i = 0; i < PyList_Size(py_puts); ++i) {
        PyObject* put = PyList_GetItem(py_puts, i);

        PyObject* py_table_key = to_python(string("table"));
        PyObject* py_columnsvalues_key = to_python(string("columnsvalues"));
        PyObject* py_replace_columnsvalues_key = to_python(string("replace_columnsvalues"));

        PyObject* py_table = PyDict_GetItem(put, py_table_key);
        PyObject* py_columnsvalues = PyDict_GetItem(put, py_columnsvalues_key);
        PyObject* py_replace_columnsvalues = PyDict_GetItem(put, py_replace_columnsvalues_key);

        Py_DECREF(py_table_key);
        Py_DECREF(py_columnsvalues_key);
        Py_DECREF(py_replace_columnsvalues_key);

        if (!py_table || !py_columnsvalues || !py_replace_columnsvalues_key) {
            puts.reset();
            return puts;
        }

        boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > 
            columnsvalues = from_python<boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > >(py_columnsvalues);
        boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > 
            replace_columnsvalues = 
            from_python<boost::shared_ptr<list<boost::shared_ptr<Op::KeyValue> > > >(py_replace_columnsvalues);
        puts->push_back(boost::shared_ptr<
                        PutOp>(new PutOp(string(PyString_AsString(py_table)),
                                         columnsvalues, 
                                         replace_columnsvalues)));
    }

    return puts;
}

template <>
inline
std::list<std::pair<std::string, Op::ValueType> >
from_python<std::list<std::pair<std::string, Op::ValueType> > >(PyObject* py_columns) {
    using namespace std;

    list<pair<string, Op::ValueType> > l;

    PyObject* py_column_names = PyDict_Keys(py_columns);
    
    for (int i = 0; i < PyList_Size(py_column_names); i++) {
        PyObject *py_column_name = PyList_GetItem(py_column_names, i);
        PyObject *py_column_type = PyDict_GetItem(py_columns, py_column_name);
        
        Op::ValueType type;
        if (PyInt_Check(py_column_type) || PyLong_Check(py_column_type)) {
            type = Op::INT;
        } else if (PyFloat_Check(py_column_type)) {
            type = Op::DOUBLE;
        } else if (PyString_Check(py_column_type) || PyUnicode_Check(py_column_type)) {
            type = Op::TEXT;
        } else if (PyBuffer_Check(py_column_type)) {
            type = Op::BLOB;
        } else {
            Py_DECREF(py_column_names);

            // An empty list is a sign of conversion error.
            l.clear();
            return l;
        }

        l.push_back(make_pair(string(PyString_AsString(py_column_name)), type));
    }

    Py_DECREF(py_column_names);
    return l;
}

template <>
inline
std::list<std::list<std::string> >
from_python<std::list<std::list<std::string> > >(PyObject* py_indices) {
    using namespace std;

    list<list<string> > l;

    for (int i = 0; i < PyList_Size(py_indices); ++i) {
        PyObject* py_index = PyList_GetItem(py_indices, i);
        list<string> index;

        for (int j = 0; j < PyTuple_Size(py_index); ++j) {
            PyObject* py_column = PyTuple_GetItem(py_index, j);
            index.push_back(string(PyString_AsString(py_column)));
        }
        
        l.push_back(index);
    }

    return l;
}

} // namespace vigil

#endif /* controller/pyndbglue.hh */
