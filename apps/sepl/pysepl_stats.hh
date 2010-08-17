/* Copyright 2008 (C) Nicira, Inc. */

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
