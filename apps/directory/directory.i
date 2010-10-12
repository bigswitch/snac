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
%{
#include "directory.hh"
using namespace vigil;
using namespace vigil::applications;
%}

class Directory {
public:

    static const std::string NO_SUPPORT;
    static const std::string READ_ONLY_SUPPORT;
    static const std::string READ_WRITE_SUPPORT;

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
};
