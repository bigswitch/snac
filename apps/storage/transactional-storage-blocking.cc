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

#include "transactional-storage-blocking.hh"

#include <boost/bind.hpp>

using namespace vigil;
using namespace vigil::applications::storage;

Sync_transactional_storage::
Sync_transactional_storage(Async_transactional_storage* storage_)
    : storage(storage_) {

}

Sync_transactional_storage::~Sync_transactional_storage() {

}

Sync_transactional_storage::Get_connection_result
Sync_transactional_storage::get_connection() const {
    Co_sema sem;
    Get_connection_result result;
    storage->get_connection
        (boost::bind(&Sync_transactional_storage::get_connection_callback, this,
                     _1, _2, &sem, &result));
    sem.down();
    return result;
}

void
Sync_transactional_storage::
get_connection_callback(const Result& result,
                        const Async_transactional_connection_ptr& conn,
                        Co_sema* sem, Sync_transactional_storage::
                        Get_connection_result* ret) const {
    *ret = Get_connection_result(result, 
                                 Sync_transactional_connection_ptr
                                 (new Sync_transactional_connection(conn)));
    sem->up();
}

Sync_transactional_connection::
Sync_transactional_connection(const Async_transactional_connection_ptr& c)
    : connection(c) {

}

const Result 
Sync_transactional_connection::begin(const Async_transactional_connection::
                                     Transaction_mode& mode) const {
    Co_sema sem;
    Result result;
    connection->begin(mode, boost::bind(&Sync_transactional_connection::
                                        callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

const Result 
Sync_transactional_connection::commit() const {
    Co_sema sem;
    Result result;
    connection->commit(boost::bind(&Sync_transactional_connection::
                                   callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

const Result 
Sync_transactional_connection::rollback() const {
    Co_sema sem;
    Result result;
    connection->rollback(boost::bind(&Sync_transactional_connection::
                                     callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

Sync_transactional_connection::Get_result
Sync_transactional_connection::get(const Table_name& t, const Query& q) const {
    Co_sema sem;
    Get_result result;
    connection->get
        (t, q, boost::bind(&Sync_transactional_connection::get_callback, this,
                           _1, _2, &sem, &result));
    sem.down();
    return result;
}

void
Sync_transactional_connection::
get_callback(const Result& result, const Async_transactional_cursor_ptr& cursor,
             Co_sema* sem, Get_result* ret) const {
    *ret = Get_result(result, Sync_transactional_cursor_ptr
                      (new Sync_transactional_cursor(cursor)));
    sem->up();
}

const Sync_transactional_connection::Put_result 
Sync_transactional_connection::put(const Table_name& table, 
                                   const Row& row) const {
    Co_sema sem;
    Put_result result;
    connection->put(table, row, 
                    boost::bind(&Sync_transactional_connection::put_callback, 
                                this, _1, _2, &sem, &result));
    sem.down();
    return result;
}

void 
Sync_transactional_connection::put_callback(const Result& result, 
                                            const GUID& guid,
                                            Co_sema* sem, 
                                            Sync_transactional_connection::
                                            Put_result* ret) const {
    *ret = Put_result(result, guid);
    sem->up();
}

const Result
Sync_transactional_connection::modify(const Table_name& table,
                                      const Row& row) const {
    Co_sema sem;
    Result result;
    connection->modify(table, row,
                       boost::bind(&Sync_transactional_connection::
                                   callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

void 
Sync_transactional_connection::callback(const Result& result, Co_sema* sem, 
                                        Result* ret) const {
    *ret = result;
    sem->up();
}

const Result
Sync_transactional_connection::remove(const Table_name& table,
                                      const Row& row) const {
    Co_sema sem;
    Result result;
    connection->remove(table, row, 
                       boost::bind(&Sync_transactional_connection::callback, 
                                   this, _1, &sem, &result));
    sem.down();
    return result;
}

const Result 
Sync_transactional_connection::create_table(const Table_name& table, 
                                            const Column_definition_map& c,
                                            const Index_list& indices,
                                            const int version) const {
    Co_sema sem;
    Result result;
    connection->create_table(table, c, indices, version,
                             boost::bind(&Sync_transactional_connection::
                                         callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

const Result 
Sync_transactional_connection::drop_table(const Table_name& table) const {
    Co_sema sem;
    Result result;
    connection->drop_table(table, 
                           boost::bind(&Sync_transactional_connection::callback,
                                       this, _1, &sem, &result));
    sem.down();
    return result;
}

/* Create a trigger for previous query results. */
const Sync_transactional_connection::Put_trigger_result 
Sync_transactional_connection::put_trigger(const Table_name& table,
                                           const Row& row,
                                           const Trigger_function& tf) const {
    Co_sema sem;
    Put_trigger_result result;
    connection->put_trigger(table, row, tf,
                            boost::bind(&Sync_transactional_connection::
                                        put_trigger_callback, 
                                        this, _1, _2, &sem, &result));
    sem.down();
    return result;
}

void
Sync_transactional_connection::put_trigger_callback(const Result& result, 
                                                    const Trigger_id& tid,
                                                    Co_sema* sem, 
                                                    Put_trigger_result* ret) 
    const {
    *ret = Put_trigger_result(result, tid);
    sem->up();
}

const Sync_transactional_connection::Put_trigger_result 
Sync_transactional_connection::put_trigger(const Table_name& table,
                                           const bool sticky,
                                           const Trigger_function& tf) const {
    Co_sema sem;
    Put_trigger_result result;
    connection->put_trigger(table, sticky, tf,
                            boost::bind(&Sync_transactional_connection::
                                        put_trigger_callback, 
                                        this, _1, _2, &sem, &result));
    sem.down();
    return result;
}

const Result 
Sync_transactional_connection::remove_trigger(const Trigger_id& tid) const {
    Co_sema sem;
    Result result;
    connection->remove_trigger(tid,
                               boost::bind(&Sync_transactional_connection::
                                           callback, this, _1, &sem, &result));
    sem.down();
    return result;
}

Sync_transactional_cursor::
Sync_transactional_cursor(const Async_transactional_cursor_ptr& c)
    : cursor(c) {

}

Sync_transactional_cursor::Get_next_result
Sync_transactional_cursor::get_next() const {
    Co_sema sem;
    Get_next_result result;
    cursor->get_next
        (boost::bind(&Sync_transactional_cursor::get_next_callback, this,
                     _1, _2, &sem, &result));
    sem.down();
    return result;
}

void
Sync_transactional_cursor::
get_next_callback(const Result& result, const Row& row, Co_sema* sem,
                  Sync_transactional_cursor::Get_next_result* ret) const {
    *ret = Get_next_result(result, row);
    sem->up();
}

Result
Sync_transactional_cursor::close() const {
    Co_sema sem;
    Result result;
    cursor->close(boost::bind(&Sync_transactional_cursor::close_callback, this,
                              _1, &sem, &result));
    sem.down();
    return result;
}

void
Sync_transactional_cursor::
close_callback(const Result& result, Co_sema* sem, Result* ret) const {
    *ret = result;
    sem->up();
}
