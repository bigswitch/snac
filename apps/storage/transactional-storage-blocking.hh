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
#ifndef TRANSACTIONAL_STORAGE_BLOCKING_HH
#define TRANSACTIONAL_STORAGE_BLOCKING_HH 1

#include <boost/tuple/tuple.hpp>

#include "threads/cooperative.hh"
#include "transactional-storage.hh"

namespace vigil {
namespace applications {
namespace storage {

class Sync_transactional_connection;
typedef boost::shared_ptr<Sync_transactional_connection>
Sync_transactional_connection_ptr;

class Sync_transactional_cursor;
typedef boost::shared_ptr<Sync_transactional_cursor>
Sync_transactional_cursor_ptr;

/* A blocking wrapper for the transactional multi-key-value storage.
 * The semantics of the storage operations are identical to the
 * non-blocking storage.
 */
class Sync_transactional_storage {
public:
    Sync_transactional_storage(Async_transactional_storage*);
    virtual ~Sync_transactional_storage();

    typedef boost::tuple<Result, Sync_transactional_connection_ptr> 
    Get_connection_result;

    Get_connection_result get_connection() const;

private:
    void get_connection_callback(const Result&,
                                 const Async_transactional_connection_ptr&,
                                 Co_sema*,
                                 Get_connection_result*) const;

    Async_transactional_storage* storage;
};

/* A blocking wrapper for the transactional multi-key-value
 * connection.  The semantics of the connection operations are
 * identical to the non-blocking connection.
 */
class Sync_transactional_connection {
public:
    typedef boost::tuple<Result, Sync_transactional_cursor_ptr> Get_result;
    typedef boost::tuple<Result, Trigger_id> Put_trigger_result;
    typedef boost::tuple<Result, GUID> Put_result;

    Sync_transactional_connection(const Async_transactional_connection_ptr&);

    const Result begin(const Async_transactional_connection::Transaction_mode&)
        const;
    const Result commit() const;
    const Result rollback() const;
    Get_result get(const Table_name&, const Query&) const;
    const Put_trigger_result put_trigger(const Table_name&, const Row&,
                                         const Trigger_function&) const;
    const Put_trigger_result put_trigger(const Table_name&,
                                         const bool sticky,
                                         const Trigger_function&) const;
    const Result remove_trigger(const Trigger_id&) const;
    const Result create_table(const Table_name&, const Column_definition_map&,
                              const Index_list&, const int version) const;
    const Result drop_table(const Table_name&) const;
    const Put_result put(const Table_name&, const Row&) const;
    const Result modify(const Table_name&, const Row&) const;
    const Result remove(const Table_name&, const Row&) const;

    Async_transactional_connection_ptr connection;

private:
    void get_callback(const Result&, const Async_transactional_cursor_ptr&,
                      Co_sema*, Get_result*) const;
    void put_callback(const Result&, const GUID&, Co_sema*, Put_result*) const;
    void put_trigger_callback(const Result&, const Trigger_id&,
                              Co_sema*, Put_trigger_result*) const;
    void callback(const Result&, Co_sema*, Result*) const;
};

/* A blocking wrapper for the transactional multi-key-value cursor.
 * The semantics of the cursor operations are identical to the
 * non-blocking cursor.
 */
class Sync_transactional_cursor {
public:
    typedef boost::tuple<Result, Row> Get_next_result;

    Sync_transactional_cursor(const Async_transactional_cursor_ptr&);

    Get_next_result get_next() const;
    Result close() const;

private:
    void get_next_callback(const Result&, const Row&, Co_sema*,
                           Get_next_result*) const;
    void close_callback(const Result&, Co_sema*, Result*) const;

    Async_transactional_cursor_ptr cursor;
};

} /* namespace storage */
} /* namespace applications */
} /* namespace vigil */

#endif
