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
#ifndef SQLITE3_IMPL_HH
#define SQLITE3_IMPL_HH 1

#include "sqlite3.h"

#include <list>
#include <vector>

#include <boost/function.hpp>
#include <boost/tuple/tuple.hpp>
#include <boost/weak_ptr.hpp>

#include "component.hh"
#include "hash_map.hh"
#include "hash_set.hh"
#include "threads/native-pool.hh"
#include "transactional-storage.hh"

namespace vigil {
namespace applications {
namespace storage {

/* SQLite based transactional multi key-value pair storage
 * implementation.
 *
 * All SQLite operations are blocking and hence are executed in a
 * native thread.  Moreover, since SQLite does not support row-level
 * write concurrency, only concurrent (read) operations are allowed.
 * It's the responsibility of the storage implementation to avoid
 * executing operations breaking SQLite's concurrency and transaction
 * model.  
 *
 * As a result, the storage implementation involves integration of a)
 * asynchronous code, b) native threads, c) database operation level
 * locking.  Therefore, the code involves a hefty amount of callbacks
 * and use of boost::bind().  Be warned.
 */

typedef boost::function<void()> Result_callback;
typedef std::list<Result_callback> Result_callback_list;

class SQLite_impl;
class SQLite_storage;
typedef Native_thread_pool<Result_callback, SQLite_impl> SQLite_impl_pool;

typedef int Cursor_id;
class Lock_manager;

class Lock_id {
public:
    Lock_id();
    Lock_id(const Lock_manager*, const int);
    void release() const;
    bool operator==(const Lock_id& other) const;

    int id;

    static const int NO_LOCK_ID;

private:
    static void timeout(const std::string&);
#ifndef NDEBUG
    mutable Timer timer;
    SQLite_storage* s;
#else
#ifdef PROFILING
    mutable Timer timer;
    SQLite_storage* s;
#endif
#endif
};

}
}
}

#include "hash.hh"
#include "fnv_hash.hh"

/* G++ 4.2+ has hash template specializations in std::tr1, while G++
   before 4.2 expect them to be in __gnu_cxx. Hence the namespace
   macro magic. */
ENTER_HASH_NAMESPACE
template<>
struct hash<vigil::applications::storage::Lock_id>
    : public std::unary_function<vigil::applications::storage::Lock_id, 
                                 std::size_t>
{      
    std::size_t
    operator()(const vigil::applications::storage::Lock_id& t) const {
        return vigil::fnv_hash(&t.id, sizeof(t.id));
    }
};

EXIT_HASH_NAMESPACE

namespace vigil {
namespace applications {
namespace storage {

class SQLite_connection;
class SQLite_cursor;
class Statement;

/* Lock manager guards the access to the SQLite database engine.
 * Multiple readers may share the access, but writers get exclusive
 * access.  This follows the concurrency and locking model of SQLite
 * and prevents the bindings from getting SQLITE_BUSY errors.
 */
class Lock_manager {
public:
    Lock_manager(SQLite_storage*);

    typedef boost::function<void(const Lock_id)> Callback;

    void get_shared(const Lock_id&, const Callback&) const;
    void get_exclusive(const Lock_id&, const Callback&) const;
    Lock_id release(const Lock_id&) const;

    static const Lock_id NO_LOCK;

protected:
    friend class Lock_id;

    SQLite_storage* is_lock_trace_enabled() const;

private:
    /* Every lock has a unique identifier. Allocate a new id. */
    Lock_id get_next_lock_id() const;

    typedef std::list<std::pair<Lock_id, Callback> > Waiter_queue;
    typedef hash_set<Lock_id> Lock_set;

    /* Queues for callbacks pending for a lock */
    mutable Waiter_queue pending_shared;
    mutable Waiter_queue pending_exclusive;

    /* Current lock (identifiers) holding the access. */
    mutable Lock_set shared;
    mutable Lock_set exclusive;

    mutable int next_lock_id;

    SQLite_storage* storage;
};

/* Public SQLite component for applications to access. */
class SQLite_storage
    : public Async_transactional_storage,
      public container::Component {
public:
    SQLite_storage(const container::Context*, const json_object*);

    /* Get a connection object to access the database. */
    void get_connection(const Get_connection_callback&) const;

    /* Get a database file location */
    std::string get_location() const;

protected:
    friend class SQLite_connection;
    friend class SQLite_cursor;
    friend class Lock_manager;

    void configure(const container::Configuration*);
    void install();

    /* Synchronization between the native thread running SQLite lite
       and the cooperative threads. */
    SQLite_impl_pool pool;

    /* Lock manager guarding the access to the SQLite engine. */
    const Lock_manager lockmgr;

    /* SQLite3 database file */
    std::string database;

    /* Whether lock tracking is enabled or not.  Set by giving
       "trace_locks" as a second parameter for the component. */
    bool trace_locks;
};

/* A cursor implementation wrapping an SQLite SELECT statement. */
class SQLite_cursor
    : public Async_transactional_cursor {
public:
    SQLite_cursor(boost::shared_ptr<SQLite_connection>, Statement*, 
                  const Cursor_id,
                  const Async_transactional_connection::Transaction_mode);
    ~SQLite_cursor();

    /* For the semantics of the operations, see the inherited
       class. */
    void get_next(const Get_next_callback&);
    void close(const Close_callback&);

protected:
    friend class SQLite_connection;

    /* Weak ptr to obtain shared_ptr's from */
    boost::weak_ptr<SQLite_cursor> weak_this;

    /* Connection this cursor was openend within */
    boost::shared_ptr<SQLite_connection> impl;

    /* If cursor open, a non-null ptr to a SQLite statement. */
    Statement* stmt;

    /* Unique per connection identifier for this cursor. */
    const Cursor_id cursor_id;

    /* Connection transaction mode at the time of cursor opening. */
    const Async_transactional_connection::Transaction_mode mode;
};

/* SQLite connection class shadows the locking and concurrency
 * mechanism implementation of SQLite itself (with the help of
 * Lock_manager) and only passes operations in a proper order to the
 * native thread running interacting with the actual SQLite engine.
 */
class SQLite_connection
    : public Async_transactional_connection {
public:
    /* Connection is always bound to a storage. */
    SQLite_connection(SQLite_storage*);

    /* Currently merely a placeholder. */
    ~SQLite_connection();

    /* For the semantics of the operations, see the inherited class. */

    void begin(const Transaction_mode&, const Begin_callback&);
    void commit(const Commit_callback&);
    const Transaction_mode get_transaction_mode();
    void put_trigger(const Table_name&, const Row&, const Trigger_function&,
                     const Put_trigger_callback&);
    void put_trigger(const Table_name&, const bool sticky,
                     const Trigger_function&, const Put_trigger_callback&);
    void remove_trigger(const Trigger_id&,
                        const Remove_trigger_callback&);
    void create_table(const Table_name&,
                      const Column_definition_map&,
                      const Index_list&,
                      const int version,
                      const Create_table_callback&);
    void drop_table(const Table_name&,
                    const Drop_table_callback&);
    void get(const Table_name&, const Query&, const Get_callback&);
    void cursor_closed(const boost::shared_ptr<SQLite_cursor>&,
                       const Async_transactional_connection::
                       Transaction_mode& mode, const Result_callback&);
    void put(const Table_name&, const Row&, const Put_callback&);
    void modify(const Table_name&, const Row&, const Modify_callback&);
    void remove(const Table_name&, const Row&, const Remove_callback&);
    void rollback(const Rollback_callback&);

protected:
    friend class SQLite_cursor;
    friend class SQLite_storage;

    /* Weak ptr to obtain shared_ptr's from */
    boost::weak_ptr<SQLite_connection> weak_this;

private:
    void lock_acquired(const Lock_id, const boost::function<void()>&);
    void allocate_cursor(const Result&, Statement*, 
                         const Async_transactional_connection::
                         Transaction_mode&, boost::shared_ptr<SQLite_cursor>, 
                         const Get_callback&);
    void store_cursor(Async_transactional_cursor_ptr, 
                       const boost::function<void()>&);
    void close_cursors(const Result&, const boost::function<void()>&);
    void release_lock(const Async_transactional_connection::Transaction_mode&, 
                      const Result_callback&);

    /* Storage this connection belongs to */
    SQLite_storage* storage;

    /* Cursors currently open */
    typedef hash_map<Cursor_id, Async_transactional_cursor_ptr> Cursor_map;
    Cursor_map cursors_open;

    /* The currently held lock */
    Lock_id lock_id;

    /* Any errors returned by the ... */
    Result result;

    /* Commit mode */
    Transaction_mode mode;

    /* Next cursor id */
    Cursor_id next_cursor_id;
};

/* SQLite (blocking) bindings executed in a native thread. */
class SQLite_impl {
public:
    SQLite_impl(SQLite_storage* s, const char* database = "");
    ~SQLite_impl();

    /* For get, transactional_connection default callback signature
       can't be used, since the native thread returns an internal
       presentation of a statement. */
    typedef boost::function<void(const Result&, Statement*)> Get_callback;

    typedef boost::function<void()> Callback;
    typedef std::vector<Callback> Callback_list;

    Result_callback
    begin(const Async_transactional_connection::Begin_callback&);
    Result_callback
    commit(const Async_transactional_connection::Commit_callback&);
    Result_callback rollback(const Async_transactional_connection::
                             Rollback_callback&);
    Result_callback put_trigger_1(const Async_transactional_connection::
                                  Transaction_mode&, const Table_name&,
                                  const Row&, const Trigger_function&,
                                  const Async_transactional_connection::
                                  Put_trigger_callback&);
    Result_callback put_trigger_2(const Async_transactional_connection::
                                  Transaction_mode&, const Table_name&,
                                  const bool sticky, const Trigger_function&,
                                  const Async_transactional_connection::
                                  Put_trigger_callback&);
    Result_callback remove_trigger(const Async_transactional_connection::
                                   Transaction_mode&, const Trigger_id&,
                                   const Async_transactional_connection::
                                   Remove_trigger_callback&);
    Result_callback create_table(const Async_transactional_connection::
                                 Transaction_mode&, const Table_name&,
                                 const Column_definition_map&,const Index_list&,
                                 const int version,
                                 const Async_transactional_connection::
                                 Create_table_callback&);
    Result_callback drop_table(const Async_transactional_connection::
                               Transaction_mode&, const Table_name&,
                               const Async_transactional_connection::
                               Drop_table_callback&);
    Result_callback get(const Table_name&, const Query&,const Get_callback&);
    Result_callback get_next(Statement*, const Async_transactional_cursor::
                             Get_next_callback&);
    Result_callback close(Statement*,
                          const Async_transactional_cursor::Close_callback&);
    Result_callback put(const Async_transactional_connection::Transaction_mode&,
                        const Table_name&, const Row&,
                        const Async_transactional_connection::Put_callback&);
    Result_callback modify(const Async_transactional_connection::
                           Transaction_mode&, const Table_name&, const Row&,
                           const Async_transactional_connection::
                           Modify_callback&);
    Result_callback remove(const Async_transactional_connection::
                           Transaction_mode&, const Table_name&, const Row&,
                           const Async_transactional_connection::
                           Remove_callback&);

    /* SQLite callbacks will invoke these */
    void insert_callback(const Table_name&, sqlite3_context*, int,
                         sqlite3_value**);
    void update_callback(const Table_name&, sqlite3_context*, int,
                         sqlite3_value**);
    void delete_callback(const Table_name&, sqlite3_context*, int,
                         sqlite3_value**);

protected:
    friend class Statement;

    /* Validates a row/query against the table definitions */
    void validate_column_types(const Table_name&,const Column_value_map&) const;

    void create_trigger_functions(const Table_name&, const Column_value_map&);

    /* Map the SQLite invoked table trigger to a row trigger call */
    void process_trigger(const Table_name&, const Column_value_map&,
                         const Trigger_reason);

    /* Auto-commit mode wrappers that execute explicit transaction
       management on behalf of the user, if the auto-commits are
       enabled. */
    void auto_begin(const Async_transactional_connection::Transaction_mode&);
    void auto_commit(const Async_transactional_connection::Transaction_mode&);
    void auto_rollback(const Async_transactional_connection::Transaction_mode&);

    /* Internal exception throwing transaction mgmt functions */
    void internal_begin();
    void internal_commit();
    void internal_rollback();

    typedef hash_map<Index_name, Index> Index_map;
    typedef std::pair<Column_definition_map, Index_map> Table_definition;
    typedef hash_map<Table_name, Table_definition> Table_definition_map;

    Index_list to_list(const SQLite_impl::Index_map&);

    /* Meta table memory replica mgmt functions */
    void store_table_definition(const Table_name&, const Table_definition&);
    void remove_table_definition(const Table_name&);

    boost::tuple<Trigger_function, Row, bool>
    internal_remove_trigger(const Trigger_id&);
    void internal_put_trigger(const Trigger_id&, const Row&, bool,
                              const Trigger_function&);
    Index identify_index(const Table_name&, const Query&) const;

    /* Table schemas */
    mutable Table_definition_map tables;

    /* Triggers */
    typedef boost::tuple<Trigger_id, Row, Trigger_function> Trigger_def;
    typedef std::vector<Trigger_def> Trigger_def_list;
    typedef hash_map<Table_name, Trigger_def_list> Table_trigger_map;
    Table_trigger_map table_triggers;
    Table_trigger_map sticky_table_triggers;
    typedef hash_map<GUID, Trigger_def_list> GUID_trigger_map;
    typedef hash_map<Index_name, GUID_trigger_map> Index_trigger_map;
    hash_map<Table_name, Index_trigger_map> row_triggers;

    /* Next trigger identifier to assign for a new user level
       trigger. */
    int64_t next_tid;

    /* SQLite table trigger invoked user row and table trigger
       invocations gathered during the execution of a SQL command. */
    Callback_list invoked_triggers;

    /* Function to construct a single callback out of all the gathered
       trigger invocations to be passed out of the native thread pool. */
    Result_callback gather_callbacks(const Callback&);

    /* For all operations to memory based data structures, the
       corresponding undo operations are stored into the rollback
       log. */
    Callback_list rollback_log;

    /* Don't use this in anything else but in result callbacks which
       are *not* executed in the native thread. */
    SQLite_storage* storage;

    /* SQLite engine */
    sqlite3* sqlite;
};

/*
 * SQLite C/C++ statement.
 */
class Statement {
public:
    Statement(SQLite_impl*, sqlite3*, const Table_name&);
    ~Statement();
    void get(const Query&);
    Row get_next();
    GUID put(const Row&);
    void modify(const Row&);
    void remove(const Row&);

private:
    void check_row_exists(const Row&);

    SQLite_impl* impl;
    sqlite3* sqlite;
    sqlite3_stmt* stmt;
    const Table_name table;
};

}
}
}

#endif
