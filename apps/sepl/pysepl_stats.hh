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
#ifndef PYSEPL_STATS_GLUE_HH
#define PYSEPL_STATS_GLUE_HH 1

#include <Python.h>

#include "component.hh"
#include "sepl_stats.hh"

/*
 * Proxy Sepl_stats "component" to retrieve/configure SEPL stats..
 */
namespace vigil {
namespace applications {

struct PyRuleStatsEntry {
    uint32_t count;
    bool record_senders;
    std::list<ethernetaddr> sender_macs;
};

class PySepl_stats {

public:
    PySepl_stats(PyObject* ctxt);

    void configure(PyObject*);
    void set_record_rule_senders(uint32_t, bool);
    PyRuleStatsEntry get_rule_stats(uint32_t);
    void remove_entry(uint32_t);
    void clear_stats();

    void increment_allows();
    uint64_t get_allows();
    void clear_allows();

    void increment_denies();
    uint64_t get_denies();
    void clear_denies();

    // Forces wrap file to reference global ethernetaddr
    ethernetaddr force_swig_to_include_eth() { return ethernetaddr(); }

private:
    Sepl_stats* stats;
    container::Component* c;

};

}
}

#endif
