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

typedef boost::function<bool(uint32_t, Directory::Group_Type&)>
        Group_type_resolver; 

#if PY_VERSION_HEX < 0x02050000
static PyObject *PySet_New(PyObject *iterable) {
    return PyObject_CallFunctionObjArgs((PyObject *) &PySet_Type, iterable, NULL);
}

static int PySet_Add(PyObject *s, PyObject *key) {
    PyObject *ret = PyObject_CallMethod(s, "add", "O", key);
    if (ret == NULL)
        return -1;
    Py_DECREF(ret);
    return 0;
}
#endif

static inline PyObject* to_set(std::vector<uint32_t> intvec) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(uint32_t id, intvec) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}

static inline PyObject* to_set(std::list<uint32_t> intlist) {
    PyObject* ret = PySet_New(NULL);
    BOOST_FOREACH(uint32_t id, intlist) {
        PySet_Add(ret, ::to_python(id));
    }
    return ret;
}

static inline void set_host_groups(std::vector<uint32_t> group_ids,
        PyObject* hgroup_set, PyObject* lgroup_set, PyObject* sgroup_set,
        Group_type_resolver gtr) {
    BOOST_FOREACH(uint32_t id, group_ids) {
        Directory::Group_Type gtype;
        if(gtr(id, gtype)) {
            switch (gtype) {
            case Directory::HOST_PRINCIPAL_GROUP:
                PySet_Add(hgroup_set, ::to_python(id));
                break;
            case Directory::LOCATION_PRINCIPAL_GROUP:
                PySet_Add(lgroup_set, ::to_python(id));
                break;
            case Directory::SWITCH_PRINCIPAL_GROUP:
                PySet_Add(sgroup_set, ::to_python(id));
                break;
            default:
                break; //avoid compiler warning
            }
        }
    }
}

static inline void set_addr_groups(std::vector<uint32_t> group_ids,
        PyObject* dl_group_set, PyObject* nw_group_set,
        Group_type_resolver gtr) {
    BOOST_FOREACH(uint32_t id, group_ids) {
        Directory::Group_Type gtype;
        if(gtr(id, gtype)) {
            switch (gtype) {
            case Directory::DLADDR_GROUP:
                PySet_Add(dl_group_set, ::to_python(id));
                break;
            case Directory::NWADDR_GROUP:
                PySet_Add(nw_group_set, ::to_python(id));
                break;
            default:
                break; //avoid compiler warning
            }
        }
    }
}

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
    pyglue_setdict_string(ret, "src_users", to_set(fi.src_users));
    pyglue_setdict_string(ret, "src_user_groups", to_set(fi.src_user_groups));
    pyglue_setdict_string(ret, "dst_users", to_set(fi.dst_users));
    pyglue_setdict_string(ret, "dst_user_groups", to_set(fi.dst_user_groups));
    pyglue_setdict_string(ret, "src_host", ::to_python(fi.src_host));
    pyglue_setdict_string(ret, "dst_host", ::to_python(fi.dst_host));

    //fi.src_host_groups may contain host, location, and switch group ids
    PyObject* shgroups = PySet_New(NULL);
    PyObject* slgroups = PySet_New(NULL);
    PyObject* ssgroups = PySet_New(NULL);
    set_host_groups(fi.src_host_groups, shgroups, slgroups, ssgroups, gtr);
    pyglue_setdict_string(ret, "src_host_groups", shgroups);
    pyglue_setdict_string(ret, "src_location_groups", slgroups);
    pyglue_setdict_string(ret, "src_switch_groups", ssgroups);

    //fi.dst_host_groups may contain host, location, and switch group ids
    PyObject* dhgroups = PySet_New(NULL);
    PyObject* dlgroups = PySet_New(NULL);
    PyObject* dsgroups = PySet_New(NULL);
    set_host_groups(fi.dst_host_groups, dhgroups, dlgroups, dsgroups, gtr);
    pyglue_setdict_string(ret, "dst_host_groups", dhgroups);
    pyglue_setdict_string(ret, "dst_location_groups", dlgroups);
    pyglue_setdict_string(ret, "dst_switch_groups", dsgroups);

    //fi.src_addr_groups may contain dladdr and nwaddr group ids
    PyObject* s_dladdr_groups = PySet_New(NULL);
    PyObject* s_nwaddr_groups = PySet_New(NULL);
    set_addr_groups(*(fi.src_addr_groups), s_dladdr_groups, s_nwaddr_groups,
            gtr);
    pyglue_setdict_string(ret, "src_dladdr_groups", s_dladdr_groups);
    pyglue_setdict_string(ret, "src_nwaddr_groups", s_nwaddr_groups);

    //fi.dst_addr_groups may contain dladdr and nwaddr group ids
    PyObject* d_dladdr_groups = PySet_New(NULL);
    PyObject* d_nwaddr_groups = PySet_New(NULL);
    set_addr_groups(*(fi.dst_addr_groups), d_dladdr_groups, d_nwaddr_groups,
            gtr);
    pyglue_setdict_string(ret, "dst_dladdr_groups", d_dladdr_groups);
    pyglue_setdict_string(ret, "dst_nwaddr_groups", d_nwaddr_groups);

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
        throw runtime_error("Unable to access Python context.");
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

