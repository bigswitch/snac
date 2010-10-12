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
#ifndef DIRECTORY_MANAGER_HH
#define DIRECTORY_MANAGER_HH 1

#include "config.h"

#ifdef TWISTED_ENABLED
#include <Python.h>
#include "pyrt/deferredcallback.hh"
#include "pyrt/pyglue.hh"
#else
class PyObject;
#endif // TWISTED_ENABLED

#include "component.hh"
#include "directory.hh"
#include "hash_set.hh"
#include "principal_types.hh"
#include "netinet++/datapathid.hh"
#include "netinet++/ethernetaddr.hh"
#include "boost/function.hpp"
#include <string>

namespace vigil {
namespace applications {

class DirectoryManager
    : public container::Component {

public:
    typedef boost::function<void(directory::SwitchInfo&)> SwitchCb;
    // C++ only supports one credential type for now
    typedef boost::function<void(const std::vector <directory::CertFingerprintCredential> & ) > CredentialCb;
    typedef boost::function<void(const std::vector<std::string>&)> SearchCb;
    typedef boost::function<void(const std::string&)> StringCb;
    typedef boost::function<void(bool)> BoolCb;
    typedef boost::function<void()> EmptyCb;
    typedef boost::function<void()> ErrorCb;

    typedef hash_set<std::string> KeySet;

    DirectoryManager(const container::Context*, const json_object*);
    DirectoryManager() : Component(0), dm(0), create_dp(0), create_eth(0),
                         create_ip(0), create_cidr(0), create_cred(0) { }
    ~DirectoryManager() { }

    static void getInstance(const container::Context*, DirectoryManager*&);

    void configure(const container::Configuration*);
    void install();

    bool set_py_dm(PyObject *);
    bool set_create_dp(PyObject *);
    bool set_create_eth(PyObject *);
    bool set_create_ip(PyObject *);
    bool set_create_cidr(PyObject *);
    bool set_create_cred(PyObject *);
    bool supports_authentication();
    bool add_switch(const directory::SwitchInfo&, const std::string&,
                    const SwitchCb&, const ErrorCb&);
    bool search_switches(const directory::SwitchInfo&,
                         const hash_set<std::string>&,
                         const std::string&, const SearchCb&, const ErrorCb&);
    bool search_locations(const directory::LocationInfo&,
                          const hash_set<std::string>&,
                          const std::string&, const SearchCb&, const ErrorCb&);
    bool search_hosts(const directory::HostInfo&, const hash_set<std::string>&,
                      const std::string&, const SearchCb&, const ErrorCb&);
    bool search_users(const directory::UserInfo&, const hash_set<std::string>&,
                      const std::string&, const SearchCb&, const ErrorCb&);
    bool search_switch_groups(const std::string&, const std::string&,
                              bool, const SearchCb&, const ErrorCb&);
    bool search_location_groups(const std::string&, const std::string&,
                                bool, const SearchCb&, const ErrorCb&);
    bool search_host_groups(const std::string&, const std::string&,
                            bool, const SearchCb&, const ErrorCb&);
    bool search_user_groups(const std::string&, const std::string&,
                            bool, const SearchCb&, const ErrorCb&);
    bool search_dladdr_groups(const ethernetaddr&, const std::string&,
                              bool, const SearchCb&, const ErrorCb&);
    bool search_nwaddr_groups(uint32_t, const std::string&,
                              bool, const SearchCb&, const ErrorCb&);
    bool modify_switch_group(const std::string&,
                             const std::vector<std::string>&,
                             const std::vector<std::string>&, bool,
                             const EmptyCb&, const ErrorCb&);
    bool modify_location_group(const std::string&,
                               const std::vector<std::string>&,
                               const std::vector<std::string>&, bool,
                               const EmptyCb&, const ErrorCb&);
    bool modify_host_group(const std::string&,
                            const std::vector<std::string>&,
                            const std::vector<std::string>&, bool,
                            const EmptyCb&, const ErrorCb&);
    bool modify_user_group(const std::string&,
                           const std::vector<std::string>&,
                           const std::vector<std::string>&, bool,
                           const EmptyCb&, const ErrorCb&);
    bool modify_dladdr_group(const std::string&,
                             const std::vector<ethernetaddr>&,
                             const std::vector<std::string>&, bool,
                             const EmptyCb&, const ErrorCb&);
    bool modify_nwaddr_group(const std::string&,
                           const std::vector<uint32_t>&,
                           const std::vector<std::string>&, bool,
                           const EmptyCb&, const ErrorCb&);
    bool is_gateway(const ethernetaddr&, const std::string&,
                    const BoolCb&, const ErrorCb&);
    bool is_router(const ethernetaddr&, const std::string&,
                   const BoolCb&, const ErrorCb&);

    bool get_certfp_credential(Directory::Principal_Type ptype,
                               const std::string mangled_princpal_name,
                               const CredentialCb& cb, const ErrorCb& ecb);

    bool put_certfp_credential(Directory::Principal_Type ptype,
                               const std::string &mangled_principal_name,
                               const directory::CertFingerprintCredential &c_cred,
                               const CredentialCb& cred_cb,
                               const ErrorCb& error_cb);

    std::string add_discovered_switch(const datapathid &);
    bool get_discovered_switch_name(const datapathid &, bool ensure_in_dir,
                                    const StringCb&, const ErrorCb&);
    bool get_discovered_location_name(const std::string&, const std::string&,
                                      const datapathid &, uint16_t,
                                      bool ensure_in_dir,
                                      const StringCb&, const ErrorCb&);
    bool get_discovered_host_name(const ethernetaddr &, uint32_t nwaddr,
                                  bool dlname, bool ensure_in_dir,
                                  const StringCb&, const ErrorCb&);

private:
    PyObject *dm;
    PyObject *create_dp;
    PyObject *create_eth;
    PyObject *create_ip;
    PyObject *create_cidr;
    PyObject *create_cred;

    PyObject* to_datapathid(uint64_t);
    PyObject* to_ethernetaddr(uint64_t);
    PyObject* to_ipaddr(uint32_t);
    PyObject* to_cidr(uint32_t);
    PyObject* to_certFingerprintCredential(
        const directory::CertFingerprintCredential &cred);

    void errback(PyObject *, const char *, const ErrorCb&);
    void add_switch_cb(PyObject *, const SwitchCb&);
    void search_cb(PyObject *, const SearchCb&);
    void string_cb(PyObject *, const StringCb&);
    void empty_cb(PyObject *, const EmptyCb&);
    void bool_cb(PyObject *, const BoolCb&);
    bool search_groups(Directory::Group_Type, const std::string&,
                       const std::string&, bool, const SearchCb&,
                       const ErrorCb&);
    bool modify_group(Directory::Group_Type, const std::string&,
                      const std::vector<std::string>&,
                      const std::vector<std::string>&,
                      bool, const EmptyCb&, const ErrorCb&);
    void credentials_cb(PyObject *, const CredentialCb&);

#ifdef TWISTED_ENABLED
    bool call_method(const char*, PyObject*, PyObject*, const std::string&,
                     const DeferredCallback::Callback&,
                     const DeferredCallback::Callback&);
    bool call_search_principals(PyObject*, PyObject*, const std::string&,
                                const SearchCb&, const ErrorCb&);
    PyObject* get_py_gtype(Directory::Group_Type);
    bool call_group_method(PyObject*, PyObject*,
                           const std::string&, bool,
                           const SearchCb&, const ErrorCb&);
    bool call_modify_group(const std::string&, PyObject *,
                           PyObject *, PyObject *, bool,
                           const EmptyCb&, const ErrorCb&);

#endif
};

}

}

#endif
