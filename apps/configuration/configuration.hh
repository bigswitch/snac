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
#ifndef CONFIGURATION_HH
#define CONFIGURATION_HH 1

#include "component.hh"

#include <string>

namespace vigil {
namespace applications {
namespace configuration {

/* Configuration management component.
 *
 * Currently the supported functionality is minimal: the component
 * merely creates the configuration table to the transactional storage
 * as needed.  The applications are expected to access the table
 * directly, with the Property helper classes provided for them.
 */
class Configuration
    : public container::Component {
public:
    Configuration(const container::Context* c, const json_object*);

    void configure(const container::Configuration*);
    void install();

    /* Table name and column names */
    static const std::string TABLE;
    static const std::string COL_GUID;
    static const std::string COL_SECTION;
    static const std::string COL_KEY;
    static const std::string COL_VALUE_ORDER;
    static const std::string COL_VALUE_TYPE;
    static const std::string COL_VALUE_INT;
    static const std::string COL_VALUE_STR;
    static const std::string COL_VALUE_FLOAT;

    static const int VAL_TYPE_STR;
    static const int VAL_TYPE_INT;
    static const int VAL_TYPE_FLOAT;
};

}
}
}

#endif
