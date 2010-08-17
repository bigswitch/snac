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
#ifndef MEMORY_HH 
#define MEMORY_HH 1

#include <utility>

#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>

#include "component.hh"
#include "dht-impl.hh"
#include "threads/cooperative.hh"
#include "transactional-storage.hh"

namespace vigil {
namespace applications {
namespace storage {

/**
 * A memory-based implementation of the multi key-value storage.
 */
class Async_DHT_storage 
    : public Async_storage,
      public container::Component {
public:
    Async_DHT_storage(const container::Context*,
                      const json_object*);

    void create_table(const Table_name&,
                      const Column_definition_map&,
                      const Index_list&,
                      const Create_table_callback&); 

    void drop_table(const Table_name&,
                    const Drop_table_callback&); 
    
    void get(const Table_name&,
             const Query&,
             const Get_callback&); 

    void get_next(const Context&,
                  const Get_callback&);
    
    void put(const Table_name&,
             const Row&,
             const Put_callback&);

    void modify(const Context&,
                const Row&,
                const Modify_callback&);
    
    void remove(const Context&, 
                const Remove_callback&);

    void put_trigger(const Context&,
                     const Trigger_function&,
                     const Put_trigger_callback&);

    void put_trigger(const Table_name&,
                     const bool sticky,
                     const Trigger_function&,
                     const Put_trigger_callback&);

    void remove_trigger(const Trigger_id&, 
                        const Remove_callback&); 

    void debug(const Table_name&);

protected:
    void configure(const container::Configuration*);
    void install();
    
private:
    bool validate_column_types(const Table_name&, const Column_value_map&,
                               const Result::Code&, 
                               const boost::function<void(const Result&)>&) 
        const;

    /* Determines the matching index for a query. */
    Index identify_index(const Table_name&, const Query&) const;

    typedef std::list<boost::function<void(const Put_callback)> > Put_list;
    void create_table_step(const Result&, const GUID&, const Put_list&, 
                           const boost::function<void(const Result)>&);
    void create_table_end(const Result&, const Table_name&,
                          const Column_definition_map&, const Index_list&,
                          const Create_table_callback&);
    void drop_table_step_0(const Result&, const Table_name&,
                           const Drop_table_callback&);
    void drop_table_step_1(const Result&, const Async_transactional_cursor_ptr&,
                           const Table_name&, const std::list<Table_name>&,
                           const boost::function<void(const Result)>&);
    void drop_table_step_2(const Result&, const Row&,
                           const Async_transactional_cursor_ptr& cur,
                           const Table_name&, const std::list<Table_name>&,
                           const boost::function<void(const Result)>&);
    void drop_table_step_3(const Result&, const Table_name&,
                           const std::list<Table_name>&,
                           const boost::function<void(const Result)>&);
    void drop_table_end(const Result&, const Table_name&, 
                        const Drop_table_callback&);
    
    /* Table schemas */
    typedef hash_map<Index_name, Index> Index_map;
    typedef std::pair<Column_definition_map, Index_map> Table_definition;
    typedef hash_map<Table_name, Table_definition> Table_definition_map;
    Table_definition_map tables;

    Index_list to_list(const Index_map&);

    /* Fake DHTs */
    hash_map<DHT_name, Content_DHT_ptr> content_dhts;
    hash_map<DHT_name, Index_DHT_ptr> index_dhts;

    /* Pointer to the persistent storage */
    Async_transactional_connection_ptr connection;

    /* Mutex protecting the table definitions and rings */
    mutable Co_mutex mutex;
};

} // namespace storage
} // namespace applications
} // namespace vigil

#endif
