/* Copyright 2008 (C) Nicira, Inc. */
%module "nox.ext.apps.failover.pyreplicator"

%{
#include "pyreplicator.cc"
%}

%include "std_string.i"

class PyStorage_replicator {
public:
    PyStorage_replicator(PyObject*);
    PyObject* snapshot(const std::string&, bool, PyObject* cb);
};


