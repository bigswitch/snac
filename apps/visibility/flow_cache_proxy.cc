/*
 * Copyright 2008 (C) Nicira, Inc.
 */

#include <Python.h>

#include "authenticator/authenticator.hh"
#include <boost/bind.hpp>
#include "flow_cache.hh"
#include "flow_cache_proxy.hh"
#include "pyrt/pycontext.hh"
#include "pyrt/pyglue.hh"
#include "swigpyrun.h"

using namespace std;
using namespace vigil;
using namespace vigil::applications;

namespace vigil {
namespace applications {

static inline PyObject* to_set(std::vector<int64_t> intvec) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(int64_t id, intvec) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}

static inline PyObject* to_set(std::list<int64_t> intlist) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(int64_t id, intlist) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}
static inline PyObject* to_set(std::vector<uint64_t> intvec) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(uint64_t id, intvec) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}

static inline PyObject* to_set(std::list<uint64_t> intlist) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(uint64_t id, intlist) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}

typedef boost::function<bool(uint64_t, Directory::Group_Type&)>
        Group_type_resolver;

static PyObject*
to_python(const Flow_info& fi, Group_type_resolver gtr) {
    PyObject* ret = PyDict_New();
    if (!ret) {
        return 0;
    }

    /* flow info */
    pyglue_setdict_string(ret, "id", ::to_python(fi.id));
    double received = fi.received.tv_sec + (fi.received.tv_usec / 1000000.0); 
    pyglue_setdict_string(ret, "received_ts", ::to_python(received));
    pyglue_setdict_string(ret, "flow", ::to_python(fi.flow));
    pyglue_setdict_string(ret, "dpid", ::to_python(fi.dpid));

    /* bindings info */
    //SNAC0.4: pyglue_setdict_string(ret, "src_users", to_set(fi.src_users));
    //SNAC0.4: pyglue_setdict_string(ret, "src_user_groups", to_set(fi.src_user_groups));
    //SNAC0.4: pyglue_setdict_string(ret, "dst_users", to_set(fi.dst_users));
    //SNAC0.4: pyglue_setdict_string(ret, "dst_user_groups", to_set(fi.dst_user_groups));

    pyglue_setdict_string(ret, "src_host", ::to_python(fi.src_host));
    pyglue_setdict_string(ret, "dst_host", ::to_python(fi.dst_host));

    pyglue_setdict_string(ret, "src_dladdr_groups", to_set(*fi.src_dladdr_groups));
    pyglue_setdict_string(ret, "src_nwaddr_groups", to_set(*fi.src_nwaddr_groups));
    pyglue_setdict_string(ret, "dst_dladdr_groups", to_set(*fi.dst_dladdr_groups));
    pyglue_setdict_string(ret, "dst_nwaddr_groups", to_set(*fi.dst_nwaddr_groups));

    /* policy info */
    pyglue_setdict_string(ret, "policy_id", ::to_python(fi.policy_id));
    PyObject* pyrules = PySet_New(NULL);
    BOOST_FOREACH(uint32_t id, fi.policy_rules) {
        PySet_Add(pyrules, ::to_python(id));
    }
    pyglue_setdict_string(ret, "policy_rules", pyrules);
    pyglue_setdict_string(ret, "routing_action",
            ::to_python(fi.routing_action_str(fi.routing_action)));
    return ret;
}

flow_cache_proxy::flow_cache_proxy(PyObject* ctxt)
        : fc(0)
{
    if (!SWIG_Python_GetSwigThis(ctxt) || !SWIG_Python_GetSwigThis(ctxt)->ptr) {
        throw std::runtime_error("Unable to access Python context.");
    }

    c = ((PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr)->c;
}

void 
flow_cache_proxy::configure(PyObject* configuration) {
    c->resolve(fc);
}

void 
flow_cache_proxy::install(PyObject*) {
    //NOP
}

PyObject*
flow_cache_proxy::get_py_flows(const FlowBuf &buf, size_t max_count) {
    size_t sz;
    if (max_count > 0) {
        sz = max_count < buf.size() ? max_count : buf.size();
    }
    else {
        sz = buf.size();
    }
    PyObject* ret = PyTuple_New(sz);
    for (int i = 0; i < sz; ++i) {
        PyTuple_SetItem(ret, i, ::to_python(*(buf.get(i)),
                boost::bind(&Flow_cache::get_group_type, fc, _1, _2)));
    }
    return ret;
}

PyObject* 
flow_cache_proxy::get_host_flows(std::string hostname) {
    FlowBuf_ptr buf = fc->get_host_flow_buf(hostname);
    if (buf == NULL) {
        return PyTuple_New(0);
    }
    PyObject* ret = PyTuple_New(buf->size());
    for (int i = 0; i < buf->size(); ++i) {
        PyTuple_SetItem(ret, i, ::to_python(*(buf->get(i)),
                boost::bind(&Flow_cache::get_group_type, fc, _1, _2)));
    }
    return ret;
}

PyObject* 
flow_cache_proxy::get_policy_flows(uint32_t policy_id, uint32_t rule_id) {
    FlowBuf_ptr buf = fc->get_policy_flow_buf(policy_id, rule_id);
    if (buf == NULL) {
        return PyTuple_New(0);
    }
    PyObject* ret = PyTuple_New(buf->size());
    for (int i = 0; i < buf->size(); ++i) {
        PyTuple_SetItem(ret, i, ::to_python(*(buf->get(i)),
                boost::bind(&Flow_cache::get_group_type, fc, _1, _2)));
    }
    return ret;
}

} // namespcae applications
} // namespace vigil

