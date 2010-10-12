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
#ifndef CONTROLLER_PYDIRGLUE_HH
#define CONTROLLER_PYDIRGLUE_HH 1

#include "directorymanager.hh"

namespace vigil {
namespace applications {

class PyDirectoryManager {
public:
    PyDirectoryManager(PyObject*);

    void configure(PyObject*);
    void install();

    bool set_py_dm(PyObject *);
    bool set_create_dp(PyObject *);
    bool set_create_eth(PyObject *);
    bool set_create_ip(PyObject *);
    bool set_create_cidr(PyObject *);
    bool set_create_cred(PyObject *);

private:
    DirectoryManager *dm;
    container::Component *c;
};

}
}

#endif
