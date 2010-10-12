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
#ifndef PYPRINCIPAL_TYPES_HH
#define PYPRINCIPAL_TYPES_HH

#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>

#include <Python.h>

#include "pyrt/pyglue.hh"
#include "principal_types.hh"

namespace vigil {
namespace applications {
namespace directory {

template <typename T>
PyObject* to_python(const T& type);

template <>
PyObject* to_python(const AuthSupportSet&);
template <>
PyObject* to_python(const PrincipalSupportMap&);
template <>
PyObject* to_python(const GroupSupportMap&);

template <>
PyObject* to_python(const AuthResult&);

template<>
inline
PyObject* to_python(const AuthResult::AuthStatus& status) {
    return vigil::to_python(int(status));
}

template<>
inline
PyObject* to_python(const Principal_Type& pt) {
    return vigil::to_python(int(pt));
}

template<>
inline
PyObject* to_python(const Group_Type& gt) {
    return vigil::to_python(int(gt));
} 

template <>
PyObject* to_python(const PrincipalInfo&);
template <>
PyObject* to_python(const SwitchInfo&);
template <>
PyObject* to_python(const LocationInfo&);
template <>
PyObject* to_python(const NetInfo&);
template <>
PyObject* to_python(const HostInfo&);
template <>
PyObject* to_python(const UserInfo&);

//template <>
//PyObject* to_python(const Group_set&);

template <>
PyObject* to_python(const GroupInfo&);

} // namespace directory
} // namespace applications
} // namespace vigil

#endif /* PYPRINCIPAL_TYPES_HH */
