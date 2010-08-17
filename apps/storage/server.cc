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
#include "server.hh"

#include <stdexcept>

#include <boost/bind.hpp>
#include <boost/lexical_cast.hpp>

#include "buffer.hh"
#include "connection.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace vigil::applications::storage;

static Vlog_module lg("ndb-listener");

Servant::Servant(Server* server_, auto_ptr<Tcp_socket> socket_) 
    : server(server_) {
    sock = socket_;
}

static void empty_callback(const Result&) { }

void 
Servant::run() {
    run_connection(new InitiateHandshake(this));

    /* Remove any pending triggers */
    for (hash_set<Trigger_id>::iterator i = triggers.begin(); 
         i != triggers.end(); ++i) {
        server->storage->remove_trigger(*i, &empty_callback);
    }
}

void
Servant::generic_callback(const Message::Message_id& req_id, 
                          const Result& result) {
    Result_message* msg = new Result_message();
    msg->ack_id = req_id;
    msg->result = result;
    enqueue(Message_ptr(msg), 0);
} 

void
Servant::process(Create_table_message* msg) {
    Async_storage::Create_table_callback f = 
        boost::bind(&Servant::generic_callback, this, msg->req_id, _1);
    server->storage->create_table(msg->table, msg->columns, msg->indices, f);
}


void
Servant::process(Drop_table_message* msg) {
    Async_storage::Drop_table_callback f = 
        boost::bind(&Servant::generic_callback, this, msg->req_id, _1);
    server->storage->drop_table(msg->table, f);
}

void
Servant::get_callback(const Message::Message_id& req_id, 
                      const Result& result,
                      const Context& ctxt, 
                      const Row& row) {
    Get_result_message* msg = new Get_result_message();
    msg->ack_id = req_id;
    msg->result = result;
    msg->row = row;
    enqueue(Message_ptr(msg), 0);
}

void
Servant::process(Get_message* msg) {
    Async_storage::Get_callback f = 
        boost::bind(&Servant::get_callback, this, msg->req_id, _1, _2, _3);
    server->storage->get(msg->table, msg->query, f);
}

void
Servant::process(Get_next_message* msg) {
    Async_storage::Get_callback f = 
        boost::bind(&Servant::get_callback, this, msg->req_id, _1, _2, _3);
    server->storage->get_next(msg->ctxt, f);
}

void
Servant::put_callback(const Message::Message_id& req_id, 
                      const Result& result,
                      const GUID& guid) {
    Put_result_message* msg = new Put_result_message();
    msg->ack_id = req_id;
    msg->result = result;
    msg->guid = guid;
    enqueue(Message_ptr(msg), 0);
}

void
Servant::process(Put_message* msg) {
    Async_storage::Put_callback f = 
        boost::bind(&Servant::put_callback, this, msg->req_id, _1, _2);
    server->storage->put(msg->table, msg->row, f);
}

void
Servant::modify_callback(const Message::Message_id& req_id, 
                         const Result& result,
                         const Context& ctxt) {
    Modify_result_message* msg = new Modify_result_message();
    msg->ack_id = req_id;
    msg->result = result;
    msg->ctxt = ctxt;
    enqueue(Message_ptr(msg), 0);
}

void
Servant::process(Modify_message* msg) {
    Async_storage::Modify_callback f = 
        boost::bind(&Servant::modify_callback, this, msg->req_id, _1, _2);
    server->storage->modify(msg->ctxt, msg->row, f);
}

void
Servant::process(Remove_message* msg) {
    Async_storage::Remove_callback f = 
        boost::bind(&Servant::generic_callback, this, msg->req_id, _1);
    server->storage->remove(msg->ctxt, f);
}

void
Servant::put_trigger_callback(const Message::Message_id& req_id, 
                              const Result& result,
                              const Trigger_id& tid) {
    Put_trigger_result_message* msg = new Put_trigger_result_message();
    msg->ack_id = req_id;
    msg->result = result;
    msg->tid = tid;

    triggers.insert(msg->tid);
    enqueue(Message_ptr(msg), 0);
}

void
Servant::send_trigger_call(const bool sticky, const Trigger_id& tid, 
                           const Row& row) {
    Trigger_message* msg = new Trigger_message();
    msg->tid = tid;
    msg->row = row;
    if (!sticky) {
        triggers.erase(tid);
    }
    enqueue(Message_ptr(msg), 0);
}

void
Servant::process(Put_row_trigger_message* msg) {
    Async_storage::Put_trigger_callback f = 
        boost::bind(&Servant::put_trigger_callback, this, msg->req_id, _1, _2);
    Trigger_function tfunc = 
        boost::bind(&Servant::send_trigger_call, this, false, _1, _2); 
    server->storage->put_trigger(msg->ctxt, tfunc, f);
}

Server::Server(const container::Context* ctxt,
               const xercesc::DOMNode*) 
    : Component(ctxt) {
    
}

void 
Server::configure(const Configuration*) {
    // TODO: parse the configuration
    int port = 8001;
    int backlog = 10;

    init(port, backlog);
    resolve(storage);
}

void 
Server::install() {
    start(boost::bind(&Listener<Servant>::run, (Listener<Servant>*)this));
}

boost::shared_ptr<Servant> 
Server::get_servant(std::auto_ptr<Tcp_socket> socket) {
    return boost::shared_ptr<Servant>(new Servant(this, socket));
}

REGISTER_COMPONENT(container::Simple_component_factory<Server>, Server);
