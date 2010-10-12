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
#include "directorymanager.hh"
#include <boost/bind.hpp>

#include "directory.hh"
#include "group_change_event.hh"
#include "group_event.hh"
#include "location_del_event.hh"
#include "netinfo_mod_event.hh"
#include "principal_event.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;

namespace vigil {

using namespace applications;
using namespace applications::directory;

static Vlog_module lg("cdirectorymanager");

#ifdef TWISTED_ENABLED

#define CHECK_PY_GETATTR(main_obj, attr_name, attr_obj, chk_fn, onfail)         \
    do {                                                                        \
        attr_obj = PyObject_GetAttrString(main_obj, attr_name);                 \
        if (attr_obj == NULL || !(chk_fn(attr_obj))) {                          \
            VLOG_ERR(lg, "Could not access python attribute '%s'.", attr_name); \
            onfail;                                                             \
        }                                                                       \
    } while (0)

#define NO_CHECK(x) true

template <>
inline
uint64_t
from_python(PyObject *pyint)
{
    return PyInt_AsUnsignedLongLongMask(pyint);
}

template <>
inline
uint32_t
from_python(PyObject *pyint)
{
    return PyInt_AsUnsignedLongMask(pyint);
}

template <>
inline
uint16_t
from_python(PyObject *pyint)
{
    return PyInt_AsUnsignedLongMask(pyint);
}

// we can convert either standard strings, or unicode string
bool isPyStringType(PyObject *s) { 
  return PyString_Check(s) || PyUnicode_Check(s); 
} 

template <>
inline
std::string
from_python(PyObject *s)
{
    if (PyString_Check(s)) {
        return std::string(PyString_AsString(s));
    } else if (PyUnicode_Check(s)) {
        PyObject* u = PyUnicode_AsUTF8String(s);
        if (u == NULL) {
            lg.err("Could not encode unicode as UTF-8");
            return "";
        }
        std::string r(PyString_AsString(u));
        Py_DECREF(u);
        return r;
    }
    return "";
}

template <>
inline
bool
from_python(PyObject *pybool)
{
    return pybool == Py_True;
}

template <>
inline
datapathid
from_python(PyObject *pydp)
{
    static PyObject *method = PyString_FromString("as_host");
    if (method == NULL) {
        VLOG_ERR(lg, "Could not create as_host string.");
    } else {
        PyObject *as_host = PyObject_CallMethodObjArgs(pydp, method, NULL);
        if (as_host == NULL) {
            const string exc = pretty_print_python_exception();
            VLOG_ERR(lg, "Could not get as_host() datapathid value: %s",
                     exc.c_str());
        } else {
            datapathid dp = datapathid::from_host(from_python<uint64_t>(as_host));
            Py_DECREF(as_host);
            return dp;
        }
    }
    return datapathid::from_host(0);
}

template <>
inline
ethernetaddr
from_python(PyObject *pyeth)
{
    static PyObject *method = PyString_FromString("hb_long");
    if (method == NULL) {
        VLOG_ERR(lg, "Could not create hb_long string.");
    } else {
        PyObject *as_host = PyObject_CallMethodObjArgs(pyeth, method, NULL);
        if (as_host == NULL) {
            const string exc = pretty_print_python_exception();
            VLOG_ERR(lg, "Could not get hb_long() ethernetaddr value: %s",
                     exc.c_str());
        } else {
            ethernetaddr eth(from_python<uint64_t>(as_host));
            Py_DECREF(as_host);
            return eth;
        }
    }
    return ethernetaddr((uint64_t)0);
}

template <>
inline
SwitchInfo
from_python(PyObject *pyswitch)
{
    SwitchInfo s;
    PyObject *name, *dp;
    CHECK_PY_GETATTR(pyswitch,"name", name, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyswitch,"dpid", dp, NO_CHECK, goto done);
    if (name != Py_None) {
        s.name = from_python<std::string>(name);
    }
    if (name != Py_None) {
        s.dpid = from_python<datapathid>(dp);
    }

done:
    Py_XDECREF(name);
    Py_XDECREF(dp);
    return s;
}

template <>
inline
LocationInfo
from_python(PyObject *pylocation)
{
    LocationInfo l;
    PyObject *name=0, *dp=0, *port=0;
    CHECK_PY_GETATTR(pylocation, "name", name, isPyStringType, goto done);
    CHECK_PY_GETATTR(pylocation,"dpid",dp, NO_CHECK, goto done);
    CHECK_PY_GETATTR(pylocation,"port",port, PyInt_Check, goto done);
    if (name != Py_None) {
        l.name = from_python<std::string>(name);
    }
    if (dp != Py_None) {
        l.dpid = from_python<datapathid>(dp);
    }
    if (port != Py_None) {
        l.port = from_python<uint16_t>(port);
    }

done:
    Py_XDECREF(name);
    Py_XDECREF(dp);
    Py_XDECREF(port);
    return l;
}

template <>
inline
NetInfo
from_python(PyObject *pynet)
{
    NetInfo n;
    PyObject *dp=0, *port=0, *dl=0, *nw=0, *is_router=0, *is_gway=0;

    CHECK_PY_GETATTR(pynet, "dpid", dp, NO_CHECK, goto done);
    CHECK_PY_GETATTR(pynet, "port", port, PyInt_Check, goto done);
    CHECK_PY_GETATTR(pynet, "dladdr", dl, NO_CHECK, goto done);
    CHECK_PY_GETATTR(pynet, "nwaddr", nw, PyInt_Check, goto done);
    CHECK_PY_GETATTR(pynet, "is_router", is_router, PyBool_Check, goto done);
    CHECK_PY_GETATTR(pynet, "is_gateway", is_gway, PyBool_Check, goto done);
    if (dp != Py_None) {
        n.dpid = from_python<datapathid>(dp);
    }
    if (port != Py_None) {
        n.port = from_python<uint16_t>(port);
    }
    if (dl != Py_None) {
        n.dladdr = from_python<ethernetaddr>(dl);
    }
    if (nw != Py_None) {
        n.nwaddr = from_python<uint32_t>(nw);
    }
    if (is_router != Py_None) {
        n.is_router = from_python<bool>(is_router);
    }
    if (is_gway != Py_None) {
        n.is_gateway = from_python<bool>(is_gway);
    }

done:
    Py_XDECREF(dp);
    Py_XDECREF(port);
    Py_XDECREF(dl);
    Py_XDECREF(nw);
    return n;
}

template <>
inline
HostInfo
from_python(PyObject *pyhost)
{
    HostInfo h;
    PyObject *name=0, *desc=0, *aliases=0, *netinfos=0;
    CHECK_PY_GETATTR(pyhost, "name", name, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyhost, "description", desc, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyhost, "aliases", aliases, PyList_Check, goto done);
    CHECK_PY_GETATTR(pyhost,"netinfos",netinfos, PyList_Check, goto done);
    if (name != Py_None) {
      h.name = from_python<std::string>(name);
    }
    if (desc != Py_None) {
      h.description = from_python<std::string>(desc);
    }
    if (aliases != Py_None) {
        uint32_t n = PyList_GET_SIZE(aliases);
        for (uint32_t i = 0; i < n; ++i) {
            PyObject *alias = PyList_GET_ITEM(aliases, i);
            h.aliases.push_back(from_python<std::string>(alias));
        }
    }
    if (netinfos != Py_None) {
        uint32_t n = PyList_GET_SIZE(netinfos);
        for (uint32_t i = 0; i < n; ++i) {
            PyObject *netinfo = PyList_GET_ITEM(netinfos, i);
            h.netinfos.push_back(from_python<NetInfo>(netinfo));
        }
    }

done:
    Py_XDECREF(name);
    Py_XDECREF(desc);
    Py_XDECREF(aliases);
    Py_XDECREF(netinfos);
    return h;
}

template <>
inline
UserInfo
from_python(PyObject *pyuser)
{
    UserInfo u;
    PyObject *name=0, *id=0, *real_name=0, *desc=0, *location=0, *phone=0,
        *email=0;

    CHECK_PY_GETATTR(pyuser, "name", name, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyuser, "user_id", id, PyInt_Check, goto done);
    CHECK_PY_GETATTR(pyuser, "user_real_name", real_name, isPyStringType,
                     goto done);
    CHECK_PY_GETATTR(pyuser, "description", desc, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyuser, "location", location, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyuser, "phone", phone, isPyStringType, goto done);
    CHECK_PY_GETATTR(pyuser, "user_email", email, isPyStringType, goto done);
    if (name != Py_None) {
        u.name = from_python<std::string>(name);
    }
    if (id != Py_None) {
        u.user_id = from_python<uint32_t>(id);
    }
    if (real_name != Py_None) {
        u.user_real_name = from_python<std::string>(real_name);
    }
    if (desc != Py_None) {
        u.description = from_python<std::string>(desc);
    }
    if (location != Py_None) {
        u.location = from_python<std::string>(location);
    }
    if (phone != Py_None) {
        u.phone = from_python<std::string>(phone);
    }
    if (email != Py_None) {
        u.user_email = from_python<std::string>(email);
    }

done:
    Py_XDECREF(name);
    Py_XDECREF(id);
    Py_XDECREF(real_name);
    Py_XDECREF(desc);
    Py_XDECREF(location);
    Py_XDECREF(phone);
    Py_XDECREF(email);
    return u;
}

template <>
inline
CertFingerprintCredential
from_python(PyObject *pycred)
{
    PyObject *type=0, *fp=0, *approved=0;
    CertFingerprintCredential c;

    CHECK_PY_GETATTR(pycred, "type", type, isPyStringType, goto done);
    CHECK_PY_GETATTR(pycred, "fingerprint", fp, isPyStringType, goto done);
    CHECK_PY_GETATTR(pycred, "is_approved", approved, PyBool_Check, goto done);
    if (type != Py_None) {
      c.type = from_python<std::string>(type);
    }
    if (fp != Py_None) {
        c.fingerprint = from_python<std::string>(fp);
    }
    if (approved != Py_None) {
        c.is_approved = from_python<bool>(approved);
    }

done:
    Py_XDECREF(type);
    Py_XDECREF(fp);
    Py_XDECREF(approved);
    return c;
}

#endif

namespace applications {

DirectoryManager::DirectoryManager(const container::Context *c,
                                   const json_object *d)
    : Component(c), dm(NULL), create_dp(NULL), create_eth(NULL),
      create_ip(NULL), create_cidr(NULL), create_cred(NULL)
{}

void
DirectoryManager::getInstance(const container::Context* ctxt,
                              DirectoryManager*& d)
{
    d = dynamic_cast<DirectoryManager*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(DirectoryManager).name())));
}

void
DirectoryManager::configure(const container::Configuration*)
{
    register_event(Principal_name_event::static_get_name());
    register_event(Group_name_event::static_get_name());
    register_event(Group_change_event::static_get_name());
    register_event(Location_delete_event::static_get_name());
    register_event(NetInfo_mod_event::static_get_name());
}

void
DirectoryManager::install()
{}

bool
DirectoryManager::set_py_dm(PyObject *dm_)
{
#ifdef TWISTED_ENABLED
    Py_XDECREF(dm);
    dm = dm_;
    Py_XINCREF(dm);
    return true;
#else
    VLOG_ERR(lg, "Cannot set py directory manager - Python disabled.");
    return false;
#endif // TWISTED_ENABLED
}

#ifdef TWISTED_ENABLED

#define MAKE_SET_CREATE_FN(fn, class_var, desc_str)                       \
bool DirectoryManager::fn(PyObject *fn_param) {                           \
    if (fn_param != NULL && !PyCallable_Check(fn_param)) {                \
        VLOG_ERR(lg, "Cannot set %s to non-callable PyObject", desc_str); \
        return false;                                                     \
    }                                                                     \
    Py_XDECREF(class_var);                                                \
    class_var = fn_param;                                                 \
    Py_XINCREF(class_var);                                                \
    return true;                                                          \
}

#else
#define MAKE_SET_CREATE_FN(fn, class_var, desc_str)                       \
bool DirectoryManager::fn(PyObject *fn_param) {                           \
    VLOG_ERR(lg, "Cannot set %s - Python disabled.", desc_str);           \
    return false;                                                         \
}

#endif

MAKE_SET_CREATE_FN(set_create_dp, create_dp, "create_dp")
MAKE_SET_CREATE_FN(set_create_eth, create_eth, "create_eth")
MAKE_SET_CREATE_FN(set_create_ip, create_ip, "create_ip")
MAKE_SET_CREATE_FN(set_create_cidr, create_cidr, "create_cidr")
MAKE_SET_CREATE_FN(set_create_cred, create_cred, "create_cred")

#define CHECK_CREATE_FN(class_var, desc_str, onfail)                      \
    do {                                                                  \
        if (create_dp == NULL) {                                          \
            VLOG_ERR(lg, " %s not set.",desc_str);                        \
            onfail;                                                       \
        }                                                                 \
    } while(0)


PyObject*
DirectoryManager::to_datapathid(uint64_t dp)
{
#ifdef TWISTED_ENABLED
    PyObject *pydp = ::to_python(dp);
    if (pydp == NULL) {
        VLOG_ERR(lg, "Could not create datapathid uint64_t PyObject.");
        return NULL;
    }

    CHECK_CREATE_FN(create_dp, "create_dp", return NULL);
    PyObject *ret = PyObject_CallFunctionObjArgs(create_dp, pydp, NULL);
    if (ret == NULL) {
        const string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call create_dp function: %s", exc.c_str());
    }
    Py_DECREF(pydp);
    return ret;
#else
    VLOG_ERR(lg, "Cannot create datapathid - Python disabled.");
    return NULL;
#endif // TWISTED_ENABLED
}

PyObject*
DirectoryManager::to_ethernetaddr(uint64_t dladdr)
{
#ifdef TWISTED_ENABLED
    PyObject *pydladdr = ::to_python(dladdr);
    if (pydladdr == NULL) {
        VLOG_ERR(lg, "Could not create ethernetaddr uint64_t PyObject.");
        return NULL;
    }

    CHECK_CREATE_FN(create_eth, "create_eth", return NULL);
    PyObject *ret = PyObject_CallFunctionObjArgs(create_eth, pydladdr, NULL);
    if (ret == NULL) {
        const string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call create_eth function: %s", exc.c_str());
    }
    Py_DECREF(pydladdr);
    return ret;
#else
    VLOG_ERR(lg, "Cannot create ethernetaddr - Python disabled.");
    return NULL;
#endif // TWISTED_ENABLED
}

PyObject*
DirectoryManager::to_ipaddr(uint32_t nwaddr)
{
#ifdef TWISTED_ENABLED
    PyObject *pynwaddr = ::to_python(nwaddr);
    if (pynwaddr == NULL) {
        VLOG_ERR(lg, "Could not create ipaddr uint32_t PyObject.");
        return NULL;
    }

    CHECK_CREATE_FN(create_ip, "create_ip", return NULL);
    PyObject *ret = PyObject_CallFunctionObjArgs(create_ip, pynwaddr, NULL);
    if (ret == NULL) {
        const string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call create_ip function: %s", exc.c_str());
    }
    Py_DECREF(pynwaddr);
    return ret;
#else
    VLOG_ERR(lg, "Cannot create ipaddr - Python disabled.");
    return NULL;
#endif // TWISTED_ENABLED
}

PyObject*
DirectoryManager::to_cidr(uint32_t nwaddr)
{
#ifdef TWISTED_ENABLED
    ipaddr ip(nwaddr);
    std::string ipstr = ip.string();
    PyObject *pynwaddr = PyString_FromString(ipstr.c_str());
    if (pynwaddr == NULL) {
        VLOG_ERR(lg, "Could not create cidr string PyObject.");
        return NULL;
    }

    CHECK_CREATE_FN(create_cidr, "create_cidr", return NULL);
    PyObject *ret = PyObject_CallFunctionObjArgs(create_cidr, pynwaddr, NULL);
    if (ret == NULL) {
        const string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call create_cidr function: %s", exc.c_str());
    }
    Py_DECREF(pynwaddr);
    return ret;
#else
    VLOG_ERR(lg, "Cannot create cidr - Python disabled.");
    return NULL;
#endif // TWISTED_ENABLED
}


// SHOULD ALL PyObject * variables when passed to these macros...

#define CHECK_PY_CREATE(value, name, onfail)                          \
    do {                                                              \
        if (value == NULL) {                                          \
            VLOG_ERR(lg, "Could not create %s PyObject.", name);      \
            onfail;                                                   \
        }                                                             \
    } while (0)

#define CHECK_PY_CREATE_FOR_DICT(value, dict, key, onfail)            \
    do {                                                              \
        if (value == NULL) {                                          \
            VLOG_ERR(lg, "Could not create %s PyObject.", key);       \
            Py_DECREF(dict);                                          \
            onfail;                                                   \
        } else {                                                      \
            if (PyDict_SetItemString(dict, key, value) != 0) {        \
                VLOG_ERR(lg, "Could not set dict %s key value.", key);\
                Py_DECREF(dict);                                      \
                Py_DECREF(value);                                     \
                onfail;                                               \
            }                                                         \
            Py_DECREF(value);                                         \
        }                                                             \
    } while (0)

#define CHECK_PY_RETURN(ret, name, onfail)                            \
    do {                                                              \
        if (ret == NULL) {                                            \
            const string exc = pretty_print_python_exception();       \
            VLOG_ERR(lg, "Error calling Python function '%s': %s",    \
                     name, exc.c_str());                              \
            onfail;                                                   \
        }                                                             \
    } while (0)

PyObject*
DirectoryManager::to_certFingerprintCredential(
    const CertFingerprintCredential & c_cred) {
#ifdef TWISTED_ENABLED
    CHECK_CREATE_FN(create_cred, "create_cred", return NULL);

    PyObject *fp = 0, *approved = 0, *type = 0, *cred = 0;
    fp = ::to_python(c_cred.fingerprint);
    CHECK_PY_CREATE(fp, "fingerprint", goto done);
    approved = ::to_python(c_cred.is_approved);
    CHECK_PY_CREATE(approved, "is_approved", goto done);
    type = ::to_python(c_cred.type);
    CHECK_PY_CREATE(type, "type", goto done);

    cred = PyObject_CallFunctionObjArgs(create_cred, type, NULL);
    CHECK_PY_RETURN(cred, "create_cred" , goto done);
    PyObject_SetAttrString(cred, "fingerprint", fp);
    PyObject_SetAttrString(cred, "is_approved", approved);

done:
    Py_XDECREF(fp);
    Py_XDECREF(type);
    Py_XDECREF(approved);
    return cred;
#else
    VLOG_ERR(lg, "Cannot create CertFingerprintCredential - Python disabled.");
    return NULL;
#endif // TWISTED_ENABLED
}

bool
DirectoryManager::put_certfp_credential(Directory::Principal_Type ptype,
                                        const string &mangled_principal_name,
                                        const CertFingerprintCredential &c_cred,
                                        const CredentialCb& cred_cb,
                                        const ErrorCb& error_cb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    DeferredCallback::Callback cb, ecb;
    bool success = false;
    PyObject *cred=0, *principal_type=0, *mangled_name=0, *credtype=0,
             *cred_list=0, *ret=0, *dcb=0, *edcb=0;

    static const char *method_name = "put_credentials";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, goto done);

    principal_type = ::to_python(int(ptype));
    CHECK_PY_CREATE(principal_type, "principal type", return false);
    mangled_name = ::to_python(mangled_principal_name);
    CHECK_PY_CREATE(mangled_name, "principal_name", goto done);
    principal_type = ::to_python((int) Directory::SWITCH_PRINCIPAL);
    CHECK_PY_CREATE(principal_type, "principal type", goto done);
    credtype = ::to_python(Directory::AUTHORIZED_CERT_FP);
    CHECK_PY_CREATE(credtype, "cred_type", goto done);
    cred = to_certFingerprintCredential(c_cred);
    CHECK_PY_CREATE(cred, "credential", goto done);
    cred_list = PyList_New(1);
    CHECK_PY_CREATE(cred_list, "cred_list", goto done);
    PyList_SetItem(cred_list, 0, cred); // steals ref

    ret = PyObject_CallMethodObjArgs(dm, method, principal_type, mangled_name,
                                     cred_list, credtype, NULL);
    CHECK_PY_RETURN(ret, method_name, goto done);

    cb = boost::bind(&DirectoryManager::credentials_cb, this, _1, cred_cb),
        ecb = boost::bind(&DirectoryManager::errback, this, _1,
                          "put_credentials", error_cb);

    dcb = DeferredCallback::get_instance(cb);
    CHECK_PY_CREATE(dcb, "deferred callback", goto done);
    edcb = DeferredCallback::get_instance(ecb);
    CHECK_PY_CREATE(edcb, "error deferred callback", goto done);


    if (DeferredCallback::add_callbacks(ret, dcb, edcb)) {
        success = true;
    }
done:
    // cred_list stole reference to 'cred'
    Py_XDECREF(cred_list);
    Py_XDECREF(principal_type);
    Py_XDECREF(mangled_name);
    Py_XDECREF(credtype);
    Py_XDECREF(ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    return success;
#else
    VLOG_ERR(lg, "Cannot call put_credentials - Python disabled.");
    return false;
#endif
}


void
DirectoryManager::errback(PyObject *error, const char *fn, const ErrorCb& cb)
{
#ifdef TWISTED_ENABLED
    static PyObject *method = PyString_FromString("getErrorMessage");
    if (method == NULL) {
        VLOG_ERR(lg, "Could not create getErrorMessage string.");
    } else {
        PyObject *errstr = PyObject_CallMethodObjArgs(error, method, NULL);
        if (errstr == NULL) {
            const string exc = pretty_print_python_exception();
            VLOG_ERR(lg, "Could not get failure error message: %s",exc.c_str());
        } else {
            const char *cerrstr = PyString_AsString(errstr);
            VLOG_ERR(lg, "Could not call %s method: %s.", fn, cerrstr);
            Py_DECREF(errstr);
        }
    }
    cb();
#endif
}

bool
DirectoryManager::supports_authentication()
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *method_name = "supports_authentication";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);

    PyObject *ret = PyObject_CallMethodObjArgs(dm, method, NULL);
    CHECK_PY_RETURN(ret, method_name, return false);

    bool result = from_python<bool>(ret);
    Py_DECREF(ret);
    return result;
#else
    VLOG_ERR(lg, "Cannot look up authentication - Python disabled.");
    return false;
#endif
}

#ifdef TWISTED_ENABLED
inline
bool
DirectoryManager::call_method(const char *method_name,
                              PyObject *method,
                              PyObject *py_obj,
                              const std::string& dir,
                              const DeferredCallback::Callback& cb,
                              const DeferredCallback::Callback& ecb)
{
    bool result = false;
    PyObject *py_dir = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    if (dir != "") {
        py_dir = ::to_python(dir);
        CHECK_PY_CREATE(py_dir, "Directory string", goto done);
        py_ret = PyObject_CallMethodObjArgs(dm, method, py_obj, py_dir, NULL);
    } else {
        py_ret = PyObject_CallMethodObjArgs(dm, method, py_obj, NULL);
    }

    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(cb);
    edcb = DeferredCallback::get_instance(ecb);

    CHECK_PY_CREATE(dcb, "deferred callback", goto done);
    CHECK_PY_CREATE(edcb, "deferred callback", goto done);

    result = DeferredCallback::add_callbacks(py_ret, dcb, edcb);

done:
    Py_XDECREF(py_dir);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    return result;
}

inline
bool
DirectoryManager::call_search_principals(PyObject *py_ptype, PyObject *py_obj,
                                         const std::string& dir,
                                         const SearchCb& cb, const ErrorCb& ecb)
{
    static const char *method_name = "search_principals";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);

    bool result = false;
    PyObject *py_dir = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    if (dir != "") {
        py_dir = ::to_python(dir);
        CHECK_PY_CREATE(py_dir, "Directory string", goto done);
        py_ret = PyObject_CallMethodObjArgs(dm, method, py_ptype, py_obj, py_dir, NULL);
    } else {
        py_ret = PyObject_CallMethodObjArgs(dm, method, py_ptype, py_obj, NULL);
    }

    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::search_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    CHECK_PY_CREATE(dcb, "deferred callback", goto done);
    CHECK_PY_CREATE(edcb, "deferred callback", goto done);

    result = DeferredCallback::add_callbacks(py_ret, dcb, edcb);

done:
    Py_XDECREF(py_dir);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    return result;
}

inline
PyObject*
DirectoryManager::get_py_gtype(Directory::Group_Type gtype)
{
    static PyObject *switch_group = ::to_python(int(Directory::SWITCH_PRINCIPAL_GROUP));
    static PyObject *location_group = ::to_python(int(Directory::LOCATION_PRINCIPAL_GROUP));
    static PyObject *host_group = ::to_python(int(Directory::HOST_PRINCIPAL_GROUP));
    static PyObject *user_group = ::to_python(int(Directory::USER_PRINCIPAL_GROUP));
    static PyObject *dladdr_group = ::to_python(int(Directory::DLADDR_GROUP));
    static PyObject *nwaddr_group = ::to_python(int(Directory::NWADDR_GROUP));

    switch(gtype) {
    case Directory::SWITCH_PRINCIPAL_GROUP:
        return switch_group;
    case Directory::LOCATION_PRINCIPAL_GROUP:
        return location_group;
    case Directory::HOST_PRINCIPAL_GROUP:
        return host_group;
    case Directory::USER_PRINCIPAL_GROUP:
        return user_group;
    case Directory::DLADDR_GROUP:
        return dladdr_group;
    case Directory::NWADDR_GROUP:
        return nwaddr_group;
    default:
        VLOG_ERR(lg, "Unknown group type %u.", gtype);
    }

    return NULL;
}

inline
bool
DirectoryManager::call_group_method(PyObject *py_gtype,
                                    PyObject *py_principal,
                                    const std::string& dir,
                                    bool include_global,
                                    const SearchCb& cb, const ErrorCb& ecb)
{
    static const char *method_name = "get_group_membership";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);

    bool result = false;
    PyObject *py_dir = 0, *py_include = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    py_dir = ::to_python(dir);
    CHECK_PY_CREATE(py_dir, "Directory name", goto done);

    py_include = ::to_python(include_global);
    CHECK_PY_CREATE(py_include, "Include global bool", goto done);

    py_ret = PyObject_CallMethodObjArgs(dm, method, py_gtype, py_principal,
                                        py_dir, py_include, NULL);

    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::search_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    CHECK_PY_CREATE(dcb, "deferred callback", goto done);
    CHECK_PY_CREATE(edcb, "deferred callback", goto done);

    result = DeferredCallback::add_callbacks(py_ret, dcb, edcb);

done:
    Py_XDECREF(py_dir);
    Py_XDECREF(py_include);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    return result;
}

inline
bool
DirectoryManager::call_modify_group(const std::string& group_name,
                                    PyObject *py_gtype, PyObject *py_princes,
                                    PyObject *py_subgroups, bool add,
                                    const EmptyCb& cb, const ErrorCb& ecb)
{
    bool result = false;

    static const char *add_method_name = "add_group_members";
    static PyObject *add_method = PyString_FromString(add_method_name);
    CHECK_PY_CREATE(add_method, add_method_name, return false);

    static const char *del_method_name = "del_group_members";
    static PyObject *del_method = PyString_FromString(del_method_name);
    CHECK_PY_CREATE(del_method, del_method_name, return false);

    const char *method_name;
    PyObject *method;
    PyObject *py_gname = 0, *py_ret = 0, *dcb = 0, *edcb = 0;

    if (add) {
        method_name = add_method_name;
        method = add_method;
    } else {
        method_name = del_method_name;
        method = del_method;
    }

    py_gname = ::to_python(group_name);
    CHECK_PY_CREATE(py_gname, "group name", goto done);

    py_ret = PyObject_CallMethodObjArgs(dm, method, py_gtype, py_gname,
                                        py_princes, py_subgroups, NULL);
    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::empty_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    CHECK_PY_CREATE(dcb, "deferred callback", goto done);
    CHECK_PY_CREATE(edcb, "deferred callback", goto done);

    result = DeferredCallback::add_callbacks(py_ret, dcb, edcb);

done:
    Py_XDECREF(py_gname);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    return result;
}

#endif

bool
DirectoryManager::add_switch(const SwitchInfo& switch_info, const std::string& dir,
                             const SwitchCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
// TO UNCOMMENT - implement ::to_python(SwitchInfo)
//     static const char *method_name = "add_principal";
//     static PyObject *method = PyString_FromString(method_name);
//     CHECK_PY_CREATE(method, method_name,return false);

//     PyObject *pyswitch = ::to_python(switch_info);
//     CHECK_PY_CREATE(pyswitch, "SwitchInfo",return false);
//     bool result = call_method(method_name, 
//                               Directory::SWITCH_PRINCIPAL, method,
//                               pyswitch, dir,
//                               boost::bind(&DirectoryManager::add_switch_cb,
//                                           this, _1, cb),
//                               boost::bind(&DirectoryManager::errback,
//                                           this, _1, method_name, ecb));
//     Py_DECREF(pyswitch);
//     return result;
    return false;
#else
    return false;
#endif
}

void
DirectoryManager::add_switch_cb(PyObject *pyswitch, const SwitchCb& cb)
{
#ifdef TWISTED_ENABLED
    SwitchInfo si = from_python<SwitchInfo>(pyswitch);
    cb(si);
#endif
}


bool
DirectoryManager::search_switches(const SwitchInfo& switch_info,
                                  const hash_set<std::string>& set_params,
                                  const std::string& dir,
                                  const SearchCb& cb,
                                  const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *type_name = "switch principal";
    static PyObject *type = ::to_python(int(Directory::SWITCH_PRINCIPAL));
    CHECK_PY_CREATE(type, type_name, return false);

    PyObject *query = PyDict_New();
    PyObject *value;
    CHECK_PY_CREATE(query, "Query dict", return false);
    hash_set<std::string>::const_iterator found;
    if ((found = set_params.find("name")) != set_params.end()) {
        value = ::to_python(switch_info.name);
        CHECK_PY_CREATE_FOR_DICT(value, query, "name", return false);
    }
    if ((found = set_params.find("dpid")) != set_params.end()) {
        value = to_datapathid(switch_info.dpid.as_host());
        CHECK_PY_CREATE_FOR_DICT(value, query, "dpid", return false);
    }

    bool result = call_search_principals(type, query, dir, cb, ecb);
    Py_DECREF(query);
    return result;
#else
    return false;
#endif
}


bool
DirectoryManager::search_locations(const LocationInfo& location_info,
                                   const hash_set<std::string>& set_params,
                                   const std::string& dir,
                                   const SearchCb& cb,
                                   const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *type_name = "location principal";
    static PyObject *type = ::to_python(int(Directory::LOCATION_PRINCIPAL));
    CHECK_PY_CREATE(type, type_name, return false);

    PyObject *query = PyDict_New();
    PyObject *value;
    CHECK_PY_CREATE(query, "Query dict", return false);
    hash_set<std::string>::const_iterator found;
    if ((found = set_params.find("name")) != set_params.end()) {
        value = ::to_python(location_info.name);
        CHECK_PY_CREATE_FOR_DICT(value, query, "name", return false);
    }
    if ((found = set_params.find("dpid")) != set_params.end()) {
        value = to_datapathid(location_info.dpid.as_host());
        CHECK_PY_CREATE_FOR_DICT(value, query, "dpid", return false);
    }
    if ((found = set_params.find("port")) != set_params.end()) {
        value = ::to_python(location_info.port);
        CHECK_PY_CREATE_FOR_DICT(value, query, "port", return false);
    }

    bool result = call_search_principals(type, query, dir, cb, ecb);
    Py_DECREF(query);
    return result;
#else
    return false;
#endif
}


bool
DirectoryManager::search_hosts(const HostInfo& host_info,
                               const hash_set<std::string>& set_params,
                               const std::string& dir,
                               const SearchCb& cb,
                               const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *type_name = "host principal";
    static PyObject *type = ::to_python(int(Directory::HOST_PRINCIPAL));
    CHECK_PY_CREATE(type, type_name, return false);

    PyObject *query = PyDict_New();
    PyObject *value;
    CHECK_PY_CREATE(query, "Query dict", return false);
    hash_set<std::string>::const_iterator found;
    if ((found = set_params.find("name")) != set_params.end()) {
        value = ::to_python(host_info.name);
        CHECK_PY_CREATE_FOR_DICT(value, query, "name", return false);
    }
    if ((found = set_params.find("alias")) != set_params.end()) {
        if (host_info.aliases.empty()) {
            VLOG_ERR(lg, "alias cannot be query key if aliases vector empty");
            Py_DECREF(query);
            return false;
        }
        value = ::to_python(host_info.aliases[0]);
        CHECK_PY_CREATE_FOR_DICT(value, query, "alias", return false);
    }
    if ((found = set_params.find("dpid")) != set_params.end()) {
        if (host_info.netinfos.empty()) {
            VLOG_ERR(lg, "dpid cannot be query key if netinfos vector empty");
            Py_DECREF(query);
            return false;
        }
        value = to_datapathid(host_info.netinfos[0].dpid.as_host());
        CHECK_PY_CREATE_FOR_DICT(value, query, "dpid", return false);
    }
    if ((found = set_params.find("port")) != set_params.end()) {
        if (host_info.netinfos.empty()) {
            VLOG_ERR(lg, "port cannot be query key if netinfos vector empty");
            Py_DECREF(query);
            return false;
        }
        value = ::to_python(host_info.netinfos[0].port);
        CHECK_PY_CREATE_FOR_DICT(value, query, "port", return false);
    }
    if ((found = set_params.find("dladdr")) != set_params.end()) {
        if (host_info.netinfos.empty()) {
            VLOG_ERR(lg, "dladdr cannot be query key if netinfos vector empty");
            Py_DECREF(query);
            return false;
        }
        value = to_ethernetaddr(host_info.netinfos[0].dladdr.hb_long());
        CHECK_PY_CREATE_FOR_DICT(value, query, "dladdr", return false);
    }
    if ((found = set_params.find("nwaddr")) != set_params.end()) {
        if (host_info.netinfos.empty()) {
            VLOG_ERR(lg, "nwaddr cannot be query key if netinfos vector empty");
            Py_DECREF(query);
            return false;
        }
        value = ::to_python(host_info.netinfos[0].nwaddr);
        CHECK_PY_CREATE_FOR_DICT(value, query, "nwaddr", return false);
    }

    bool result = call_search_principals(type, query, dir, cb, ecb);
    Py_DECREF(query);
    return result;
#else
    return false;
#endif
}


bool
DirectoryManager::search_users(const UserInfo& user_info,
                               const hash_set<std::string>& set_params,
                               const std::string& dir,
                               const SearchCb& cb,
                               const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *type_name = "user principal";
    static PyObject *type = ::to_python(int(Directory::USER_PRINCIPAL));
    CHECK_PY_CREATE(type, type_name, return false);

    PyObject *query = PyDict_New();
    PyObject *value;
    CHECK_PY_CREATE(query, "Query dict", return false);
    hash_set<std::string>::const_iterator found;
    if ((found = set_params.find("name")) != set_params.end()) {
        value = ::to_python(user_info.name);
        CHECK_PY_CREATE_FOR_DICT(value, query, "name", return false);
    }
    if ((found = set_params.find("user_id")) != set_params.end()) {
        value = ::to_python(user_info.user_id);
        CHECK_PY_CREATE_FOR_DICT(value, query, "user_id", return false);
    }
    if ((found = set_params.find("user_real_name")) != set_params.end()) {
        value = ::to_python(user_info.user_real_name);
        CHECK_PY_CREATE_FOR_DICT(value, query, "user_real_name", return false);
    }
    if ((found = set_params.find("description")) != set_params.end()) {
        value = ::to_python(user_info.description);
        CHECK_PY_CREATE_FOR_DICT(value, query, "description", return false);
    }
    if ((found = set_params.find("location")) != set_params.end()) {
        value = ::to_python(user_info.location);
        CHECK_PY_CREATE_FOR_DICT(value, query, "location", return false);
    }
    if ((found = set_params.find("phone")) != set_params.end()) {
        value = ::to_python(user_info.phone);
        CHECK_PY_CREATE_FOR_DICT(value, query, "phone", return false);
    }
    if ((found = set_params.find("user_email")) != set_params.end()) {
        value = ::to_python(user_info.user_email);
        CHECK_PY_CREATE_FOR_DICT(value, query, "user_email", return false);
    }

    bool result = call_search_principals(type, query, dir, cb, ecb);
    Py_DECREF(query);
    return result;
#else
    return false;
#endif
}


void
DirectoryManager::search_cb(PyObject *matches, const SearchCb& cb)
{
#ifdef TWISTED_ENABLED
    uint32_t n = PyList_GET_SIZE(matches);
    std::vector<std::string> names(n);
    for (uint32_t i = 0; i < n; ++i) {
        PyObject *name = PyList_GET_ITEM(matches, i);
        names[i] = from_python<std::string>(name);
    }
    cb(names);
#endif
}


void
DirectoryManager::string_cb(PyObject *str, const StringCb& cb)
{
#ifdef TWISTED_ENABLED
    std::string s = from_python<std::string>(str);
    cb(s);
#endif
}

void
DirectoryManager::empty_cb(PyObject *ret, const EmptyCb& cb)
{
#ifdef TWISTED_ENABLED
    cb();
#endif
}

bool
DirectoryManager::search_groups(Directory::Group_Type gtype,
                                const std::string& principal,
                                const std::string& dir,
                                bool include_global,
                                const SearchCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(gtype);
    CHECK_PY_CREATE(py_gtype, "Directory group type", return false);

    PyObject *py_name = ::to_python(principal);
    CHECK_PY_CREATE(py_name, "principal name", return false);
    bool result = call_group_method(py_gtype, py_name, dir,
                                    include_global, cb, ecb);
    Py_DECREF(py_name);
    return result;
#else
    return false;
#endif
}

bool
DirectoryManager::search_switch_groups(const std::string& switch_name,
                                       const std::string& dir,
                                       bool include_global,
                                       const SearchCb& cb, const ErrorCb& ecb)
{
    return search_groups(Directory::SWITCH_PRINCIPAL_GROUP, switch_name,
                         dir, include_global, cb, ecb);
}

bool
DirectoryManager::search_location_groups(const std::string& location,
                                         const std::string& dir,
                                         bool include_global,
                                         const SearchCb& cb, const ErrorCb& ecb)
{
    return search_groups(Directory::LOCATION_PRINCIPAL_GROUP, location,
                         dir, include_global, cb, ecb);
}


bool
DirectoryManager::search_host_groups(const std::string& hostname,
                                     const std::string& dir,
                                     bool include_global,
                                     const SearchCb& cb, const ErrorCb& ecb)
{
    return search_groups(Directory::HOST_PRINCIPAL_GROUP, hostname,
                         dir, include_global, cb, ecb);
}


bool
DirectoryManager::search_user_groups(const std::string& username,
                                     const std::string& dir,
                                     bool include_global,
                                     const SearchCb& cb, const ErrorCb& ecb)
{
    return search_groups(Directory::USER_PRINCIPAL_GROUP, username,
                         dir, include_global, cb, ecb);
}


bool
DirectoryManager::search_dladdr_groups(const ethernetaddr& dladdr,
                                       const std::string& dir,
                                       bool include_global,
                                       const SearchCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(Directory::DLADDR_GROUP);
    CHECK_PY_CREATE(py_gtype, "dladdr group type", return false);

    PyObject *py_dladdr = to_ethernetaddr(dladdr.hb_long());
    CHECK_PY_CREATE(py_dladdr, "Ethernet address", return false);
    bool result =  call_group_method(py_gtype, py_dladdr, dir,
                                     include_global, cb, ecb);
    Py_DECREF(py_dladdr);
    return result;
#else
    return false;
#endif
}


bool
DirectoryManager::search_nwaddr_groups(uint32_t nwaddr,
                                       const std::string& dir,
                                       bool include_global,
                                       const SearchCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(Directory::NWADDR_GROUP);
    CHECK_PY_CREATE(py_gtype, "nwaddr group type", return false);

    PyObject *py_nwaddr = to_cidr(nwaddr);
    CHECK_PY_CREATE(py_nwaddr, "CIDR IP address", return false);
    bool result =  call_group_method(py_gtype, py_nwaddr, dir,
                                     include_global, cb, ecb);
    Py_DECREF(py_nwaddr);
    return result;
#else
    return false;
#endif
}

bool
DirectoryManager::modify_group(Directory::Group_Type gtype,
                               const std::string& group_name,
                               const std::vector<std::string>& principals,
                               const std::vector<std::string>& subgroups,
                               bool add_members, const EmptyCb& cb,
                               const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }

    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(gtype);
    CHECK_PY_CREATE(py_gtype, "Directory group type", return false);

    PyObject *py_princes = 0, *py_subgroups = 0;

    py_princes = ::to_python_list(principals);
    CHECK_PY_CREATE(py_princes, "principal list", goto done);

    py_subgroups = ::to_python_list(subgroups);
    CHECK_PY_CREATE(py_subgroups, "subgroup list", goto done);

    ret = call_modify_group(group_name, py_gtype, py_princes, py_subgroups,
                            add_members, cb, ecb);

done:
    Py_XDECREF(py_princes);
    Py_XDECREF(py_subgroups);

#endif
    return ret;
}

bool
DirectoryManager::modify_switch_group(const std::string& group_name,
                                      const std::vector<std::string>& principals,
                                      const std::vector<std::string>& subgroups,
                                      bool add_members, const EmptyCb& cb,
                                      const ErrorCb& ecb)
{
    return modify_group(Directory::SWITCH_PRINCIPAL_GROUP, group_name,
                        principals, subgroups, add_members, cb, ecb);
}

bool
DirectoryManager::modify_location_group(const std::string& group_name,
                                        const std::vector<std::string>& principals,
                                        const std::vector<std::string>& subgroups,
                                        bool add_members, const EmptyCb& cb,
                                        const ErrorCb& ecb)
{
    return modify_group(Directory::LOCATION_PRINCIPAL_GROUP, group_name,
                        principals, subgroups, add_members, cb, ecb);
}

bool
DirectoryManager::modify_host_group(const std::string& group_name,
                                    const std::vector<std::string>& principals,
                                    const std::vector<std::string>& subgroups,
                                    bool add_members, const EmptyCb& cb,
                                    const ErrorCb& ecb)
{
    return modify_group(Directory::HOST_PRINCIPAL_GROUP, group_name,
                        principals, subgroups, add_members, cb, ecb);
}

bool
DirectoryManager::modify_user_group(const std::string& group_name,
                                      const std::vector<std::string>& principals,
                                      const std::vector<std::string>& subgroups,
                                      bool add_members, const EmptyCb& cb,
                                      const ErrorCb& ecb)
{
    return modify_group(Directory::USER_PRINCIPAL_GROUP, group_name,
                        principals, subgroups, add_members, cb, ecb);
}

bool
DirectoryManager::modify_dladdr_group(const std::string& group_name,
                                      const std::vector<ethernetaddr>& principals,
                                      const std::vector<std::string>& subgroups,
                                      bool add_members, const EmptyCb& cb,
                                      const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(Directory::DLADDR_GROUP);
    CHECK_PY_CREATE(py_gtype, "dladdr group type", return false);

    PyObject *py_princes = 0, *py_subgroups = 0;
    uint32_t i = 0;

    py_princes = PyList_New(principals.size());
    CHECK_PY_CREATE(py_princes, "principal list", goto done);

    for (std::vector<ethernetaddr>::const_iterator iter = principals.begin();
         iter != principals.end(); ++iter)
    {
        PyObject *py_dladdr = to_ethernetaddr(iter->hb_long());
        CHECK_PY_CREATE(py_dladdr, "Ethernet address", goto done);
        if (PyList_SetItem(py_princes, i++, py_dladdr) != 0) {
            VLOG_ERR(lg, "Cannot set %uth entry in dladdr list.", i);
            Py_DECREF(py_dladdr);
            goto done;
        }
    }

    py_subgroups = ::to_python_list(subgroups);
    CHECK_PY_CREATE(py_subgroups, "subgroup list", goto done);

    ret = call_modify_group(group_name, py_gtype, py_princes, py_subgroups,
                            add_members, cb, ecb);
done:
    Py_XDECREF(py_princes);
    Py_XDECREF(py_subgroups);
#endif
    return ret;
}

bool
DirectoryManager::modify_nwaddr_group(const std::string& group_name,
                                      const std::vector<uint32_t>& principals,
                                      const std::vector<std::string>& subgroups,
                                      bool add_members, const EmptyCb& cb,
                                      const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    // statically allocated - should not decref
    PyObject *py_gtype = get_py_gtype(Directory::NWADDR_GROUP);
    CHECK_PY_CREATE(py_gtype, "nwaddr group type", return false);

    PyObject *py_princes = 0, *py_subgroups = 0;
    uint32_t i = 0;

    py_princes = PyList_New(principals.size());
    CHECK_PY_CREATE(py_princes, "principal list", goto done);

    for (std::vector<uint32_t>::const_iterator iter = principals.begin();
         iter != principals.end(); ++iter)
    {
        PyObject *py_nwaddr = to_cidr(*iter);
        CHECK_PY_CREATE(py_nwaddr, "CIDR IP address", goto done);
        if (PyList_SetItem(py_princes, i++, py_nwaddr) != 0) {
            VLOG_ERR(lg, "Cannot set %uth entry in nwaddr list.", i);
            Py_DECREF(py_nwaddr);
            goto done;
        }
    }

    py_subgroups = ::to_python_list(subgroups);
    CHECK_PY_CREATE(py_subgroups, "subgroup list", goto done);

    ret = call_modify_group(group_name, py_gtype, py_princes, py_subgroups,
                            add_members, cb, ecb);
done:
    Py_XDECREF(py_princes);
    Py_XDECREF(py_subgroups);
#endif
    return ret;
}

bool
DirectoryManager::is_gateway(const ethernetaddr& dladdr, const std::string& dir,
                             const BoolCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *method_name = "is_gateway";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);

    PyObject *pyaddr = to_ethernetaddr(dladdr.hb_long());
    CHECK_PY_CREATE(pyaddr, "Ethernet address", return false);
    bool result = call_method(method_name, method, pyaddr, dir,
                              boost::bind(&DirectoryManager::bool_cb,
                                          this, _1, cb),
                              boost::bind(&DirectoryManager::errback,
                                          this, _1, method_name, ecb));
    Py_DECREF(pyaddr);
    return result;
#else
    return false;
#endif
}


bool
DirectoryManager::is_router(const ethernetaddr& dladdr, const std::string& dir,
                            const BoolCb& cb, const ErrorCb& ecb)
{
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *method_name = "is_router";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);

    PyObject *pyaddr = to_ethernetaddr(dladdr.hb_long());
    CHECK_PY_CREATE(pyaddr, "Ethernet address", return false);
    bool result = call_method(method_name, method, pyaddr, dir,
                              boost::bind(&DirectoryManager::bool_cb,
                                          this, _1, cb),
                              boost::bind(&DirectoryManager::errback,
                                          this, _1, method_name, ecb));
    Py_DECREF(pyaddr);
    return result;
#else
    return false;
#endif
}

void
DirectoryManager::bool_cb(PyObject *ret, const BoolCb& cb)
{
#ifdef TWISTED_ENABLED
    bool result = from_python<bool>(ret);
    cb(result);
#endif
}

// note: this will only work for 'cred_type' = Directory::AUTHORIZED_CERT_FP
// as only the CertFingerprintCredential object is implemented in C++
bool DirectoryManager::get_certfp_credential(Directory::Principal_Type ptype,
                                             const std::string mangled_principal_name,
                                             const CredentialCb& cb, const ErrorCb& ecb)
{
  #ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return false;
    }
    static const char *method_name = "get_credentials";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return false);
    PyObject *principal_type = ::to_python(int(ptype));
    CHECK_PY_CREATE(principal_type,"principal type", return false);
    PyObject *principal_name = ::to_python(mangled_principal_name);
    CHECK_PY_CREATE(principal_name,"principal name", return false);
    PyObject *credential_type = ::to_python(Directory::AUTHORIZED_CERT_FP);
    PyObject *ret = PyObject_CallMethodObjArgs(dm, method, principal_type,
                                               principal_name,credential_type, NULL);
    CHECK_PY_RETURN(ret, method_name, return false);

    PyObject *dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::credentials_cb, this, _1, cb));
    PyObject *edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));
    bool result = false;
    if (dcb == NULL || edcb == NULL) {
        VLOG_ERR(lg, "Could not create callbacks.");
    } else {
        result = DeferredCallback::add_callbacks(ret, dcb, edcb);
    }

    Py_DECREF(ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
    Py_XDECREF(principal_type);
    Py_XDECREF(principal_name);
    Py_XDECREF(credential_type);

    return result;
#else
    return false;
#endif

}

void
DirectoryManager::credentials_cb(PyObject *cred_list,
                                 const CredentialCb& cb)
{
#ifdef TWISTED_ENABLED
    uint32_t n = 0;
    if(!PyList_Check(cred_list)) {
      lg.err("credentials_cb received values that was not a list\n");
    } else {
      n = PyList_Size(cred_list);
    }
    std::vector< CertFingerprintCredential > creds(n);
    for (uint32_t i = 0; i < n; ++i) {
        PyObject *cred = PyList_GetItem(cred_list, i);
        creds[i] = from_python<CertFingerprintCredential>(cred);
    }
    cb(creds);
#endif
}



std::string
DirectoryManager::add_discovered_switch(const datapathid &dpid)
{
    std::string ret_str;

#ifdef TWISTED_ENABLED
    PyObject *py_dpid = NULL, *ret = NULL;

    if (dm == NULL) {
        goto done;
    }
    static const char *method_name = "add_discovered_switch";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, return ret_str);

    py_dpid = to_datapathid(dpid.as_host());
    if (!py_dpid) {
        goto done;
    }

    ret = PyObject_CallMethodObjArgs(dm, method, py_dpid, NULL);
    if (!ret) {
        const string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call %s Python function: %s", method_name,
                 exc.c_str());
        goto done;
    }
    ret_str = from_python<std::string>(ret);

done:
    Py_XDECREF(py_dpid);
    Py_XDECREF(ret);

#endif
    return ret_str;
}

bool
DirectoryManager::get_discovered_host_name(const ethernetaddr &dladdr,
                                           uint32_t nwaddr, bool dlname,
                                           bool ensure_in_dir,
                                           const StringCb& cb,
                                           const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
      return ret;
    }

    PyObject *py_dladdr = 0, *py_nwaddr = 0, *py_ensure_in_dir = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    static const char *method_name = "get_discovered_host_name";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, goto done);

    if (dlname) {
        py_dladdr = to_ethernetaddr(dladdr.hb_long());
        CHECK_PY_CREATE(py_dladdr, "dladdr", goto done);
        py_nwaddr = Py_None;
        Py_INCREF(py_nwaddr);
    } else {
        py_dladdr = Py_None;
        Py_INCREF(py_dladdr);
        py_nwaddr = ::to_python(nwaddr);
        CHECK_PY_CREATE(py_nwaddr, "nwaddr", goto done);
    }

    py_ensure_in_dir = ::to_python(ensure_in_dir);
    CHECK_PY_CREATE(py_ensure_in_dir, "ensure_in_dir", goto done);

    py_ret = PyObject_CallMethodObjArgs(dm, method, py_dladdr, py_nwaddr,
                                       py_ensure_in_dir, NULL);
    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::string_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    if (dcb == NULL || edcb == NULL) {
        VLOG_ERR(lg, "Could not create callbacks.");
    } else {
        ret = DeferredCallback::add_callbacks(py_ret, dcb, edcb);
    }

done:
    Py_XDECREF(py_dladdr);
    Py_XDECREF(py_nwaddr);
    Py_XDECREF(py_ensure_in_dir);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
#endif
    return ret;
}


bool
DirectoryManager::get_discovered_switch_name(const datapathid &dpid,
                                             bool ensure_in_dir,
                                             const StringCb& cb,
                                             const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
        return ret;
    }

    PyObject *py_dpid = 0, *py_ensure_in_dir = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    static const char *method_name = "get_discovered_switch_name";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, goto done);

    py_dpid = to_datapathid(dpid.as_host());
    CHECK_PY_CREATE(py_dpid, "dpid", goto done);
    py_ensure_in_dir = ::to_python(ensure_in_dir);
    CHECK_PY_CREATE(py_ensure_in_dir, "ensure_in_dir", goto done);

    py_ret = PyObject_CallMethodObjArgs(dm, method, py_dpid,
                                       py_ensure_in_dir, NULL);
    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::string_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    if (dcb == NULL || edcb == NULL) {
        VLOG_ERR(lg, "Could not create callbacks.");
    } else {
        ret = DeferredCallback::add_callbacks(py_ret, dcb, edcb);
    }

done:
    Py_XDECREF(py_dpid);
    Py_XDECREF(py_ensure_in_dir);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);
#endif
    return ret;
}

bool
DirectoryManager::get_discovered_location_name(const std::string& switch_name,
                                               const std::string& port_name,
                                               const datapathid &dpid,
                                               uint16_t port_num,
                                               bool ensure_in_dir,
                                               const StringCb& cb,
                                               const ErrorCb& ecb)
{
    bool ret = false;
#ifdef TWISTED_ENABLED
    if (dm == NULL) {
      return ret;
    }

    PyObject *py_switch_name = 0, *py_port_name = 0, *py_dpid = 0,
        *py_port_num = 0, *py_ensure_in_dir = 0, *py_ret = 0;
    PyObject *dcb = 0, *edcb = 0;

    static const char *method_name = "get_discovered_location_name";
    static PyObject *method = PyString_FromString(method_name);
    CHECK_PY_CREATE(method, method_name, goto done);

    py_switch_name = ::to_python(switch_name);
    CHECK_PY_CREATE(py_switch_name, "switch_name", goto done);
    py_port_name = ::to_python(port_name);
    CHECK_PY_CREATE(py_port_name, "port_name", goto done);
    py_dpid = to_datapathid(dpid.as_host());
    CHECK_PY_CREATE(py_dpid, "dpid", goto done);
    py_port_num = ::to_python(port_num);
    CHECK_PY_CREATE(py_port_num, "port_number", goto done);
    py_ensure_in_dir = ::to_python(ensure_in_dir);
    CHECK_PY_CREATE(py_ensure_in_dir, "ensure_in_dir", goto done);

    py_ret = PyObject_CallMethodObjArgs(dm, method, py_switch_name,
                                       py_port_name, py_dpid, py_port_num,
                                       py_ensure_in_dir, NULL);
    CHECK_PY_RETURN(py_ret, method_name, goto done);

    dcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::string_cb, this, _1, cb));
    edcb = DeferredCallback::get_instance(
        boost::bind(&DirectoryManager::errback, this, _1, method_name, ecb));

    if (dcb == NULL || edcb == NULL) {
        VLOG_ERR(lg, "Could not create callbacks.");
    } else {
        ret = DeferredCallback::add_callbacks(py_ret, dcb, edcb);
    }

done:
    Py_XDECREF(py_switch_name);
    Py_XDECREF(py_port_name);
    Py_XDECREF(py_dpid);
    Py_XDECREF(py_port_num);
    Py_XDECREF(py_ensure_in_dir);
    Py_XDECREF(py_ret);
    Py_XDECREF(dcb);
    Py_XDECREF(edcb);

#endif
    return ret;
}


}
}

REGISTER_COMPONENT(vigil::container::Simple_component_factory<vigil::applications::DirectoryManager>,
                   vigil::applications::DirectoryManager);
