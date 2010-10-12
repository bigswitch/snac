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
#ifndef DIRECTORY_HH
#define DIRECTORY_HH

#include <list>
#include <map>
#include <string>

#include "component.hh"
#include "configuration/properties.hh"
#include "principal_types.hh"

namespace vigil {
namespace applications {

namespace directory {

enum DirectoryError {
    UNKNOWN_ERROR = 0,
    RECORD_ALREADY_EXISTS,
    NONEXISTING_NAME,
    OPERATION_NOT_PERMITTED,
    BADLY_FORMATTED_NAME,
    INSUFFICIENT_INPUT,
    INVALID_QUERY,
    INVALID_CRED_TYPE,
    INVALID_DIR_TYPE,
    COMMUNICATION_ERROR,
    REMOTE_ERROR,
    INVALID_CONFIGURATION,
};

class DirectoryException : public std::exception {
public:
    DirectoryException(DirectoryError cd, std::string m) : code(cd), msg(m) {}
    ~DirectoryException() throw() {}
    const char* what() const throw() { return msg.c_str(); }
    DirectoryError get_code() { return code; }

private:
    DirectoryError code;
    std::string msg;
};

} // namespace directory

class Directory {
public:
    typedef std::map<std::string, std::string> ConfigParamMap;
    typedef boost::function<void(configuration::Properties*)> ConfigCb;
    typedef boost::function<void()> ErrorCb;

    static const std::string NO_SUPPORT;
    static const std::string READ_ONLY_SUPPORT;
    static const std::string READ_WRITE_SUPPORT;
    
    static const std::string AUTH_SIMPLE;
    static const std::string AUTHORIZED_CERT_FP;

    enum Principal_Type {
        SWITCH_PRINCIPAL = 0,
        LOCATION_PRINCIPAL,
        HOST_PRINCIPAL,
        USER_PRINCIPAL
    };

    enum Group_Type {
        SWITCH_PRINCIPAL_GROUP = 0,
        LOCATION_PRINCIPAL_GROUP,
        HOST_PRINCIPAL_GROUP,
        USER_PRINCIPAL_GROUP,
        DLADDR_GROUP,
        NWADDR_GROUP
    };

    enum Directory_Status {
        UNKNOWN = 0,
        OK,
        INVALID
    };

	virtual ~Directory() {}

	virtual void simple_auth(const std::string &username,
                             const std::string &password,
                             const directory::Simple_auth_callback& cb) { } ;
};

} // namespace vigil
} // namespace applications

#endif /* DIRECTORY_HH */
