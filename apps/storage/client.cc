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
#include "client.hh"

#include <boost/bind.hpp>

#include "connection.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::storage;
using namespace vigil::container;

static Vlog_module lg("storage-client");

Async_client::Async_client(const container::Context* c,
                           const xercesc::DOMNode*) 
    : Component(c) {

}

void 
Async_client::configure(const Configuration*) {
    // TODO: parse the configuration
    host = ipaddr("localhost");
    port = 8001;
}

void 
Async_client::install() {
    start(boost::bind(&Async_client::run, this));
}

/* Storage API */

void
Async_client::generic_callback(const Async_storage::Create_table_callback& f,
                               Message_ptr message) {
    Result_message* r = dynamic_cast<Result_message*>(message.get());
    if (r == 0) {
        dispatcher->post(boost::bind(f, Result(Result::CONNECTION_ERROR, ""))); 
        throw Connection_error("Unexpected message.");
    }
    f(r->result);
}

void
Async_client::create_table(const Table_name& table,
                           const Column_definition_map& columns,
                           const Index_list& indices,
                           const Create_table_callback& cb) {
    boost::shared_ptr<Create_table_message> ctm(new Create_table_message());
    ctm->table = table;
    ctm->columns = columns;
    ctm->indices = indices;
    enqueue(ctm, boost::bind(&Async_client::generic_callback, this, cb, _1));
}

void
Async_client::drop_table(const Table_name& table,
                         const Drop_table_callback& cb) {
    boost::shared_ptr<Drop_table_message> dtm(new Drop_table_message());
    dtm->table = table;
    enqueue(dtm, boost::bind(&Async_client::generic_callback, this, cb, _1));
}

void
Async_client::get_callback(const Async_storage::Get_callback& f,
                           Message_ptr message) {
    Get_result_message* r = dynamic_cast<Get_result_message*>(message.get());
    if (r == 0) {
        dispatcher->post(boost::bind(f, Result(Result::CONNECTION_ERROR, ""), 
                                     Context(), Row()));
        throw Connection_error("Unexpected message.");
    }

    f(r->result, r->ctxt, r->row);
}

void 
Async_client::get(const Table_name& table, const Query& query, 
                  const Get_callback& cb) {
    boost::shared_ptr<Get_message> gm(new Get_message());
    gm->table = table;
    gm->query = query;
    enqueue(gm, boost::bind(&Async_client::get_callback, this, cb, _1));
}

void 
Async_client::get_next(const Context& ctxt, const Get_callback& cb) {
    boost::shared_ptr<Get_next_message> gnm(new Get_next_message());
    gnm->ctxt = ctxt;
    enqueue(gnm, boost::bind(&Async_client::get_callback, this, cb, _1));
}

void
Async_client::put_callback(const Async_storage::Put_callback& f,
                           const GUID& guid, Message_ptr message) {
    Put_result_message* r = dynamic_cast<Put_result_message*>(message.get());
    if (r == 0) {
        dispatcher->post(boost::bind(f, Result(Result::CONNECTION_ERROR, ""), 
                                     guid));
        throw Connection_error("Unexpected message.");
    }

    f(r->result, guid);
}

void 
Async_client::put(const Table_name& table,const Row& row,const Put_callback& cb)
{
    boost::shared_ptr<Put_message> pm(new Put_message());
    Row row_ = row;

    if (row_.find("guid") == row_.end()) {
        row_["guid"] = GUID::random();
    }

    try {
        const GUID guid = boost::get<GUID>(row_["guid"]);
        pm->table = table;
        pm->row = row_;
        enqueue(pm, boost::bind(&Async_client::put_callback, this, cb, 
                                guid, _1));
    }
    catch (const boost::bad_get& e) { 
        dispatcher->post
            (boost::bind(cb, Result(Result::INVALID_ROW_OR_QUERY,
                                    "GUID given with invalid type."), GUID()));
        return;
    }
}

void
Async_client::modify_callback(const Async_storage::Modify_callback& f,
                              Message_ptr message) {
    Modify_result_message* r = 
        dynamic_cast<Modify_result_message*>(message.get());
    if (r == 0) {
        dispatcher->post(boost::bind(f, Result(Result::CONNECTION_ERROR, ""), 
                                     vigil::applications::storage::Context()));
        throw Connection_error("Unexpected message.");
    }

    f(r->result, r->ctxt);
}

void 
Async_client::modify(const Context& ctxt, const Row& row,
                     const Modify_callback& cb)
{
    boost::shared_ptr<Modify_message> mm(new Modify_message());
    mm->ctxt = ctxt;
    mm->row = row;
    enqueue(mm, boost::bind(&Async_client::modify_callback, this, cb, _1));
}

void 
Async_client::remove(const Context& ctxt, const Remove_callback& cb)
{
    boost::shared_ptr<Remove_message> rm(new Remove_message());
    rm->ctxt = ctxt;
    enqueue(rm, boost::bind(&Async_client::generic_callback, this, cb, _1));
}

void
Async_client::put_trigger_callback(const Trigger_function& tfunc,
                                   const Async_storage::Put_trigger_callback& f,
                                   Message_ptr message) {
    Put_trigger_result_message* r = 
        dynamic_cast<Put_trigger_result_message*>(message.get());
    if (r == 0) {
        dispatcher->post(boost::bind(f, Result(Result::CONNECTION_ERROR, ""), 
                                     Trigger_id()));
        throw Connection_error("Unexpected message.");
    }

    {
        Co_scoped_mutex l(&mutex);
        triggers[r->tid] = make_pair(tfunc, false);
    }

    f(r->result, r->tid);
}

void 
Async_client::put_trigger(const Context& ctxt, const Trigger_function& tfunc,
                          const Put_trigger_callback& cb)
{
    boost::shared_ptr<Put_row_trigger_message> 
        prtm(new Put_row_trigger_message());
    prtm->ctxt = ctxt;
    enqueue(prtm, boost::bind(&Async_client::put_trigger_callback, this,
                              tfunc, cb, _1));
}


/* Supported callbacks */

void
Async_client::process(Trigger_message* msg) {
    Co_scoped_mutex l(&mutex);
    
    hash_map<Trigger_id, pair<Trigger_function, bool> >::iterator i = 
        triggers.find(msg->tid);
    if (i == triggers.end()) {
        /* Trigger must have been removed. Ignore */
        return;
    }

    /* If not sticky, remove once called. */
    Trigger_function tfunc = i->second.first; 
    if (!i->second.second) {
        triggers.erase(i);
    }

    dispatcher->post(boost::bind(tfunc, msg->tid, msg->row));
}

int
Async_client::connect() {
    lg.dbg("Connecting to network database at %s:%d...", host.c_str(), port);
    sock.reset(new Tcp_socket());
    return sock->connect(host, htons(port), true);
}

void
Async_client::run() {
    while (true) {
        run_connection(new Connecting(this));
    }

}
Connecting::Connecting(Async_client* client_) 
    : State(client_), client(client_) {
        
}

State* 
Connecting::advance() {
    for (long delay = 1; true; delay <<= 1) {
        int error = client->connect();
        if (!error) {
            break;
        }

        lg.dbg("Can't connect %d", error);

        if (delay > 1000) { 
            delay = 1000; 
        }

        Co_thread::sleep(timeval_from_ms(delay));
    }

    return new InitiateHandshake(this);
}

REGISTER_COMPONENT(container::Simple_component_factory<Async_client>, 
                   Async_storage);
