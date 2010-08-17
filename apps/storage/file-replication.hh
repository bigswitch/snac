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
#ifndef FILE_REPLICATION_HH
#define FILE_REPLICATION_HH 1

#include "storage.hh"

namespace vigil {
namespace applications {
namespace storage {

class Async_file_logger 
    : public Async_logger {
public:
    /* Insert a new row. */
    void put(const Row&, 
                     /* Put_callback arguments */
                     const Result&, const GUID&, 
                     const Async_storage::Put_callback&);
    
    /* Modify an existing row */
    void modify(const Row&,
                        /* Modify_callback arguments */
                        const Result&, const Context&, 
                        const Async_storage::Modify_callback&);
    
    /* Remove a row */
    void remove(const GUID&,
                /* Remove_callback arguments */
                const Result&, 
                const Async_storage::Remove_callback&);
};

class Async_file_replicator 
    : public Async_replicator {
public:
    virtual Async_logger* get_instance(const Table_name&, 
                                       const Column_definition_map&);
};

} // namespace storage
} // namespace applications
} // namespace vigil

#endif
