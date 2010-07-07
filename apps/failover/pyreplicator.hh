/* Copyright 2008 (C) Nicira, Inc. */
#ifndef PYREPLICATOR_HH
#define PYREPLICATOR_HH 1

#include <string>

#include <Python.h>

#include "component.hh"
#include "replicator.hh"

namespace vigil {
namespace applications {
namespace replicator {

/* A Python wrapper for the replicator */
class PyStorage_replicator {
public:
    PyStorage_replicator(PyObject* ctxt);
    PyObject* snapshot(const std::string&, bool unique, PyObject* cb);

private:
    Storage_replicator* replicator;
    container::Component* c;
};

} // replicator
} // applications
} // vigil

#endif /* PYREPLICATOR */
