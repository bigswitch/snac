/* 
 * Proxy class to expose flow_cache.hh to Python.
 * This file is only to be included from the SWIG interface file
 * (pyflow_cache.i)
 *
 * Copyright 2008 (C) Nicira, Inc.
 *
 */

#ifndef FLOW_CACHE_PROXY_HH__
#define FLOW_CACHE_PROXY_HH__

#include <Python.h>

#include "flow_cache.hh"
#include "pyrt/pyglue.hh"

using namespace std;

namespace vigil {
namespace applications {

class flow_cache_proxy{
public:
    flow_cache_proxy(PyObject* ctxt);

    void configure(PyObject*);
    void install(PyObject*);

    /*
     * Returns tuple(flow_info)
     */
    inline PyObject* get_all_flows(int max_count=0) {
        return get_py_flows(fc->get_all_flow_buf(), max_count);
    }

    /*
     * Returns tuple(flow_info)
     */
    inline PyObject* get_allowed_flows(int max_count=0) {
        return get_py_flows(fc->get_allowed_flow_buf(), max_count);
    }

    /*
     * Returns tuple(flow_info)
     */
    inline PyObject* get_denied_flows(int max_count=0) {
        return get_py_flows(fc->get_denied_flow_buf(), max_count);
    }

    /*
     * Returns tuple(flow_info)
     */
    PyObject* get_host_flows(std::string hostname);

    /*
     * Returns tuple(flow_info)
     */
    PyObject* get_policy_flows(uint32_t policy_id, uint32_t rule_id);

    int get_cur_policy_id() {return fc->get_cur_policy_id();}

protected:   
    PyObject* get_py_flows(const FlowBuf &buf, size_t max_count);

    Flow_cache* fc;
    container::Component* c;
};

} // namespcae applications
} // namespace vigil

#endif /* FLOW_CACHE_PROXY_HH__ */
