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
#ifndef PROPERTIES_HH
#define PROPERTIES_HH 1

#include <string>
#include <vector>

#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <boost/tuple/tuple.hpp>
#include <boost/variant.hpp>

#include "hash_map.hh"
#include "storage/transactional-storage.hh"

namespace vigil {
namespace applications {
namespace configuration {

typedef std::string Section_id;
typedef std::string Key;
typedef boost::function<void()> Callback;
typedef boost::function<void()> Errback;


class Properties;
class Property_list;

/* Every property value is represented by a Property instance. */
class Property {
public:
    typedef storage::Column_value Value;

    Property();
    Property(const Value&);
    void set_value(const Value&);
    const Value get_value() const;

protected:
    friend class Properties;
    friend class Property_list;

    Value value;
    storage::GUID guid;
    bool persistent;

    Property(const storage::Row&);

    void put_or_modify(storage::Async_transactional_connection_ptr&,
                       const Section_id&,
                       const Key&,
                       const int order,
                       const Callback&,
                       const Errback&);

private:
    void put_callback(const storage::Result&, const storage::GUID&,
                      const Callback&, const Errback&);

    bool dirty;
};

/* In the Properties class below, all property values corresponding to
 * a key are stored into a vector like structure, which is ordered.
 */
class Property_list {
public:
    typedef std::vector<Property>::iterator iterator;

    Property_list(Properties*);

    /* See the STL vector documentation for the syntax of the
       following methods. */

    void clear();
    iterator begin();
    iterator end();
    size_t size();
    void resize(int n);
    Property& operator[](size_t);
    void push_back(const Property&);
    const Property pop_front(); 
    const Property pop_back();

protected:
    friend class Properties;

    Property_list(Properties*, bool);
    bool default_values;

private:
    Properties* p;
    std::vector<Property> values;
};

typedef boost::shared_ptr<Property_list> Property_list_ptr;

/* Object-oriented interface to the PROPERTIES table in the
 * configuration database.
 *
 * To load the values in from the database, the application must call
 * load() method. If the values are to be modified, the application
 * must open a transaction (with begin()) before loading and modifying
 * values.  Once done, the values have to be committed (or rollbacked)
 * to the database.
 *
 * Methods returning a deferred (begin(), commit(), rollback(), and
 * load()) do not support concurrent access.  Application can issue
 * only a single blocking operation at a time for the class.
 *
 * N.B. Nothing prevents application accessing the PROPERTIES table
 *      directly, as long as the transactional semantics are obeyed: a
 *      single transaction should not leave the application-level
 *      configuration in inconsistent state, ever.
 */
class Properties {
public:
    typedef storage::Trigger_id Callback_id;
    typedef boost::function<void(const Callback_id&)> Add_callback_callback;

    typedef hash_map<Key, std::vector<Property> > Default_value_map;

    Properties(storage::Async_transactional_storage*, const Section_id&, 
               const Default_value_map& defaults = Default_value_map());

    /* Adds a callback to be called at most once the database contents
     * have changed for the property section.  Returns a callback id
     * to use when removing the callback.  
     */
    void async_add_callback(const Callback& trigger, 
                            const Add_callback_callback&, const Errback&);

    /* Update the properties from the database.  Doesn't require
       transaction to be open. */
    void async_load(const Callback&, const Errback&);

    /* Prepare the properties for modifications by opening a
       transaction.  Loads the latest values from the database. */
    void async_begin(const Callback&, const Errback&);

    /* Commit the changes to the database.  Properties can't be edited
       after the commit. */
    void async_commit(const Callback&, const Errback&);

    /* Abort the done changes.  Properties can't be edited after the
       commit. */
    void async_rollback(const Callback&, const Errback&);

    /* Synchronous method counterpairs for the above asynchronous
       methods. Return true if successful.  */

    /* Add a callback to detect changes in the configuration table.
       Callback id can be used to unregister configuration change
       trigger. */
    const boost::tuple<bool, Callback_id> add_callback(const Callback&);

    bool load();
    bool begin();
    bool commit();
    bool rollback();

    /* Get properties corresponding a key.  The properties can be
     * edited in place. */
    const Property_list_ptr get_value(const Key&);

    /* Remove values corresponding the key. */
    void remove_value(const Key&); 

    /* Inefficient hack to avoid writing an iterator  */ 
    std::vector<Key> get_loaded_keys(); 

protected:
    friend class Property_list;

    typedef std::vector<storage::GUID> GUID_list;
    GUID_list deleted;

private:
    void commit_callback_callback(const storage::Result&, const Callback&,
                                  const Errback&);
    void add_callback_callback(const Callback& trigger,
                               const Add_callback_callback&, const Errback&);
    void trigger_callback(const storage::Result&, const storage::Trigger_id&,
                          const Add_callback_callback&, const Errback&);
    void trigger_processor(const storage::Trigger_id&, const storage::Row&,
                           const storage::Trigger_reason,
                           const Callback& trigger);
    void call_begin(storage::Async_transactional_connection::Begin_callback&);
    void async_begin_callback(const storage::Result&, const Callback&,
                              const Errback&);
    void update_snapshot(const Callback&);
    void cache_connection(const storage::Result&,
                          storage::Async_transactional_connection_ptr&,
                          const Callback&, const Errback&);
    void get_callback(const storage::Result&,
                      const storage::Async_transactional_cursor_ptr&,
                      const Callback&, const Errback&);
    void get_next_callback(const storage::Result&, const storage::Row&,
                           const storage::Async_transactional_cursor_ptr&,
                           const Callback&, const Errback&);
    void get_close(const storage::Async_transactional_cursor_ptr&,
                   const Callback&, const Errback&);
    void process(const storage::Row&);

    typedef boost::function<void(const Callback&, const Errback&)>
        Storage_operation_callback;
    typedef std::vector<Storage_operation_callback> Operation_list;

    void op(Operation_list&, const Callback&, const Errback&);
    void refresh(const Callback&, const Errback&);

    storage::Async_transactional_storage* storage;
    storage::Async_transactional_connection_ptr connection;

    const Section_id section_id;

    typedef hash_map<Key, Property_list_ptr> KVP_hash_map;
    KVP_hash_map kvp;

    /* Applications default values to use if key(s) not found in the
       database */
    KVP_hash_map defaults;

    /* In the beginning of the transaction, a snapshot of the current
       state is stored for rollbacking purposes. */
    KVP_hash_map kvp_snapshot;

    /* True if begin() has been called and the properties can be
       modified. */
    bool in_transaction;
};

}
}
}

#endif /* PROPERTIES_HH */
