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
#ifndef NDB_CLIENT_HH
#define NDB_CLIENT_HH 1

#include <boost/shared_ptr.hpp>

#include "component.hh"
#include "connection.hh"
#include "netinet++/ipaddr.hh"
#include "storage.hh"
#include "threads/cooperative.hh"
#include "timer-dispatcher.hh"

namespace vigil { 
namespace applications { 
namespace storage {

class Connecting;

/**
 * Storage client provides the storage interface towards a remote
 * storage backend instance.
 */
class Async_client
    : public Co_thread,
      public vigil::container::Component, 
      public Async_storage,
      public Callbacks {
public:
    Async_client(const container::Context*,
                 const xercesc::DOMNode*);
    
    void configure(const container::Configuration*);
    void install();

    /* Storage API */

    void create_table(const Table_name&, const Column_definition_map&,
                      const Index_list&, const Create_table_callback&);
    void drop_table(const Table_name&, const Drop_table_callback&);
    void get(const Table_name&, const Query&, const Get_callback&);
    void get_next(const Context&, const Get_callback&);
    void put(const Table_name&, const Row&, const Put_callback&); 
    void modify(const Context&, const Row&, const Modify_callback&);
    void remove(const Context&, const Remove_callback&);
    void put_trigger(const Context&, const Trigger_function&,
                     const Put_trigger_callback&); 
    void put_trigger(const Table_name&, const bool, const Trigger_function&,
                     const Put_trigger_callback&); 
    void remove_trigger(const Trigger_id&, const Remove_trigger_callback&);

    /* Callbacks */

    void disconnected();
    void process(Create_table_message*);
    void process(Drop_table_message*);
    void process(Get_message*);
    void process(Get_next_message*);
    void process(Put_message*);
    void process(Modify_message*);
    void process(Remove_message*);
    void process(Put_row_trigger_message*);
    void process(Trigger_message*);

protected:
    int connect();
    
    friend class Connecting;

private:
    void generic_callback(const Async_storage::Create_table_callback&,
                          Message_ptr);
    void get_callback(const Async_storage::Get_callback&, Message_ptr);
    void put_callback(const Async_storage::Put_callback&, const GUID&,
                      Message_ptr);
    void modify_callback(const Async_storage::Modify_callback&, Message_ptr);
    void put_trigger_callback(const Trigger_function&,
                              const Async_storage::Put_trigger_callback&,
                              Message_ptr);

    /* Connection management is run in a dedicated thread */
    void run();

    /* Remote NDB master address */
    ipaddr host;
    uint16_t port;

    /* Mutex protecting the queue */
    Co_mutex mutex;

    hash_map<Trigger_id, std::pair<Trigger_function, bool> > triggers;
    
    Timer_dispatcher* dispatcher;
};

/**
 * State to connect to a remote host.  For a client to initiate a
 * connection.
 */
class Connecting
    : public State {
public:
    Connecting(Async_client*);
    State* advance();

private:
    Async_client* client;

    ipaddr ip;
    uint16_t port;
};

} // namespace storage
} // namespace applications
} // namespace vigil

#endif
