/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "pytransactional-storage.hh"

#include <boost/bind.hpp>

#include "pyrt/pycontext.hh"
#include "storage/pystorage-common.hh"
#include "threads/cooperative.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::storage;

static Vlog_module lg("pytransactional-storage");

PyTransactional_storage::PyTransactional_storage(PyObject* ctxt)
    : storage(0) {
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void
PyTransactional_storage::configure(PyObject*) {
    c->resolve(storage);
}

void
PyTransactional_storage::install(PyObject*) {
    /* Nothing here */
}

static void python_callback(PyObject* args, PyObject_ptr cb) {
    Co_critical_section c;
    PyObject* ret = PyObject_CallObject(cb.get(), args);
    if (ret == 0) {
        const string exc = pretty_print_python_exception();
        lg.err("Python callback invocation failed:\n%s", exc.c_str());
    }

    Py_DECREF(args);
    Py_XDECREF(ret);
}

static PyObject_ptr check_callback(PyObject* cb) {
    if (!cb || !PyCallable_Check(cb)) {
        throw runtime_error("Invalid callback");
    }

    return PyObject_ptr(cb, true);
}

static
PyObject*
get_connection_ctor()
{
    PyObject* pname = PyString_FromString("nox.apps.storage.pytransactional_storage");
    if (!pname) {
        throw runtime_error("unable to create a module string");
    }

    PyObject* pmod = PyImport_Import(pname);
    if (!pmod || !PyModule_Check(pmod)){
        Py_DECREF(pname);
        Py_XDECREF(pmod);
        throw runtime_error("unable to import nox.apps.storage module");
    }
    Py_DECREF(pname);

    PyObject* pfunc =
        PyObject_GetAttrString(pmod, (char*)"PyTransactional_connection");
    if (!pfunc || !PyCallable_Check(pfunc)) {
        Py_DECREF(pmod);
        Py_XDECREF(pfunc);
        throw runtime_error("unable to pull in a Transactional_connection "
                            "constructor");
    }

    Py_DECREF(pmod);

    return pfunc;
}

PyObject*
PyTransactional_storage::get_connection(PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_storage::Get_connection_callback f =
            boost::bind(&PyTransactional_storage::get_connection_callback, this,
                        _1, _2, cptr);
        
        storage->get_connection(f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

void
PyTransactional_storage::get_connection_callback(const Result& result,
                                                 const Async_transactional_connection_ptr& conn,
                                                 PyObject_ptr cb) {
    PyObject* t = PyTuple_New(2);

    try {
        Co_critical_section critical;

        // Intentionally leaked
        static PyObject* pfunc = get_connection_ctor();

        PyTuple_SET_ITEM(t, 0, to_python(result));

        if (result.is_success()) {
            // Call the constructor in Python
            PyObject* py_conn = PyObject_CallObject(pfunc, 0);
            if (!py_conn) {
                throw runtime_error("Python callback invocation failed:\n" +
                                    pretty_print_python_exception());
            }

            if (!SWIG_Python_GetSwigThis(py_conn) || SWIG_Python_GetSwigThis(py_conn)->ptr == 0) {
                Py_DECREF(py_conn);
                throw runtime_error("get_connection_callback unable "
                                    "to recover C++ object from Python "
                                    "transactional connection.");
            }

            ((PyTransactional_connection*)SWIG_Python_GetSwigThis(py_conn)->ptr)->conn = conn;

            PyTuple_SET_ITEM(t, 1, py_conn);
        } else {
            Py_INCREF(Py_None);
            PyTuple_SET_ITEM(t, 1, Py_None);
        }
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        t = PyTuple_New(2);
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 0,
                         to_python(Result(Result::UNKNOWN_ERROR, e.what())));
        PyTuple_SET_ITEM(t, 1, Py_None);
    }

    python_callback(t, cb);
}

static void callback(const Result& result, PyObject_ptr cb) {
    PyObject* py_result = 0;
    try {
        py_result = to_python(result);
    }
    catch (const runtime_error& e) {
        py_result = to_python(Result(Result::UNKNOWN_ERROR, e.what()));
    }

    PyObject* t = PyTuple_New(1);
    PyTuple_SET_ITEM(t, 0, py_result);

    python_callback(t, cb);
}

PyObject*
PyTransactional_connection::begin(PyObject* mode_, PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        int mode = from_python<int32_t>(mode_);
        Async_transactional_connection::Transaction_mode m;

        switch (mode) {
        case Async_transactional_connection::AUTO_COMMIT:
            m = Async_transactional_connection::AUTO_COMMIT;
            break;

        case Async_transactional_connection::DEFERRED:
            m = Async_transactional_connection::DEFERRED;
            break;

        case Async_transactional_connection::EXCLUSIVE:
            m = Async_transactional_connection::EXCLUSIVE;
            break;

        default:
            throw runtime_error("unsupported transaction mode");
        }

        Async_transactional_connection::Begin_callback f =
            boost::bind(&callback, _1, cptr);
        conn->begin(m, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::commit(PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_connection::Begin_callback f =
            boost::bind(&callback, _1, cptr);
        conn->commit(f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::rollback(PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_connection::Begin_callback f =
            boost::bind(&callback, _1, cptr);
        conn->rollback(f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::get_transaction_mode() {
    const int mode = conn->get_transaction_mode();
    return to_python(mode);
}

PyObject*
PyTransactional_connection::create_table(PyObject* table, PyObject* columns,
                                         PyObject* indices, PyObject* version,
                                         PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        const Table_name t = from_python<Table_name>(table);
        const Column_definition_map c =
            from_python<Column_definition_map>(columns);
        const Index_list i = from_python<Index_list>(indices);
        const int v = from_python<int32_t>(version);
        
        Async_transactional_connection::Create_table_callback f =
            boost::bind(&callback, _1, cptr);
        conn->create_table(t, c, i, v, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::get(PyObject* table, PyObject* query,
                                PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        const Table_name t = from_python<Table_name>(table);
        const Query q = from_python<Column_definition_map>(query);

        Async_transactional_connection::Get_callback f =
            boost::bind(&PyTransactional_connection::get_callback, this,
                        _1, _2, cptr);
        conn->get(t, q, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

static
PyObject*
get_cursor_ctor()
{
    PyObject* pname = PyString_FromString("nox.apps.storage.pytransactional_storage");
    if (!pname) {
        throw runtime_error("unable to create a module string");
    }

    PyObject* pmod = PyImport_Import(pname);
    if (!pmod || !PyModule_Check(pmod)){
        Py_DECREF(pname);
        Py_XDECREF(pmod);
        throw runtime_error("unable to import nox.apps.storage module");
    }
    Py_DECREF(pname);

    PyObject* pfunc =
        PyObject_GetAttrString(pmod, (char*)"PyTransactional_cursor");
    if (!pfunc || !PyCallable_Check(pfunc)) {
        Py_DECREF(pmod);
        Py_XDECREF(pfunc);
        throw runtime_error("unable to pull in a Transactional_cursor "
                            "constructor");
    }
    Py_DECREF(pmod);

    return pfunc;
}

void
PyTransactional_connection::get_callback(const Result& result, const
                                         Async_transactional_cursor_ptr& cursor,
                                         PyObject_ptr cb) {

    PyObject* t = PyTuple_New(2);

    try {
        Co_critical_section critical;

        PyObject* py_result = to_python(result);

        // Intentionally leaked
        static PyObject* pfunc = get_cursor_ctor();

        // Call the constructor in Python
        PyObject* py_cursor = PyObject_CallObject(pfunc, 0);
        if (!py_cursor) {
            Py_DECREF(py_result);
            throw runtime_error("Python callback invocation failed:\n" +
                                pretty_print_python_exception());
        }

        if (!SWIG_Python_GetSwigThis(py_cursor) || SWIG_Python_GetSwigThis(py_cursor)->ptr == 0) {
            Py_DECREF(py_result);
            Py_DECREF(py_cursor);
            throw runtime_error("get_cursor_callback unable "
                                "to recover C++ object from Python "
                                "transactional connection.");
        }

        ((PyTransactional_cursor*)SWIG_Python_GetSwigThis(py_cursor)->ptr)->cursor = cursor;

        PyTuple_SET_ITEM(t, 0, py_result);
        PyTuple_SET_ITEM(t, 1, py_cursor);
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        t = PyTuple_New(2);
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM(t, 0,
                         to_python(Result(Result::UNKNOWN_ERROR, e.what())));
        PyTuple_SET_ITEM(t, 1, Py_None);
    }

    python_callback(t, cb);
}

static void put_callback(const Result& result, const GUID& guid,
                         PyObject_ptr cb) {
    PyObject* t = PyTuple_New(2);

    try {
        PyTuple_SET_ITEM(t, 0, to_python(result));
        PyTuple_SET_ITEM(t, 1, to_python(guid));
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        t = PyTuple_New(2);
        PyTuple_SET_ITEM(t, 0,
                         to_python(Result(Result::UNKNOWN_ERROR, e.what())));
        PyTuple_SET_ITEM(t, 1, to_python(GUID()));
    }

    python_callback(t, cb);
}

PyObject*
PyTransactional_connection::put(PyObject* table, PyObject* row, PyObject* cb) {
    try {
        const Table_name t = from_python<Table_name>(table);
        const Row r = from_python<Row>(row);
        PyObject_ptr cptr = check_callback(cb);

        Async_transactional_connection::Put_callback f =
            boost::bind(&put_callback, _1, _2, cptr);
        conn->put(t, r, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::modify(PyObject* table, PyObject* row,PyObject* cb){
    try {
        const Table_name t = from_python<Table_name>(table);
        const Row r = from_python<Row>(row);
        PyObject_ptr cptr = check_callback(cb);

        Async_transactional_connection::Modify_callback f =
            boost::bind(&callback, _1, cptr);
        conn->modify(t, r, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::remove(PyObject* table, PyObject* row,PyObject* cb){
    try {
        const Table_name t = from_python<Table_name>(table);
        const Row r = from_python<Row>(row);
        PyObject_ptr cptr = check_callback(cb);

        Async_transactional_connection::Remove_callback f =
            boost::bind(&callback, _1, cptr);
        conn->remove(t, r, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::drop_table(PyObject* table, PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        const Table_name t = from_python<Table_name>(table);

        Async_transactional_connection::Drop_table_callback f =
            boost::bind(&callback, _1, cptr);
        conn->drop_table(t, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

static void put_trigger_callback(const Result& result, const Trigger_id& tid,
                                 PyObject_ptr cb) {
    PyObject* t = PyTuple_New(2);

    try {
        PyTuple_SET_ITEM(t, 0, to_python(result));
        PyTuple_SET_ITEM(t, 1, to_python(tid));
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        t = PyTuple_New(2);
        PyTuple_SET_ITEM(t, 0,
                         to_python(Result(Result::UNKNOWN_ERROR, e.what())));
        PyTuple_SET_ITEM(t, 1, to_python(Trigger_id()));
    }

    python_callback(t, cb);
}

static void trigger_callback(const Trigger_id& tid, const Row& row,
                             const Trigger_reason reason,
                             PyObject_ptr trigger_func) {
    PyObject* t = PyTuple_New(3);

    try {
        PyTuple_SET_ITEM(t, 0, to_python(tid));
        PyTuple_SET_ITEM(t, 1, to_python(row));
        PyTuple_SET_ITEM(t, 2, to_python(reason));

        python_callback(t, trigger_func);
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        lg.err("Unable to invoke a trigger: %s", e.what());
    }
}

PyObject*
PyTransactional_connection::put_table_trigger(PyObject* table, PyObject* sticky,
                                              PyObject* trigger_func,
                                              PyObject* cb) {
    try {
        const Table_name t = from_python<Table_name>(table);
        const bool s = from_python<bool>(sticky);

        PyObject_ptr tptr(trigger_func, true);
        Trigger_function tf = boost::bind(&trigger_callback, _1, _2, _3, tptr);

        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_connection::Put_trigger_callback f =
            boost::bind(&put_trigger_callback, _1, _2, cptr);
        conn->put_trigger(t, s, tf, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::put_row_trigger(PyObject* table_, PyObject* row,
                                            PyObject* trigger_func,
                                            PyObject* cb) {
    try {
        const Table_name table = from_python<Table_name>(table_);
        const Row r = from_python<Row>(row);
        PyObject_ptr tptr(trigger_func, true);
        PyObject_ptr cptr = check_callback(cb);

        Trigger_function t = boost::bind(&trigger_callback, _1, _2, _3, tptr);

        Async_transactional_connection::Put_trigger_callback f =
            boost::bind(&put_trigger_callback, _1, _2, cptr);
        conn->put_trigger(table, r, t, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_connection::remove_trigger(PyObject* tid, PyObject* cb) {
    try {
        const Trigger_id t = from_python<Trigger_id>(tid);

        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_connection::Remove_trigger_callback f =
            boost::bind(&callback, _1, cptr);
        conn->remove_trigger(t, f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}

PyObject*
PyTransactional_cursor::get_next(PyObject* cb) {
    PyObject_ptr cptr = check_callback(cb);
    Async_transactional_cursor::Get_next_callback f =
        boost::bind(&PyTransactional_cursor::get_next_callback, this,
                    _1, _2, cptr);

    cursor->get_next(f);
    Py_RETURN_NONE;
}

void
PyTransactional_cursor::get_next_callback(const Result& result, const Row& row,
                                          PyObject_ptr cb) {
    PyObject* t = PyTuple_New(2);

    try {
        PyTuple_SET_ITEM(t, 0, to_python(result));
        PyTuple_SET_ITEM(t, 1, to_python(row));
    }
    catch (const runtime_error& e) {
        Py_DECREF(t);

        t = PyTuple_New(2);
        PyTuple_SET_ITEM(t, 0,
                         to_python(Result(Result::UNKNOWN_ERROR, e.what())));
        PyTuple_SET_ITEM(t, 1, to_python(Row()));
    }

    python_callback(t, cb);
}

PyObject*
PyTransactional_cursor::close(PyObject* cb) {
    try {
        PyObject_ptr cptr = check_callback(cb);
        Async_transactional_cursor::Close_callback f =
            boost::bind(&callback, _1, cptr);
        
        cursor->close(f);
        Py_RETURN_NONE;
    }
    catch (const runtime_error& e) {
        /* Unable to convert the arguments. */
        PyErr_SetString(PyExc_TypeError, e.what());
        return 0;
    }
}
