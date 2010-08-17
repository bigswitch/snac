/* Copyright 2008 (C) Nicira, Inc. */
#ifndef PYSEPL_ENFORCER_GLUE_HH
#define PYSEPL_ENFORCER_GLUE_HH 1

#include <Python.h>

#include "component.hh"
#include "sepl_enforcer.hh"

/*
 * Proxy Sepl_enforcer "component" to initialize enforcer from Python and
 * add/remove rules.
 */
namespace vigil {
namespace applications {

class PySepl_enforcer {
public:
    PySepl_enforcer(PyObject* ctxt);

    void configure(PyObject*);

    void set_most_secure(bool most_secure);
    uint32_t add_rule(uint32_t priority, const Flow_expr&,
                      const Flow_action&);
    void build();
    bool change_rule_priority(uint32_t id, uint32_t priority);
    bool delete_rule(uint32_t id);
    void reset();

private:
    Sepl_enforcer* enforcer;
    container::Component* c;
};

}
}

#endif
