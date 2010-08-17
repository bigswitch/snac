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

#ifndef TRANSACTIONAL_STORAGE
#define TRANSACTIONAL_STORAGE 1

#include <boost/shared_ptr.hpp>

#include "storage.hh"

namespace vigil {
namespace applications {
namespace storage {

/*
 * Transactional storage contains three meta data tables:
 * 
 * - NOX_SCHEMA_META contains a row per every table in system.
 * - NOX_SCHEMA_TABLE contains a row per a table column
 * - NOX_SCHEMA_INDEX contains a row per a table index column
 */

class Async_transactional_connection;
typedef boost::shared_ptr<Async_transactional_connection>
Async_transactional_connection_ptr;

class Async_transactional_cursor;
typedef boost::shared_ptr<Async_transactional_cursor>
Async_transactional_cursor_ptr;

/*
 * Transactional storage interface for storage component(s) to
 * implement.
 */
class Async_transactional_storage {
public:
    virtual ~Async_transactional_storage();

    static void getInstance(const container::Context*,
                            Async_transactional_storage*&);

    typedef boost::function<void(const Result&, 
                                 Async_transactional_connection_ptr&)>
    Get_connection_callback;

    /* Obtain a connection to the transactional storage. */
    virtual void get_connection(const Get_connection_callback&) const = 0;
};

/*
 * Connection to a transactional storage.
 *
 * The model: the connections remain in auto-commit mode until
 * application calls begin().  The auto-commit mode is re-entered once
 * commit()'d or rollback'ed().  All operations after begin() are
 * rollback'able().
 *
 * In auto-commit mode, all operations are executed as separate
 * transactions and no rollback nor commit calls are allowed.
 */
class Async_transactional_connection {
public:
    typedef boost::function<void(const Result&)> Begin_callback;

    typedef boost::function<void(const Result&, const Trigger_id&)>
    Put_trigger_callback;
    typedef boost::function<void(const Result&)> Remove_trigger_callback;
    typedef boost::function<void(const Result&)> Create_table_callback;
    typedef boost::function<void(const Result&)> Drop_table_callback;
    typedef boost::function<void(const Result&,
                                 const Async_transactional_cursor_ptr&)>
    Get_callback;

    typedef boost::function<void(const Result&, const GUID&)> Put_callback;
    typedef boost::function<void(const Result&)> Modify_callback;
    typedef boost::function<void(const Result&)> Remove_callback;

    typedef boost::function<void(const Result&)> Commit_callback;
    typedef boost::function<void(const Result&)> Rollback_callback;

    /* Destructor will rollback the transaction, if not committed. */
    virtual ~Async_transactional_connection();

    enum Transaction_mode { AUTO_COMMIT = 0, DEFERRED, EXCLUSIVE };

    /* Leave the auto-commit mode.
     *
     * After the call the application is required to call the commit()
     * or rollback() once done with the transaction.  Otherwise every
     * other applications will remain blocked in their access to the
     * database.
     *
     * The transaction may be opened in three different modes:
     *
     * - DEFERRED: no locks are acquired before the first actual
     *             operation, and even then, it's first opened for
     *             shared access (to support multiple concurrent
     *             reads) and moved to EXCLUSIVE as necessary.
     * - EXCLUSIVE: the transaction requires full exclusive access to
     *              the database right from the beginning. Prefer
     *              this, if the semantics of 'DEFERRED' mode are not
     *              100% obvious and 'AUTO_COMMIT' is not enough.
     * - AUTO_COMMIT: the operation does nothing.
     */
    virtual void begin(const Transaction_mode&, const Begin_callback&) = 0;

    /* Commit all changes since the begin() and return back to the
       auto-commit mode. Guaranteed to success, if there's a
       transaction to commit. */
    virtual void commit(const Commit_callback&) = 0;

    /* Rollback any changes since the previous commit and return back
       to the auto-commit mode. Guaranteed to success, if there's a
       transaction to rollback. */
    virtual void rollback(const Rollback_callback&) = 0;

    /* Return the mode of the connection. Guaranteed not to block. */
    virtual const Transaction_mode get_transaction_mode() = 0;

    /* Create a trigger for previous query results. */
    virtual void put_trigger(const Table_name&, const Row&,
                             const Trigger_function&,
                             const Put_trigger_callback&) = 0;

    /* Create a trigger for a table. */
    virtual void put_trigger(const Table_name&, const bool sticky,
                             const Trigger_function&,
                             const Put_trigger_callback&) = 0;

    /* Remove a trigger */
    virtual void remove_trigger(const Trigger_id&,
                                const Remove_trigger_callback&) = 0;

    virtual void create_table(const Table_name&, const Column_definition_map&,
                              const Index_list&, const int version,
                              const Create_table_callback&) = 0;

    virtual void drop_table(const Table_name&, const Drop_table_callback&) = 0;

    /* Query for row(s). */
    virtual void get(const Table_name&, const Query&, const Get_callback&) = 0;

    /* Insert a new row. */
    virtual void put(const Table_name&, const Row&, const Put_callback&) = 0;

    /* Modify an existing row */
    virtual void modify(const Table_name&, const Row&,
                        const Modify_callback&) = 0;

    /* Remove a row */
    virtual void remove(const Table_name&, const Row&,
                        const Remove_callback&) = 0;
};

/*
 * Getting a row (or more) from a database requires first opening a
 * cursor, which is then used to fetch the actual row(s).  Note that
 * it's essential to close cursor once the necessary rows have been
 * fetched.  If the cursor is not closed, other applications will
 * remain blocked in their access to the database.
 *
 * Note that due to the transaction semantics, one cannot iterate over
 * a row set and while iterating remove the rows. It's due to the fact
 * that writes require exclusive access to the database
 */
class Async_transactional_cursor {
public:
    virtual ~Async_transactional_cursor();

    typedef boost::function<void(const Result&, const Row&)> Get_next_callback;
    typedef boost::function<void(const Result&)> Close_callback;

    /* Get the next row. Note, if no row is found, the Result object
       will have a status code of NO_MORE_ROWS. */
    virtual void get_next(const Get_next_callback&) = 0;

    /* Release any database resources. Guaranteed to succeed, if the
       cursor is still open. */
    virtual void close(const Close_callback&) = 0;
};

} /* namespace storage */
} /* namespace applications */
} /* namespace vigil */

#endif
