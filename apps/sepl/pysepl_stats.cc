/* Copyright 2008 (C) Nicira, Inc. */
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
#include "pysepl_stats.hh"

#include "swigpyrun.h"
#include "pyrt/pycontext.hh"

namespace vigil {
namespace applications {

PySepl_stats::PySepl_stats(PyObject* ctxt)
    : stats(0)
{
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void
PySepl_stats::configure(PyObject* configuration) {
    c->resolve(stats);
}

void
PySepl_stats::set_record_rule_senders(uint32_t id, bool record)
{
    stats->set_record_rule_senders(id, record);
}

PyRuleStatsEntry
PySepl_stats::get_rule_stats(uint32_t id)
{
    Sepl_stats::RuleStatsEntry entry;
    stats->get_rule_stats(id, entry);

    PyRuleStatsEntry stats;
    stats.count = entry.count;
    stats.record_senders = entry.record_senders;
    stats.sender_macs.assign(entry.sender_macs.begin(), entry.sender_macs.end());
    return stats;
}

void
PySepl_stats::remove_entry(uint32_t id)
{
    stats->remove_entry(id);
}

void
PySepl_stats::clear_stats()
{
    stats->clear_stats();
}

void
PySepl_stats::increment_allows()
{
    stats->increment_allows();
}

uint64_t
PySepl_stats::get_allows()
{
    return stats->get_allows();
}

void
PySepl_stats::clear_allows()
{
    stats->clear_allows();
}

void
PySepl_stats::increment_denies()
{
    stats->increment_denies();
}

uint64_t
PySepl_stats::get_denies()
{
    return stats->get_denies();
}

void
PySepl_stats::clear_denies()
{
    stats->clear_denies();
}

}
}
