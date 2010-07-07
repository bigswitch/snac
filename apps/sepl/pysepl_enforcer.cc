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
#include "pysepl_enforcer.hh"

#include "swigpyrun.h"
#include "pyrt/pycontext.hh"

namespace vigil {
namespace applications {

PySepl_enforcer::PySepl_enforcer(PyObject* ctxt)
    : enforcer(0)
{
    PySwigObject* swigo = SWIG_Python_GetSwigThis(ctxt);
    if (!swigo || !swigo->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)swigo->ptr)->c;
}

void
PySepl_enforcer::configure(PyObject* configuration) {
    c->resolve(enforcer);
}

void
PySepl_enforcer::set_most_secure(bool most_secure)
{
    enforcer->set_most_secure(most_secure);
}

uint32_t
PySepl_enforcer::add_rule(uint32_t priority, const Flow_expr& expr,
                          const Flow_action& action)
{
    return enforcer->add_rule(priority, expr, action);
}

void
PySepl_enforcer::build() {
    enforcer->build();
    //enforcer->print();
}

bool
PySepl_enforcer::change_rule_priority(uint32_t id, uint32_t priority) {
    return enforcer->change_rule_priority(id, priority);
}

bool
PySepl_enforcer::delete_rule(uint32_t id) {
    return enforcer->delete_rule(id);
}

void
PySepl_enforcer::reset() {
    enforcer->reset();
}

}
}
