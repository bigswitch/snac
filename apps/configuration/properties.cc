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
#include <string>

#include <boost/foreach.hpp>
#include <inttypes.h>

#include "configuration.hh"
#include "properties.hh"
#include "storage/transactional-storage.hh"
#include "storage/transactional-storage-blocking.hh"
#include "threads/cooperative.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::configuration;
using namespace vigil::applications::storage;

static Vlog_module lg("properties");

Properties::Properties(storage::Async_transactional_storage* storage_,
                       const Section_id& section_id_, 
                       const Properties::Default_value_map& defaults) 
    : storage(storage_), section_id(section_id_), in_transaction(false) {
    /* Nothing else to do */

    BOOST_FOREACH(Default_value_map::value_type v, defaults) {
        const Key& key = v.first;
        const std::vector<Property>& values = v.second;

        Property_list_ptr n(new Property_list(this, true));
        BOOST_FOREACH(Property p, values) {
            /* Be paranoid and reconstruct the property values */
            n->push_back(Property(p.get_value()));
        }

        this->defaults[key] = n;
    }
}

static
void
generic_callback(const Result& result,
                 const vigil::applications::configuration::Callback& cb,
                 const Errback& eb){
    if (result.is_success()) {
        cb();
    } else {
        eb();
    }
}

void
Properties::async_add_callback(const Callback& trigger,
                               const Add_callback_callback& cb, 
                               const Errback& eb) {
    // Calling sequence:
    // 1. storage->get_connection
    // 2. cache_connection
    // 3. storage->put_trigger
    // 4. trigger_callback
    Callback do_add_begin =
        boost::bind(&Properties::add_callback_callback, this, trigger, cb, eb);
    storage->get_connection(boost::bind(&Properties::cache_connection,
                                        this, _1, _2, do_add_begin, eb));
}

void
Properties::add_callback_callback(const Callback& trigger,
                                  const Add_callback_callback& cb,
                                  const Errback& eb) {
    Async_transactional_connection::Put_trigger_callback put_trigger_cb =
        boost::bind(&Properties::trigger_callback, this, _1, _2, cb, eb);

    Query q;
    q[Configuration::COL_SECTION] = section_id;

    storage::Trigger_function tf =
        boost::bind(&Properties::trigger_processor, this, _1, _2, _3, trigger);

    connection->put_trigger(Configuration::TABLE, q, tf, put_trigger_cb);
}

void
Properties::trigger_callback(const Result& result, const Trigger_id& tid,
                             const Add_callback_callback& cb,
                             const Errback& eb) {
    if (!result.is_success()) {
        eb();
    } else {
        cb(tid);
    }
}

void
Properties::trigger_processor(const Trigger_id&, const Row&,
                              const Trigger_reason, const Callback& trigger) {
    trigger();
}

void
Properties::async_begin(const Callback& cb, const Errback& eb) {
    lg.dbg("async_begin():");

    // Calling sequence:
    // 1. storage->get_connection
    // 2. cache_connection
    // 3. storage->begin
    // 4. generic callback
    // 5. refresh
    // 6. update snapshot
    Callback update_snapshot = 
        boost::bind(&Properties::update_snapshot, this, cb);

    Callback do_refresh = boost::bind(&Properties::refresh, this, cb, eb);

    Async_transactional_connection::Begin_callback begin_cb =
        boost::bind(&Properties::async_begin_callback, this, _1, 
                    do_refresh, eb);
    Callback do_begin = boost::bind(&Properties::call_begin, this, begin_cb);
    storage->get_connection(boost::bind(&Properties::cache_connection,
                                        this, _1, _2, do_begin, eb));
}

void
Properties::call_begin(Async_transactional_connection::Begin_callback& cb) {
    lg.dbg("call_begin");
    connection->begin(Async_transactional_connection::EXCLUSIVE, cb);
}

void
Properties::async_begin_callback(const Result& result, const Callback& cb,
                                 const Errback& eb){
    lg.dbg("async_begin_callback");
    if (!result.is_success()) {
        eb();
    } else {
        in_transaction = true;
        cb();
    }
}

void
Properties::update_snapshot(const Callback& cb) {
    kvp_snapshot.clear();

    // Can't just copy the entire hash map since it's storing pointers
    // to property lists.
    BOOST_FOREACH(KVP_hash_map::value_type& v, kvp) {
        Property_list_ptr n(new Property_list(this));
        *n = *v.second;
        kvp_snapshot[v.first] = n;
    }
}

void
Properties::cache_connection(const Result& result,
                             Async_transactional_connection_ptr& connection,
                             const Callback& cb, const Errback& eb) {
    lg.dbg("cache_connection():");

    if (!result.is_success()) {
        eb();
    } else {
        this->connection = connection;
        cb();
    }
}

void
Properties::async_load(const Callback& cb, const Errback& eb) {
    lg.dbg("async_load():");

    Callback do_refresh = boost::bind(&Properties::refresh, this, cb, eb);
    storage->get_connection(boost::bind(&Properties::cache_connection,
                                        this, _1, _2, do_refresh, eb));
}

void
Properties::refresh(const Callback& cb, const Errback& eb) {
    lg.dbg("refresh():");

    // Calling sequence:
    // 1. connection->get
    // 2. get_callback
    // 3. cursor->get_next (loop as many times as necessary)
    // 4. get_close
    // 5. generic_callback
    kvp.clear();

    // Initialize the kvp's with the default values, to be overriden
    // with the ones found in the database (if any).  Note, we can't
    // just copy the entire hash map since it's storing pointers to
    // property lists.
    BOOST_FOREACH(KVP_hash_map::value_type& v, defaults) {
        Property_list_ptr n(new Property_list(this, true));
        *n = *v.second;
        kvp[v.first] = n;
    }

    Query query;
    query[Configuration::COL_SECTION] = section_id;

    Async_transactional_connection::Get_callback get_cb =
        boost::bind(&Properties::get_callback, this, _1, _2, cb, eb);
    connection->get(Configuration::TABLE, query, get_cb);
}

void
Properties::get_callback(const Result& result,
                         const Async_transactional_cursor_ptr& cursor,
                         const Callback& cb, const Errback& eb) {
    lg.dbg("get_callback: %d", result.code);
    
    if (!result.is_success()) {
        eb();
        return;
    }

    cursor->get_next(boost::bind(&Properties::get_next_callback, this,
                                 _1, _2, cursor, cb, eb));
}

void
Properties::get_next_callback(const Result& result, const Row& row,
                              const Async_transactional_cursor_ptr& cursor,
                              const Callback& cb, const Errback& eb) {
    lg.dbg("get_next_callback: %d", result.code);

    if (result.code == Result::NO_MORE_ROWS) {
        get_close(cursor, cb, eb);
        return;
    }

    if (!result.is_success()) {
        get_close(cursor, eb, eb); /* Call the errback in any case */
        return;
    }

    process(row);
    cursor->get_next(boost::bind(&Properties::get_next_callback, this,
                                 _1, _2, cursor, cb, eb));
}

/*
 * Synchronous row processor
 */
void
Properties::process(const Row& row) {
    Key key = boost::get<Key>(row.find(Configuration::COL_KEY)->second);
    KVP_hash_map::iterator i = kvp.find(key);
    Property_list_ptr values = i == kvp.end() || i->second->default_values ? 
        Property_list_ptr(new Property_list(this)) : i->second;

    int64_t order =
        boost::get<int64_t>(row.find(Configuration::COL_VALUE_ORDER)->second);
    if (values->size() <= order) {
        values->resize(order + 1);
    }

    (*values)[order] = Property(row);
    kvp[key] = values;
}

static
void
cursor_closed(const Result& result,
              const Async_transactional_cursor_ptr& cursor,
              const vigil::applications::configuration::Callback& cb,
              const Errback& eb) {
    generic_callback(result, cb, cb);
}

void
Properties::get_close(const Async_transactional_cursor_ptr& cursor,
                      const Callback& cb, const Errback& eb) {
    lg.dbg("get_close");

    const Async_transactional_cursor::Close_callback close_cb =
        boost::bind(&cursor_closed, _1, cursor, cb, eb);
    cursor->close(close_cb);
}

static
void
remove_row(Async_transactional_connection_ptr& connection, const GUID& guid,
           const vigil::applications::configuration::Callback& cb,
           const Errback& eb) {
    Row row;
    row["GUID"] = guid;
    connection->remove(Configuration::TABLE, row,
                       boost::bind(&generic_callback, _1, cb, eb));
}

void
Properties::async_commit(const Callback& cb, const Errback& eb) {
    lg.dbg("async_commit");

    assert(in_transaction);

    // Calling sequence
    // 1. delete_rows
    // 2. put/modify rows
    // 3. commit
    // - if error, rollback

    // Gather rows to put/modify
    Operation_list operations;
    BOOST_FOREACH(KVP_hash_map::value_type& i, kvp) {
        int k = 0;
        for (Property_list::iterator j = i.second->begin();
             j != i.second->end(); ++j, ++k) {
            operations.
                push_back(boost::bind(&Property::put_or_modify, &(*j),
                                      connection, section_id, i.first, k,
                                      _1, _2));
        }
    }

    BOOST_FOREACH(const GUID& guid, deleted) {
        operations.
            push_back(boost::bind(&remove_row, connection, guid, _1, _2));
    }

    Async_transactional_connection::Commit_callback commit_cb =
        boost::bind(&Properties::commit_callback_callback, this, _1, cb, eb);
    Callback do_commit = 
        boost::bind(&Async_transactional_connection::commit, connection, 
                    commit_cb);

    if (operations.empty()) {
        do_commit();
    } else {
        Callback rollback_cb = 
            boost::bind(&Properties::async_rollback, this, eb, eb);
        op(operations, do_commit, rollback_cb);
    }
}

void
Properties::commit_callback_callback(const Result& result,
                 const vigil::applications::configuration::Callback& cb,
                 const Errback& eb){
    if (result.is_success()) {
        deleted.clear();
        cb();
    } else {
        eb();
    }
}

void
Properties::op(Operation_list& operations,
               const Callback& cb, const Errback& eb) {
    lg.dbg("op():");
    Storage_operation_callback f = operations.back();
    operations.pop_back();

    Callback next_op =
        operations.empty() ?
        cb : 
        boost::bind(&Properties::op, this, operations, cb, eb);

    f(next_op, eb);
}

void
Properties::async_rollback(const Callback& cb, const Errback& eb) {
    lg.dbg("async_rollback");

    assert(in_transaction);

    deleted.clear();
    kvp = kvp_snapshot;
    in_transaction = false;

    connection->rollback(boost::bind(&generic_callback, _1, cb, eb));
}

const Property_list_ptr
Properties::get_value(const Key& key) {
    if (kvp.find(key) == kvp.end()) {
        Property_list_ptr v = Property_list_ptr(new Property_list(this));
        kvp[key] = v;
        return v;
    }

    return kvp.find(key)->second;
}

void
Properties::remove_value(const Key& key) {
    assert(in_transaction);

    KVP_hash_map::iterator i = kvp.find(key);
    if (i == kvp.end()) {
        return;
    }

    i->second->clear();

    kvp.erase(i);
}


vector<Key> Properties::get_loaded_keys() { 
  vector<Key> keys; 
  KVP_hash_map::iterator it; 
  for(it = kvp.begin(); it != kvp.end(); ++it) { 
    keys.push_back(it->first); 
  } 
  return keys; 
}

static
void 
sync_callback(Co_sema* sem, bool* ret) {
    *ret = true;
    sem->up();
}

static
void 
sync_add_callback_callback(const Properties::Callback_id& id, Co_sema* sem, 
                           boost::tuple<bool, Properties::Callback_id>* ret) {
    *ret = boost::tuple<bool, Properties::Callback_id>(true, id);
    sem->up();
}

static
void 
sync_errback(Co_sema* sem, bool* ret) {
    *ret = false;
    sem->up();
}

const boost::tuple<bool, Properties::Callback_id>
Properties::add_callback(const Callback& trigger) {
    Co_sema sem;
    boost::tuple<bool, Properties::Callback_id> 
        result(false, Properties::Callback_id());
    bool ignore;

    async_add_callback(trigger, boost::bind(&sync_add_callback_callback, _1, 
                                            &sem, &result),
                       boost::bind(&sync_errback, &sem, &ignore));
    sem.down();
    return result;
}

bool
Properties::load() {
    Co_sema sem;
    bool result;
    async_load(boost::bind(&sync_callback, &sem, &result),
               boost::bind(&sync_errback, &sem, &result));
    sem.down();
    return result;
}

bool
Properties::begin() {
    Co_sema sem;
    bool result;
    async_begin(boost::bind(&sync_callback, &sem, &result),
                boost::bind(&sync_errback, &sem, &result));
    sem.down();
    return result;
}

bool
Properties::commit() {
    Co_sema sem;
    bool result;
    async_commit(boost::bind(&sync_callback, &sem, &result),
                 boost::bind(&sync_errback, &sem, &result));
    sem.down();
    return result;
}

bool
Properties::rollback() {
    Co_sema sem;
    bool result;
    async_rollback(boost::bind(&sync_callback, &sem, &result),
                   boost::bind(&sync_errback, &sem, &result));
    sem.down();
    return result;
}

Property::Property()
    : persistent(false), dirty(false) {

}

Property::Property(const storage::Row& row)
    : persistent(true), dirty(false) {

    int64_t type =
        boost::get<int64_t>
        (row.find(Configuration::COL_VALUE_TYPE)->second);
    if (type == Configuration::VAL_TYPE_INT) {
        value = row.find(Configuration::COL_VALUE_INT)->second;
    } else if (type == Configuration::VAL_TYPE_FLOAT) {
        value = row.find(Configuration::COL_VALUE_FLOAT)->second;
    } else if (type == Configuration::VAL_TYPE_STR) {
        value = row.find(Configuration::COL_VALUE_STR)->second;
    } else {
        lg.err("Invalid property type in database: %"PRId64, type);
    }

    guid = boost::get<GUID>(row.find("GUID")->second);
}

Property::Property(const Value& value_)
    : value(value_), persistent(false), dirty(true) {
}

void
Property::set_value(const Value& value_) {
    dirty = true;
    value = value_;
}

const Property::Value
Property::get_value() const {
    return value;
}

void
Property::put_or_modify(Async_transactional_connection_ptr& connection,
                        const Section_id& section_id,
                        const Key& key,
                        const int order,
                        const Callback& cb,
                        const Errback& eb) {
    Row row;
    Column_type_collector c;
    boost::apply_visitor(c, value);

    row[Configuration::COL_SECTION] = section_id;
    row[Configuration::COL_KEY] = key;
    row[Configuration::COL_VALUE_ORDER] = (int64_t)order;
    row[Configuration::COL_VALUE_TYPE] = c.type;

    if (c.type == Configuration::VAL_TYPE_INT) {
        row[Configuration::COL_VALUE_INT] = boost::get<int64_t>(value);;
    } else if (c.type == Configuration::VAL_TYPE_STR) {
        row[Configuration::COL_VALUE_STR] = boost::get<string>(value);;
    } else if (c.type == Configuration::VAL_TYPE_FLOAT) { 
        row[Configuration::COL_VALUE_FLOAT] = boost::get<double>(value);;
    } else {
        lg.err("Invalid property type in database: %"PRId64, c.type);
        eb();
        return;
    }

    if (persistent) {
        row["GUID"] = guid;
        connection->modify(Configuration::TABLE, row,
                           boost::bind(&Property::put_callback, this,
                                       _1, this->guid, cb, eb));
    } else {
        connection->put(Configuration::TABLE, row,
                        boost::bind(&Property::put_callback, this, _1, _2,
                                    cb, eb));
    }
}

void
Property::put_callback(const Result& result, const GUID& guid,
                       const Callback& cb, const Errback& eb) {
    if (!result.is_success()) {
        eb();
    } else {
        this->guid = guid;
        this->persistent = true;
        this->dirty = false;
        cb();
    }
}

Property_list::Property_list(Properties* p_)
    : default_values(false), p(p_) {
}

Property_list::Property_list(Properties* p_, bool default_values_)
    : default_values(true), p(p_) {
}

void
Property_list::clear() {
    // Mark every value in the property list deleted
    BOOST_FOREACH(Property& v, values) {
        if (v.persistent) {
            p->deleted.push_back(v.guid);
        }
    }

    values.clear();
}

Property_list::iterator 
Property_list::begin() {
    return values.begin();
}

Property_list::iterator 
Property_list::end() {
    return values.end();
}

size_t
Property_list::size() {
    return values.size();
}

void
Property_list::resize(int n) {
    values.resize(n);
}

Property& 
Property_list::operator[](size_t i) {
    return values[i];
}

void
Property_list::push_back(const Property& v) {
    values.push_back(v);
}

const Property
Property_list::pop_back() {
    Property v = values.back();
    p->deleted.push_back(v.guid);
    v.persistent = false;
    values.pop_back();
    return v;
}

const Property
Property_list::pop_front() { 
  Property v = values.front(); 
  p->deleted.push_back(v.guid); 
  v.persistent = false; 
  values.erase(values.begin()); 
  return v; 
} 
