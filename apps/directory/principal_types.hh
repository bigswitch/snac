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
#ifndef PRINCIPAL_TYPES_HH
#define PRINCIPAL_TYPES_HH

#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>

#include <boost/function.hpp>

#include "netinet++/datapathid.hh"
#include "netinet++/ethernetaddr.hh"

#ifdef TWISTED_ENABLED
#include <Python.h>
#include "pyrt/pyglue.hh"
#else
class PyObject;
#endif

namespace vigil {
namespace applications {
namespace directory {

typedef std::set<std::string> Principal_name_set;
typedef std::set<std::string> Group_name_set;
typedef std::set<std::string> Group_member_set;
typedef std::set<std::string> Nox_role_set;

//TODO: change these to ints for c version
extern const std::string NO_SUPPORT;
extern const std::string READ_ONLY_SUPPORT;
extern const std::string READ_WRITE_SUPPORT;

//TODO: change these to ints for c version
extern const std::string AUTH_SIMPLE;
extern const std::string AUTHORIZED_CERT_FP;

typedef std::set<std::string> AuthSupportSet;

struct AuthResult {
    enum AuthStatus {
        SUCCESS=0,
        INVALID_CREDENTIALS,
        ACCOUNT_DISABLED,

        COMMUNICATION_TIMEOUT,
        SERVER_ERROR
    };

    AuthStatus status;
    std::string username;
    Group_name_set groups;
    Nox_role_set nox_roles;

    const std::string status_str() const {
        switch (status) {
            case SUCCESS:               return "Success";
            case INVALID_CREDENTIALS:   return "Invalid Credentials";
            case ACCOUNT_DISABLED:      return "Account Disabled";
            case COMMUNICATION_TIMEOUT: return "Communication Timeout";
            case SERVER_ERROR:          return "Server Error";
            default:                    return "Invalid Status";
        }
    }

    AuthResult(AuthStatus status, std::string username,
            Group_name_set groups = Group_name_set(),
            Nox_role_set roles = Nox_role_set())
        : status(status), username(username), groups(groups), nox_roles(roles)
    {
        //NOP
    }

};

typedef boost::function<void(const AuthResult&)> Simple_auth_callback;

enum Principal_Type {
    SWITCH_PRINCIPAL = 0,
    LOCATION_PRINCIPAL,
    HOST_PRINCIPAL,
    USER_PRINCIPAL
};
typedef std::vector<Principal_Type> PrincipalTypeList;
typedef std::map<Principal_Type, std::string> PrincipalSupportMap;

enum Group_Type {
    SWITCH_PRINCIPAL_GROUP = 0,
    LOCATION_PRINCIPAL_GROUP,
    HOST_PRINCIPAL_GROUP,
    USER_PRINCIPAL_GROUP,
    DLADDR_GROUP,
    NWADDR_GROUP
};
typedef std::vector<Group_Type> GroupTypeList;
typedef std::map<Group_Type, std::string> GroupSupportMap;

struct PrincipalInfo {
    Principal_Type type;
    std::string name;
    PrincipalInfo(Principal_Type t, std::string n) : type(t), name(n) { }
};

struct SwitchInfo : public PrincipalInfo {
    datapathid  dpid;
    SwitchInfo() : PrincipalInfo(SWITCH_PRINCIPAL, ""), dpid() { }
};

struct LocationInfo : public PrincipalInfo {
    std::string name;
    datapathid  dpid;
    uint16_t    port;
    LocationInfo() : PrincipalInfo(LOCATION_PRINCIPAL, ""), dpid(), port(0) { }
};

struct NetInfo {
    datapathid   dpid;
    uint16_t     port;
    ethernetaddr dladdr;
    uint32_t     nwaddr;
    bool         is_router;
    bool         is_gateway;
    NetInfo() : dpid(), port(0), dladdr(), nwaddr(0),
                is_router(false), is_gateway(false) { }
};

struct HostInfo : public PrincipalInfo {
    std::string              description;
    std::vector<std::string> aliases;
    std::vector<NetInfo>     netinfos;
    HostInfo() : PrincipalInfo(HOST_PRINCIPAL, ""), description(""),
                 aliases(), netinfos() { }
};

struct UserInfo : public PrincipalInfo {
    std::string user_id;
    std::string user_real_name;
    std::string description;
    std::string location;
    std::string phone;
    std::string user_email;
    UserInfo() : PrincipalInfo(USER_PRINCIPAL, ""), user_id(""),
                 user_real_name(""), description(""), location(""),
                 phone(""), user_email("") { }
};

struct CertFingerprintCredential  {
    std::string type;
    std::string fingerprint;
    bool is_approved;
    CertFingerprintCredential() : type(AUTHORIZED_CERT_FP),
                                  fingerprint(""), is_approved(false) {}
};

typedef std::map<std::string, std::string> PrincipalQuery;

struct GroupInfo {
    Group_Type type;
    std::string name;
    std::string description;
    Group_member_set members;
    Group_name_set subgroups;
    GroupInfo(Group_Type t, std::string n, std::string d="") 
            : type(t), name(n), description(d), members(), subgroups() { }
};

typedef std::map<std::string, std::string> GroupQuery;

} // namespace directory
} // namespace applications
} // namespace vigil

#endif /* PRINCIPAL_TYPES_HH */
