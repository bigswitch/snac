/* 
 * Copyright 2008 (C) Nicira, Inc.
 */
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
#include "pyldap_proxy.hh"

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

#include <sstream>

#include "configuration/properties.hh"
#include "directory/principal_types.hh"
#include "directory/pyprincipal_types.hh"
#include "ldap_proxy.hh"
#include "pyrt/deferredcallback.hh"
#include "pyrt/pycontext.hh"
#include "pyrt/pyglue.hh"
#include "pyrt/pyrt.hh"
#include "swigpyrun.h"
#include "vlog.hh"

#include <Python.h>
#include <boost/bind.hpp>
#include <boost/foreach.hpp>
#include <boost/intrusive_ptr.hpp>
#include <boost/variant/apply_visitor.hpp>

using namespace std;
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::configuration;

static Vlog_module lg("pyldap_proxy");

static const string DIR_TYPE("LDAP");

static PyObject* pydeferred_class;
static PyObject* pydir_class;
static PyObject* pydir_exception_class;
static PyObject* pydir_status_class;

namespace vigil {

/* To fix issue with 64 bit binaries which complain
 * about missing from_python<std::string> definition
 */
template<>
inline
string from_python(PyObject *str) {
    return string(PyString_AsString(str));
}

namespace applications {
namespace directory {

class PropStrVisitor
    : public boost::static_visitor<>
{
public:
    void operator()(const int64_t& i) const {ss.str(""); ss << i;}
    void operator()(const string& str) const {ss.str(str);}
    void operator()(const double& d) const {ss.str(""); ss << d;}
    void operator()(const storage::GUID& g) const {ss.str(g.str());}

    string str() const {
        return ss.str();
    }

private:
    mutable ostringstream ss;
};

class PropFromPyVisitor
    : public boost::static_visitor<>
{
public:
    void operator()(const int64_t& i) const {
        if (PyInt_Check(pyobj)) {
            int64_t v = int64_t(PyInt_AsLong(pyobj));
            if (v == -1 and PyErr_Occurred()) {
                throw DirectoryException(OPERATION_NOT_PERMITTED,
                        "Unsupported type; expected int");
            }
            val = v;
        }
        else if (PyString_Check(pyobj) or PyUnicode_Check(pyobj)) {
            const char *s = ::from_python<string>(pyobj).c_str();
            char *endp;
            errno = 0;
            int64_t v = strtoll(s, &endp, 10);
            if ( (errno == ERANGE && (v == LONG_MAX || v == LONG_MIN))
                 || (errno != 0 && v == 0) || (endp == s) || (*endp != '\0')) {
                throw DirectoryException(OPERATION_NOT_PERMITTED,
                        "Unsupported type; cannot convert string to int");
            }
            val = v;
        }
        else {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported type; expected int");
        }
    }
    void operator()(const string& str) const {
        if (PyString_Check(pyobj) or PyUnicode_Check(pyobj)) {
            val = ::from_python<string>(pyobj);
        }
        else {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported type; expected string");
        }
    }
    void operator()(const double& d) const {
        if (PyFloat_Check(pyobj)) {
            val = PyFloat_AsDouble(pyobj);
        }
        else if (PyString_Check(pyobj) or PyUnicode_Check(pyobj)) {
            const char *s = ::from_python<string>(pyobj).c_str();
            char *endp;
            errno = 0;
            double v = strtod(s, &endp);
            if ( (endp != NULL && (*endp != '\0' || endp == s))
                    || (errno == ERANGE && (v == HUGE_VALF || v == HUGE_VALL))
                    || (errno != 0 && v == 0) ) {
                throw DirectoryException(OPERATION_NOT_PERMITTED,
                        "Unsupported type; cannot convert string to double");
            }
            val = v;
        }
        else {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Unsupported type; expected double");
        }
    }
    void operator()(const storage::GUID& g) const {
        throw DirectoryException(OPERATION_NOT_PERMITTED,
                "Unsupported GUID property value");
    }

    Property::Value get_val() const {
        return val;
    }

    void set_pyval(PyObject *p) { pyobj = p; }
private:
    mutable PyObject *pyobj;
    mutable Property::Value val;
};

/****************************************************************************/ 

/*
 * NOTE: this method steals the reference to value
 */
static void
deferred_call(PyDeferred deferred, const string& method, PyObject* value) {
    Co_critical_section c;
    PyObject* func = PyObject_GetAttrString(deferred, (char *) method.c_str());
    if (!func || !PyCallable_Check(func)) {
        const string exc = pretty_print_python_exception();
        const string msg = "Could not find method named '"+method+"' on "
                           "deferred:\n"+exc;
        lg.err("%s", msg.c_str());
        Py_XDECREF(func);
        return;
    }

    PyObject* pyargs = PyTuple_New(1);
    if (value == NULL) {
        value = Py_None;
        Py_INCREF(value);
    }
    PyTuple_SetItem(pyargs, 0, value);
    PyObject* pyret = PyObject_CallObject(func, pyargs);
    Py_DECREF(func);
    Py_DECREF(pyargs);
    if (!pyret) {
        const string exc = pretty_print_python_exception();
        const string msg = "Failed to call method named '"+method+"' on "
                           "deferred:\n"+exc;
        lg.err("%s", msg.c_str());
    }
    Py_XDECREF(pyret);
}

/*
 * NOTE: this method steals the reference to both deferred and result
 */
static inline void
deferred_callback(PyDeferred deferred, PyObject* result) {
    deferred_call(deferred, "callback", result);
    Py_DECREF(deferred);
}

/*
 * NOTE: this method steals the reference to both deferred and failure
 */
static inline void
deferred_errback(PyDeferred deferred, PyObject* failure) {
    if (failure == NULL and !PyErr_Occurred()) {
        //calling errback with Py_None causes twisted to look for an exception
        failure = ::to_python(string("Unexpected Error"));
    }
    deferred_call(deferred, "errback", failure);
    Py_DECREF(deferred);
}

static inline
PyObject* to_python(Properties* props) {
    PropStrVisitor pstr;
    PyObject* ret = PyDict_New();
    BOOST_FOREACH(Key k, props->get_loaded_keys()) {
        Property_list_ptr plp = props->get_value(k);
        if (plp->size() == 0) {
            lg.warn("Not returning valueless property key '%s'", k.c_str());
        }
        else {
            Property::Value v = (*plp)[0].get_value();
            boost::apply_visitor(pstr, v);
            PyDict_SetItemString(ret, k.c_str(), ::to_python(pstr.str()));
        }
    }
    return ret;
}

/*
 * get_pydeferred - return new Twisted deferred Python object
 *
 * Returned object must be DECREFed *twice* (once on return to python, and 
 * once on callback/errback)
 */
static PyDeferred
get_pydeferred() {
    Co_critical_section c;

    PyObject* pyf = PyObject_CallObject(pydeferred_class, 0);
    if (!pyf) {
        const string msg = pretty_print_python_exception();
        lg.err("cannot instantiate deferred object:\n%s", msg.c_str());
        pyf = Py_None;
    }
    Py_XINCREF(pyf);
    return pyf;
}

static PyObject*
new_dir_exception(PyObject* excclass, const string& message, int code) {
    Co_critical_section c;

    PyObject* pyargs = PyTuple_New(2);
    PyTuple_SetItem(pyargs, 0, ::to_python(message));
    PyTuple_SetItem(pyargs, 1, ::to_python(code));
    PyObject* pyf = PyObject_CallObject(excclass, pyargs);
    if (!pyf) {
        const string msg = pretty_print_python_exception();
        lg.err("cannot instantiate DirectoryException object:\n%s",
                msg.c_str());
        return PyErr_NewException((char*)"nox.lib.directory.UnknownException",
                NULL, NULL);
    }
    return pyf;
}

/*
 * get_pyDirectoryException - return new DirectoryException instance
 */
static PyObject*
get_pyDirectoryException(const string& message, int code) {
    return new_dir_exception(pydir_exception_class, message, code);
}

static void
call_deferred_eb(PyDeferred deferred, DirectoryError code,
        const string& msg) {
    deferred_errback(deferred, get_pyDirectoryException(msg, code));
}

/****************************************************************************/

template <typename T>
inline
T from_python(PyObject*);

/*
 * The from_python template is in the 'vigil' namespace, so these
 * methods must not be moved inside vigil::applications
 */
template<>
inline
directory::AuthSupportSet from_python(PyObject *support_tuple) {
    if (PyList_Check(support_tuple)) {
        support_tuple = PyList_AsTuple(support_tuple);
    }
    else {
        Py_XINCREF(support_tuple);
    }
    if (!PyTuple_Check(support_tuple)) {
        string msg = "Invalid parameter";
        lg.warn("%s", msg.c_str());
        Py_XDECREF(support_tuple);
        throw DirectoryException(OPERATION_NOT_PERMITTED,
                "Invalid parameter; expected tuple");
    }

    directory::AuthSupportSet ss;
    for(Py_ssize_t i = 0; i < PyTuple_Size(support_tuple); ++i) {
        PyObject* item = PyTuple_GetItem(support_tuple, i);
        if (!PyString_Check(item) and !PyUnicode_Check(item)) {
            string msg = "Invalid auth support value in argument";
            lg.warn("%s", msg.c_str());
            Py_XDECREF(support_tuple);
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected string");
        }
        ss.insert(::from_python<string>(item));
    }
    return ss;
}

template<>
inline
directory::PrincipalSupportMap from_python(PyObject *support_dict) {
    if (!PyDict_Check(support_dict)) {
        string msg = "Invalid parameter; expected dict";
        lg.warn("%s", msg.c_str());
        throw DirectoryException(OPERATION_NOT_PERMITTED, msg);
    }
    PyObject *key, *value;
    Py_ssize_t ppos = 0;
    directory::PrincipalSupportMap sm;
    while (PyDict_Next(support_dict, &ppos, &key, &value)) {
        if (!PyInt_Check(key)) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected key type int");
        }
        if (!PyString_Check(value) and !PyUnicode_Check(value)) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected value type str");
        }
        sm[(directory::Principal_Type)PyInt_AS_LONG(key)] =
                ::from_python<string>(value);
    }
    return sm;
}

template<>
inline
map<string, string> from_python(PyObject *query_dict) {
    if (!PyDict_Check(query_dict)) {
        string msg = "Invalid parameter; expected dict";
        lg.warn("%s", msg.c_str());
        throw DirectoryException(OPERATION_NOT_PERMITTED, msg);
    }
    PyObject *key, *value;
    Py_ssize_t ppos = 0;
    directory::PrincipalQuery ret;
    while (PyDict_Next(query_dict, &ppos, &key, &value)) {
        if (!PyString_Check(key) and !PyUnicode_Check(key)) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected key type string");
        }
        if (!PyString_Check(value) and !PyUnicode_Check(value)) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected value type string");
        }
        ret[::from_python<string>(key)] = ::from_python<string>(value);
    }
    return ret;
}


/****************************************************************************/


static void
config_cb(PyDeferred deferred, configuration::Properties* props) {
    deferred_callback(deferred, to_python(props));
}

PyDeferred
pyldap_proxy::initialize(PyObject* ctxt)
{
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        lg.warn("Unable to access Python context.");
        Py_RETURN_NONE;
    }
    component = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
    PyObject* pydeferred_mod = PyImport_ImportModule("twisted.internet.defer");
    if (!pydeferred_mod) {
        const string msg = pretty_print_python_exception();
        lg.warn("Failed to import required twisted module:\n%s", msg.c_str());
        Py_RETURN_NONE;
    }
    pydeferred_class = PyObject_GetAttrString(pydeferred_mod, "Deferred");
    if (!pydeferred_class || !PyCallable_Check(pydeferred_class)) {
        const string msg = pretty_print_python_exception();
        lg.warn("Failed to locate twisted Deferred class:\n%s", msg.c_str());
        Py_DECREF(pydeferred_mod);
        Py_RETURN_NONE;
    }
    Py_DECREF(pydeferred_mod);

    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;

    //TODO: clean up dup check code
    PyObject* pydir_mod = PyImport_ImportModule("nox.lib.directory");
    if (!pydir_mod) {
        string errdesc = "Failed to import required nox directory module:\n"
                + pretty_print_python_exception();
        lg.warn("%s", errdesc.c_str());
        deferred_errback(deferred, ::to_python(errdesc));
        return deferred;
    }
    pydir_class = PyObject_GetAttrString(pydir_mod, "Directory");
    if (!pydir_class) {
        string errdesc = "Failed to locate nox Directory class:\n"
                + pretty_print_python_exception();
        lg.warn("%s", errdesc.c_str());
        deferred_errback(deferred, ::to_python(errdesc));
        Py_DECREF(pydir_mod);
        return deferred;
    }
    pydir_exception_class = PyObject_GetAttrString(pydir_mod,
            "DirectoryException");
    if (!pydir_exception_class) {
        string errdesc = "Failed to locate nox DirectoryException class:\n"
                + pretty_print_python_exception();
        lg.warn("%s", errdesc.c_str());
        deferred_errback(deferred, ::to_python(errdesc));
        Py_DECREF(pydir_mod);
        return deferred;
    }
    Py_DECREF(pydir_mod);
    pydir_status_class = PyObject_GetAttrString(pydir_class, "DirectoryStatus");
    if (!pydir_status_class) {
        string errdesc = "Failed to locate nox DirectoryStatus class:\n"
                + pretty_print_python_exception();
        lg.warn("%s", errdesc.c_str());
        deferred_errback(deferred, ::to_python(errdesc));
        return deferred;
    }

    component->resolve(tstorage);
    ldap_proxy = new Ldap_proxy(component, name, config_id, tstorage);

    bool will_cb = ldap_proxy->configure(
            boost::bind(config_cb, deferred, _1),
            boost::bind(call_deferred_eb, deferred, _1, _2));
    if (!will_cb) {
        string errdesc = "Unknown error in ldap configure";
        lg.warn("%s", errdesc.c_str());
        deferred_errback(deferred, ::to_python(errdesc));
    }

    return deferred;
}

string
pyldap_proxy::get_type() {
    return DIR_TYPE;
}

PyObject* 
pyldap_proxy::get_default_config() {
    Properties::Default_value_map defaults;
    Ldap_proxy::set_default_props(defaults);

    PropStrVisitor pstr;
    PyObject* ret = PyDict_New();
    BOOST_FOREACH(Properties::Default_value_map::value_type v, defaults) {
        const Key& key = v.first;
        const std::vector<Property>& values = v.second;
        boost::apply_visitor(pstr, values[0].get_value());

        PyDict_SetItemString(ret, key.c_str(), ::to_python(pstr.str()));
    }

    return ret;
}

PyObject* 
pyldap_proxy::get_config_params() {
    return to_python(ldap_proxy->get_properties());
}

static void
call_deferred_cb(PyDeferred deferred, Properties_ptr props) {
    deferred_callback(deferred, to_python(props.get()));
}

static void
set_config_params_cb(PyObject* config_str_dict,
        Properties_ptr props, PyDeferred deferred) {
    try {
        if (!PyDict_Check(config_str_dict)) {
            throw DirectoryException(OPERATION_NOT_PERMITTED,
                    "Invalid parameter; expected dict");
        }
        PropFromPyVisitor prop_from_py;
        PyObject *key, *value;
        Py_ssize_t ppos = 0;
        while (PyDict_Next(config_str_dict, &ppos, &key, &value)) {
            if (!PyString_Check(key) and !PyUnicode_Check(key)) {
                throw DirectoryException(OPERATION_NOT_PERMITTED, 
                        "Invalid parameter; expected key type string");
            }
            string k = ::from_python<string>(key);
            Property_list_ptr plp = props->get_value(k);
            if (plp->size() == 0) {
                lg.warn("Ignoring unknow property '%s' in set_config_params",
                        k.c_str());
                continue;
            }
            prop_from_py.set_pyval(value);
            boost::apply_visitor(prop_from_py, (*plp)[0].get_value());

            Property::Value v = prop_from_py.get_val();
            PropStrVisitor pstr;
            boost::apply_visitor(pstr, v);
            lg.dbg("Updated parameter %s => %s\n", k.c_str(),
                    pstr.str().c_str());
            plp->clear();
            plp->push_back(Property(v));
        }
        props->async_commit(
                boost::bind(call_deferred_cb, deferred, props),
                boost::bind(call_deferred_eb, deferred, UNKNOWN_ERROR,
                    "Failed to write configuration"));
    }
    catch (exception& e) {
        string errstr = string("set_config_params failed: ") + e.what();
        lg.warn("%s", errstr.c_str());
        deferred_errback(deferred, ::to_python(errstr));
    }
}

PyDeferred
pyldap_proxy::set_config_params(PyObject* config_str_dict) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        Properties_ptr props(new configuration::Properties(
                tstorage, ldap_proxy->get_prop_section(),
                ldap_proxy->get_default_props()));

        props->async_begin(
                boost::bind(set_config_params_cb, config_str_dict, props,
                        deferred),
                boost::bind(call_deferred_eb, deferred, UNKNOWN_ERROR, 
                        "Failed to read configuration"));
        return deferred;
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

PyObject*
pyldap_proxy::get_status() { 
    Co_critical_section c;
    int status_cd = ldap_proxy->get_status();

    PyObject* args = PyTuple_New(1);
    PyTuple_SetItem(args, 0, ::to_python(status_cd));
    PyObject* dsi = PyInstance_New(pydir_status_class, args, NULL);
    Py_XDECREF(args);
    if (!dsi) {
        const string msg = "Failed to instantiate DirectoryStatus instance:\n"
            + pretty_print_python_exception();
        lg.err("%s", msg.c_str());
        Py_RETURN_NONE;
    }
    return dsi;
}

/****************************************************************************/

static void
set_enabled_auth_types_cb(const AuthSupportSet& supp, PyDeferred deferred) {
    deferred_callback(deferred, to_python(supp));
}

PyDeferred
pyldap_proxy::set_enabled_auth_types(PyObject* auth_type_tuple) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        AuthSupportSet supp = from_python<AuthSupportSet>(auth_type_tuple);
        ldap_proxy->set_enabled_auth_types(supp, 
                boost::bind(set_enabled_auth_types_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

PyDeferred
pyldap_proxy::get_credentials(int principal_type,
        std::string principal_name, const char* credtype) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        //TODO: create a PasswordCredential Object
        PyObject* ret = PyList_New(0);
        deferred_callback(deferred, ret);
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;

}

static void
simple_auth_cb(PyDeferred deferred, const AuthResult& result) {
    deferred_callback(deferred, to_python(result));
}

PyDeferred
pyldap_proxy::simple_auth(const char* username, const char* password)
{
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        ldap_proxy->simple_auth(string(username), string(password),
                boost::bind(simple_auth_cb, deferred, _1));
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

/****************************************************************************/

PyObject*
pyldap_proxy::get_enabled_principals() {
    return to_python(ldap_proxy->get_enabled_principals());
}

static void
set_enabled_principals_cb(const PrincipalSupportMap& supp, PyDeferred deferred) {
    deferred_callback(deferred, to_python(supp));
}

PyDeferred
pyldap_proxy::set_enabled_principals(PyObject* enabled_principal_dict) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        PrincipalSupportMap supp = 
                from_python<PrincipalSupportMap>(enabled_principal_dict);
        bool willcb = ldap_proxy->set_enabled_principals(supp, 
                boost::bind(set_enabled_principals_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in set_enabled_principals")));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

static void
get_principal_cb(const PrincipalInfo_ptr principal, PyDeferred deferred) {
    try {
        if (principal == NULL) {
            Py_INCREF(Py_None);
            deferred_callback(deferred, Py_None);
        }
        else {
            deferred_callback(deferred, to_python(*principal));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
}

PyDeferred
pyldap_proxy::get_principal(int principal_type, std::string principal_name) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        bool willcb = ldap_proxy->get_principal((Principal_Type)principal_type,
                principal_name,
                boost::bind(get_principal_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in get_principal")));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

static void
search_principals_cb(const Principal_name_set& pns, PyDeferred deferred) {
    try {
        deferred_callback(deferred, to_python(pns));
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
}

PyDeferred
pyldap_proxy::search_principals(int principal_type, PyObject* query_dict) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        PrincipalQuery pq = from_python<PrincipalQuery>(query_dict);
        bool willcb = ldap_proxy->search_principals(
                (Principal_Type)principal_type, pq,
                boost::bind(search_principals_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in search_principals")));
        }
    } 
    catch (exception& e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

/****************************************************************************/
PyObject*
pyldap_proxy::get_enabled_groups() {
    return to_python(ldap_proxy->get_enabled_groups());
}

PyDeferred
pyldap_proxy::set_enabled_groups(PyObject* enabled_group_dict) {
    //we don't support any groups that can be enabled separate from principals
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    deferred_errback(deferred, PyString_FromString("Not supported"));
    return deferred;
}

static void
group_set_cb(const Group_name_set& gns, PyDeferred deferred) {
    deferred_callback(deferred, to_python(gns));
}

PyDeferred
pyldap_proxy::get_group_membership(int group_type, std::string member,
        PyObject* local_groups)
{
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        bool willcb = ldap_proxy->get_group_membership(
                (Group_Type)group_type, member,
                boost::bind(group_set_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in get_group_membership")));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

PyDeferred
pyldap_proxy::search_groups(int group_type, PyObject* query_dict) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        GroupQuery gq = from_python<GroupQuery>(query_dict);
        bool willcb = ldap_proxy->search_groups(
                (Group_Type)group_type, gq,
                boost::bind(group_set_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in search_groups")));
        }
    }
    catch (exception & e) {
        //TODO: make DirectoryException
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

static void
get_group_cb(const GroupInfo_ptr gi, PyDeferred deferred) {
    try {
        if (gi == NULL) {
            Py_INCREF(Py_None);
            deferred_callback(deferred, Py_None);
        }
        else {
            deferred_callback(deferred, to_python(*gi));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
}

PyDeferred
pyldap_proxy::get_group(int group_type, std::string group_name) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        bool willcb = ldap_proxy->get_group(
                (Group_Type)group_type, group_name,
                boost::bind(get_group_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in get_group")));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

PyDeferred
pyldap_proxy::get_group_parents(int group_type, std::string group_name) {
    PyDeferred deferred = get_pydeferred();
    if (deferred == Py_None) return deferred;
    try{
        bool willcb = ldap_proxy->get_group_parents(
                (Group_Type)group_type, group_name,
                boost::bind(group_set_cb, _1, deferred),
                boost::bind(call_deferred_eb, deferred, _1, _2));
        if (!willcb) {
            deferred_errback(deferred, ::to_python(
                        string("Unknown failure in get_group_parents")));
        }
    }
    catch (exception & e) {
        deferred_errback(deferred, ::to_python(string(e.what())));
    }
    return deferred;
}

} // namespcae directory
} // namespcae applications
} // namespace vigil





