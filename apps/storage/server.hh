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
#ifndef NDB_SERVER_HH
#define NDB_SERVER_HH 1

#include <list>
#include <string>
#include <utility>

#include <boost/shared_ptr.hpp>

#include <xercesc/dom/DOM.hpp>

#include "component.hh"
#include "connection.hh"
#include "hash_set.hh"
#include "listener.hh"
#include "storage.hh"
#include "threads/cooperative.hh"

namespace vigil { 
namespace applications { 
namespace storage {

class Server;

typedef boost::shared_ptr<Result_message> Result_message_ptr;

/*
 * Client servant thread.
 */
class Servant 
    : public Co_thread,
      public Callbacks {
public:
    Servant(Server*, std::auto_ptr<Tcp_socket>);
    
    /* Message processor thread main() */
    void run();

    /* Callback methods follow */

    void process(Create_table_message*);
    void process(Drop_table_message*);
    void process(Get_message*);
    void process(Get_next_message*);
    void process(Put_message*);
    void process(Modify_message*);
    void process(Remove_message*);
    void process(Put_row_trigger_message*);
    void process(Trigger_message*);

private:
    void generic_callback(const Message::Message_id&, const Result&);
    void get_callback(const Message::Message_id&, const Result&, const Context&,
                      const Row&);
    void put_callback(const Message::Message_id&, const Result&, const GUID&);
    void modify_callback(const Message::Message_id&, const Result&, 
                         const Context&);
    void put_trigger_callback(const Message::Message_id&, const Result&,
                              const Trigger_id&);
    void send_trigger_call(const bool, const Trigger_id&, const Row&);

    /* Socket listening server component */
    Server* server;

    /* Pointer to self */
    //boost::shared_ptr<Servant> servant_ptr;

    hash_set<Trigger_id> triggers;
};

/*
 * Listener component for inbound TCP connections.
 */
class Server
    : public vigil::container::Component, Listener<Servant> {
public:
    Server(const container::Context*,
           const xercesc::DOMNode*);
    
    void configure(const container::Configuration*);
    void install();

protected:
    friend class Servant;

    boost::shared_ptr<Servant> get_servant(std::auto_ptr<Tcp_socket>);

    /* Local network database provider component */
    Async_storage* storage;
};

} // namespace storage
} // namespace applications
} // namespace vigil

#endif
