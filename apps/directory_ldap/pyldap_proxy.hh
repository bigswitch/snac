/*
 * Proxy class to expose ldap_proxy.hh to Python.
 * This file is only to be included from the SWIG interface file
 * (ldap_proxy.i)
 *
 * Copyright 2008 (C) Nicira, Inc.
 *
 */

#ifndef PYLDAP_PROXY_HH__
#define PYLDAP_PROXY_HH__

#include <Python.h>
#include <boost/bind.hpp>

#include "ldap_proxy.hh"
#include "directory/directory.hh"
#include "pyrt/pyglue.hh"
#include "storage/transactional-storage.hh"

using namespace std;

namespace vigil {
namespace applications {
namespace directory {

typedef PyObject* PyDeferred;

// needed b/c we must call Ldap_proxy::shutdown()
// to allow its thread-pool to complete asynchronously
// before we can delete the class, which contains a
// thread pools as a member
static void delete_proxy(Ldap_proxy *p) {
  delete p;
}


class pyldap_proxy {
public:
    pyldap_proxy(const string& name, int config_id)
            : name(name), config_id(config_id) {}

    ~pyldap_proxy() {
      ldap_proxy->shutdown(boost::bind(&delete_proxy, ldap_proxy));
    }

    /*
     * Initialize directory instance for use.
     *
     * On success, returns deferred returning when instance is ready for use.
     * On error, returns Py_None or deferred calling errback.
     */
    PyDeferred initialize(PyObject* ctxt);


    /********************
     * Meta information *
     ********************/

    /*
     * Returns string describing directory component type
     */
    std::string get_type();

    /*
     * Returns python str->str dict of default config parameters
     */
    static PyObject* get_default_config();

    /*
     * Returns python str->str dict of config parameters
     */
    PyObject* get_config_params();

    /*
     * Returns deferred returning str->str dict of new config parameters
     */
    PyDeferred set_config_params(PyObject* config_str_dict);

    /*
     * Returns DirectoryStatus class describing the current status
     */
    PyObject* get_status();


    /******************
     * Authentication *
     ******************/

    PyObject* get_enabled_auth_types() {
        return to_python_tuple(ldap_proxy->get_enabled_auth_types());
    }

    PyDeferred set_enabled_auth_types(PyObject* auth_type_tuple);

    PyDeferred get_credentials(int principal_type,
            std::string principal_name, const char* credtype);

    /*
    PyObject* put_credentials(int principal_type,
            const std::string & principal_name, const char* credtype);
    */

    PyDeferred simple_auth(const char* username, const char* password);


    /**************
     * Principals *
     **************/

    PyObject* get_enabled_principals();

    std::string principal_enabled(int principal_type) {
        return ldap_proxy->principal_enabled(principal_type);
    }

    PyDeferred set_enabled_principals(PyObject* enabled_principal_dict);

    PyDeferred get_principal(int principal_type, std::string principal_name);

    PyDeferred search_principals(int principal_type, PyObject* query_dict);


    /**********
     * Groups *
     **********/

    bool supports_global_groups() {return false;}

    PyObject* get_enabled_groups();

    std::string group_enabled(int group_type) {
        return ldap_proxy->group_enabled(group_type);
    }

    PyDeferred set_enabled_groups(PyObject* enabled_group_dict);

    PyDeferred get_group_membership(int group_type, std::string member,
            PyObject* local_groups=NULL);

    PyDeferred search_groups(int group_type, PyObject* query_dict);

    PyDeferred get_group(int group_type, std::string group_name);

    PyDeferred get_group_parents(int group_type, std::string group_name);

protected:
    const string name;
    uint64_t config_id;
    storage::Async_transactional_storage *tstorage;
    Ldap_proxy* ldap_proxy;
    container::Component* component;

}; // class pyldap_proxy

} // namespcae directory
} // namespcae applications
} // namespace vigil

#endif //  PYLDAP_PROXY_HH__
