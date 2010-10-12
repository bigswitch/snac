/*
 * Copyright 2008 (C) Nicira, Inc.
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
#include "pyprincipal_types.hh"
#include "pyrt/pyglue.hh"

using namespace std;
using namespace vigil;

namespace vigil {
namespace applications {
namespace directory {

//TODO: create generic std::set -> python tuple/list/set in pyglue
template<>
PyObject* to_python(const AuthSupportSet& supp) {
    PyObject* ret = PyTuple_New(supp.size());
    std::set<std::string>::iterator supp_iter;
    int i = 0;
    for (supp_iter = supp.begin(); supp_iter != supp.end(); supp_iter++) {
        PyTuple_SetItem(ret, i++, ::to_python(*supp_iter));
    }
    return ret;
}

template<>
PyObject* to_python(const PrincipalSupportMap& sm) {
    PyObject* ret = PyDict_New();
    BOOST_FOREACH(PrincipalSupportMap::value_type v, sm) {
        PyDict_SetItem(ret, to_python(v.first), ::to_python(v.second));
    }
    return ret;
}

template<>
PyObject* to_python(const GroupSupportMap& sm) {
    PyObject* ret = PyDict_New();
    BOOST_FOREACH(GroupSupportMap::value_type v, sm) {
        PyDict_SetItem(ret, to_python(v.first), ::to_python(v.second));
    }
    return ret;
}

template<>
PyObject* to_python(const AuthResult& result) {
    Co_critical_section c;
    static PyObject* dir_mod = PyImport_ImportModule("nox.lib.directory");
    //TODO: clean up dup check code
    if (!dir_mod) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot import python directory module:\n"+msg);
    }
    static PyObject* ar = PyObject_GetAttrString(dir_mod, "AuthResult");
    if (!ar) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot locate python AuthResult class:\n"+msg);
    }

    PyObject* args = PyTuple_New(3);
    PyTuple_SetItem(args, 0, to_python(result.status));
    PyTuple_SetItem(args, 1, ::to_python(result.username));
    PyTuple_SetItem(args, 2, to_python(result.groups));
    PyObject* ari = PyInstance_New(ar, args, NULL);
    Py_XDECREF(args);
    if (!ari) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot instantiate AuthResult class:\n"+msg);
    }
    return ari;
}

/*
 * We dispatch the to_python here (instead of making them class methods)
 * as a temporary workaround; in the future, Python should reference the C 
 * principal types and Python access will be done via swig.
 */
template<>
PyObject* to_python(const PrincipalInfo& pi) {
    switch (pi.type) {
        case SWITCH_PRINCIPAL:
            return to_python((const SwitchInfo&)pi);
        case LOCATION_PRINCIPAL:
            return to_python((const LocationInfo&)pi);
        case HOST_PRINCIPAL:
            return to_python((const HostInfo&)pi);
        case USER_PRINCIPAL:
            return to_python((const UserInfo&)pi);
        default:
            break;
    }
    Py_RETURN_NONE;
}

template<>
PyObject* to_python(const SwitchInfo& pi) {
    /*
     * Workaround to instantiate Python SwitchInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    Py_RETURN_NONE; //TODO
}

template<>
PyObject* to_python(const LocationInfo& pi) {
    /*
     * Workaround to instantiate Python LocationInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    Py_RETURN_NONE; //TODO
}

template<>
PyObject* to_python(const NetInfo& pi) {
    /*
     * Workaround to instantiate Python NetInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    Py_RETURN_NONE; //TODO
}

template<>
PyObject* to_python(const HostInfo& pi) {
    /*
     * Workaround to instantiate Python HostInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    Py_RETURN_NONE; //TODO
}

template<>
PyObject* to_python(const UserInfo& pi) {
    /*
     * Workaround to instantiate Python UserInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    static PyObject* dir_mod = PyImport_ImportModule("nox.lib.directory");
    //TODO: clean up dup check code
    if (!dir_mod) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot import python directory module:\n"+msg);
    }
    static PyObject* ui = PyObject_GetAttrString(dir_mod, "UserInfo");
    if (!ui) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot locate python UserInfo class:\n"+msg);
    }

    PyObject* args = PyTuple_New(7);
    PyTuple_SetItem(args, 0, ::to_python(pi.name));
    PyTuple_SetItem(args, 1, ::to_python(pi.user_id));
    PyTuple_SetItem(args, 2, ::to_python(pi.user_real_name));
    PyTuple_SetItem(args, 3, ::to_python(pi.description));
    PyTuple_SetItem(args, 4, ::to_python(pi.location));
    PyTuple_SetItem(args, 5, ::to_python(pi.phone));
    PyTuple_SetItem(args, 6, ::to_python(pi.user_email));
    PyObject* uii = PyInstance_New(ui, args, NULL);
    Py_XDECREF(args);
    if (!uii) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot instantiate UserInfo class:\n"+msg);
    }
    return uii;
}

template<>
PyObject* to_python(const GroupInfo& gi) {
    /*
     * Workaround to instantiate Python UserInfo object until Python
     * directories are refactored to use swigged C objects
     */
    Co_critical_section c;
    static PyObject* dir_mod = PyImport_ImportModule("nox.lib.directory");
    //TODO: clean up dup check code
    if (!dir_mod) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot import python directory module:\n"+msg);
    }
    static PyObject* pgi = PyObject_GetAttrString(dir_mod, "GroupInfo");
    if (!pgi) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot locate python UserInfo class:\n"+msg);
    }

    PyObject* args = PyTuple_New(4);
    PyTuple_SetItem(args, 0, ::to_python(gi.name));
    PyTuple_SetItem(args, 1, ::to_python(gi.description));
    PyTuple_SetItem(args, 2, to_python(gi.members));
    PyTuple_SetItem(args, 3, to_python(gi.subgroups));
    PyObject* pgii = PyInstance_New(pgi, args, NULL);
    Py_XDECREF(args);
    if (!pgii) {
        const string msg = pretty_print_python_exception();
        throw runtime_error("cannot instantiate GroupInfo class:\n"+msg);
    }
    return pgii;
}


} /* directory */
} /* applications */
} /* vigil */

