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
#include "component.hh"
#include "config.h"

#include <string>

#include "configuration.hh"
#include "storage/transactional-storage.hh"
#include "storage/transactional-storage-blocking.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::configuration;
using namespace vigil::applications::storage;

static Vlog_module lg("configuration");

Configuration::Configuration(const container::Context* c, 
                             const json_object*)
    : container::Component(c) {
}

void 
Configuration::configure(const container::Configuration*) {
    /* Nothing here */
}

void
Configuration::install() {
    // Create the configuration table if necessary
    Async_transactional_storage* async_storage;
    resolve(async_storage);
    
    Sync_transactional_storage storage(async_storage);
    Sync_transactional_storage::Get_connection_result result =
        storage.get_connection();
    if (!result.get<0>().is_success()) {
        throw runtime_error("Can't access the transactional storage");
    }
    
    Sync_transactional_connection_ptr connection = result.get<1>();
    
    Column_definition_map columns;
    columns[COL_SECTION] = "";
    columns["KEY"] = "";
    columns["VALUE_ORDER"] = (int64_t)0;
    columns["VALUE_TYPE"] = (int64_t)0;
    columns["VALUE_INT"] = (int64_t)0;
    columns["VALUE_FLOAT"] = (double)0;
    columns["VALUE_STR"] = "";
    
    Index_list indices;
    Index index_1;
    index_1.name = "INDEX_1";
    index_1.columns.push_back("SECTION");
    indices.push_back(index_1);
    
    Result r = connection->create_table(TABLE, columns, indices, 0);
    if (!result.get<0>().is_success()) {
        throw runtime_error("Can't create the configuration table");
    }
}

const string Configuration::TABLE("PROPERTIES");
const string Configuration::COL_GUID("GUID");
const string Configuration::COL_SECTION("SECTION");
const string Configuration::COL_KEY("KEY");
const string Configuration::COL_VALUE_ORDER("VALUE_ORDER");
const string Configuration::COL_VALUE_TYPE("VALUE_TYPE");
const string Configuration::COL_VALUE_INT("VALUE_INT");
const string Configuration::COL_VALUE_STR("VALUE_STR");
const string Configuration::COL_VALUE_FLOAT("VALUE_FLOAT");


const int Configuration::VAL_TYPE_INT = COLUMN_INT;
const int Configuration::VAL_TYPE_STR = COLUMN_TEXT;
const int Configuration::VAL_TYPE_FLOAT = COLUMN_DOUBLE;

REGISTER_COMPONENT(container::Simple_component_factory<Configuration>,
                   Configuration);

