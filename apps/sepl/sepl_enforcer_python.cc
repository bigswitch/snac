/* Copyright 2008 (C) Nicira, Inc. */

#include "sepl_enforcer.hh"

#include "pyrt/pyglue.hh"
#include "vlog.hh"

namespace vigil {
namespace applications {

static Vlog_module lg("sepl");

/*
 * Methods creating flow PyObject to be passed to Python SEPL functions
 */

#ifdef TWISTED_ENABLED
static
bool
reset_connector(Sepl_data& data, bool reset_dst_infos)
{
    try {
        if (!data.src_current) {
            pyglue_setdict_string(data.py_flow, "suser_idx", to_python(data.suser_idx));
            data.src_current = true;
        }
        if (!data.dst_current) {
            pyglue_setdict_string(data.py_flow, "dst_idx", to_python(data.dst_idx));
            pyglue_setdict_string(data.py_flow, "duser_idx", to_python(data.duser_idx));
            data.dst_current = true;
        }
        if (reset_dst_infos) {
            PyObject *dsts = PyDict_GetItemString(data.py_flow, "destinations");
            if (dsts == NULL) {
                VLOG_ERR(lg, "Destinations entry not present in flow dict.");
                return false;
            }
            for (uint32_t i = 0; i < data.fi->dst_locations.size(); ++i) {
                PyObject *entry = PyList_GetItem(dsts, i);
                if (entry == NULL) {
                    VLOG_ERR(lg, "DstInfo not present in destinations list.");
                    return false;
                }
                Flow_in_event::DestinationInfo& dstInfo = data.fi->dst_locations[i];
                pyglue_setdict_string(entry, "allowed", to_python(dstInfo.allowed));
                pyglue_setdict_string(entry, "waypoints", to_python_list(dstInfo.waypoints));
                pyglue_setdict_string(entry, "rules", to_python_list(dstInfo.rules));
            }
        }
    } catch (std::bad_alloc& e) {
        VLOG_ERR(lg, "Could not reset flow connector.");
        Py_XDECREF(data.py_flow);
        data.py_flow = NULL;
        data.src_current = data.dst_current = false;
        return false;
    }
    return true;
}

// should eventually create Flow_in_event in python...

static
bool
set_py_flow(Sepl_data& data)
{
    try {
        data.py_flow = PyDict_New();
        if (data.py_flow == NULL) {
            VLOG_ERR(lg, "Could not create py_flow dict");
            return false;
        }

        Flow_in_event& fi = *data.fi;
        pyglue_setdict_string(data.py_flow, "flow", to_python(fi.flow));
        pyglue_setdict_string(data.py_flow, "active", to_python(fi.active));
        pyglue_setdict_string(data.py_flow, "received_sec", to_python(fi.received.tv_sec));
        pyglue_setdict_string(data.py_flow, "received_usec", to_python(fi.received.tv_usec));
        pyglue_setdict_string(data.py_flow, "src_location", to_python(fi.src_location));
        pyglue_setdict_string(data.py_flow, "route_source", route_source_to_python(fi.route_source));
        pyglue_setdict_string(data.py_flow, "dst_locations", to_python(fi.dst_locations));
        pyglue_setdict_string(data.py_flow, "route_destinations", route_destinations_to_python(fi.route_destinations));
        pyglue_setdict_string(data.py_flow, "src_dladdr_groups", to_python_list(*fi.src_dladdr_groups));
        pyglue_setdict_string(data.py_flow, "src_nwaddr_groups", to_python_list(*fi.src_nwaddr_groups));
        pyglue_setdict_string(data.py_flow, "dst_dladdr_groups", to_python_list(*fi.dst_dladdr_groups));
        pyglue_setdict_string(data.py_flow, "dst_nwaddr_groups", to_python_list(*fi.dst_nwaddr_groups));
        pyglue_setdict_string(data.py_flow, "dst_authed", to_python(fi.dst_authed));
        pyglue_setdict_string(data.py_flow, "datapath_id", to_python(fi.datapath_id));
        pyglue_setdict_string(data.py_flow, "buf", to_python(fi.buf));
        pyglue_setdict_string(data.py_flow, "total_len", to_python(fi.total_len));
        pyglue_setdict_string(data.py_flow, "buffer_id", to_python(fi.buffer_id));
        pyglue_setdict_string(data.py_flow, "reason", to_python(fi.reason));

        pyglue_setdict_string(data.py_flow, "role", to_python((uint32_t) data.role));
        pyglue_setdict_string(data.py_flow, "suser_idx", to_python(data.suser_idx));
        pyglue_setdict_string(data.py_flow, "dst_idx", to_python(data.dst_idx));
        pyglue_setdict_string(data.py_flow, "duser_idx", to_python(data.duser_idx));
        data.src_current = true;
        data.dst_current = true;

    } catch (std::bad_alloc& e) {
        VLOG_ERR(lg, "Could not create flow object - setting to NULL.");
        Py_XDECREF(data.py_flow);
        data.py_flow = NULL;
        return false;
    }
    return true;
}

#endif

bool
Sepl_data::call_python_pred(PyObject *fn)
{
#ifdef TWISTED_ENABLED
    if (py_flow == NULL) {
        if (!set_py_flow(*this)) {
            return false;
        }
    } else if (!reset_connector(*this, false)) {
        return false;
    }

    PyObject *ret = PyObject_CallFunctionObjArgs(fn, py_flow, NULL);
    if (ret == NULL) {
        const std::string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call m_fn - Python failure: %s", exc.c_str());
        return false;
    }

    bool result = false;
    if (!PyBool_Check(ret)) {
        VLOG_ERR(lg, "fn returned non-bool object - returning false match!");
    } else {
        result = (ret == Py_True);
    }
    Py_DECREF(ret);
    return result;
#else
    VLOG_ERR(lg, "Could not call fn to check for rule match - Twisted disabled");
    return false;
#endif
}

bool
Sepl_enforcer::call_python_action(PyObject *pyfn)
{
#ifdef TWISTED_ENABLED
    if (data.py_flow == NULL) {
        if (!set_py_flow(data)) {
            return false;
        }
    } else if (!reset_connector(data, true)) {
        return false;
    }
    PyObject *ret = PyObject_CallFunctionObjArgs(pyfn, data.py_flow, NULL);
    if (ret == NULL) {
        const std::string exc = pretty_print_python_exception();
        VLOG_ERR(lg, "Could not call python function action: %s", exc.c_str());
    } else {
        Py_DECREF(ret);
    }
    return true;
#else
    VLOG_ERR(lg, "Could not call Python function action - Twisted disabled");
#endif
    return false;
}

}
}
