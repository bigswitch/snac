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
#include "connection.hh"

#include <arpa/inet.h>

#include <sstream>

#include <boost/bind.hpp>
#include <boost/shared_ptr.hpp>

#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::storage;

static Vlog_module lg("storage-connection");

class ReceiveHello
    : public State {
public:
    ReceiveHello(State*);
    State* advance();
};

class Connected 
    : public State {
public:
    Connected(State*);
    State* advance();
};

class Disconnected 
    : public State {
public:
    Disconnected(State*);
    State* advance();
};

State::State(State* s)
  : callbacks(s->callbacks) {
}

State::State(Callbacks* callbacks_)
  : callbacks(callbacks_) {
}

void
State::send(const Message& m) {
    ostringstream stream_message;
    boost::archive::text_oarchive archive(stream_message);
    Message* m_ = const_cast<Message*>(&m);
    archive & m_;
    const string serialized_message = stream_message.str();

    ostringstream stream_header;
    const int header_length = sizeof(uint64_t);

    stream_header << setw(header_length) << hex << serialized_message.length();
    
    const string serialized_header = stream_header.str();
    const int total_length = serialized_header.length() + 
        serialized_message.length();

    lg.dbg("Serialized the header, %d bytes.", serialized_header.length());
    lg.dbg("Serialized the message, %d bytes.", serialized_message.length());

    //std::cerr << std::hex << serialized_message;
    //std::cerr.flush();

    Array_buffer message_buf(total_length);
    ::memcpy(message_buf.data(), 
             serialized_header.data(), 
             serialized_header.length());
    ::memcpy(message_buf.data() + serialized_header.length(), 
             serialized_message.data(), 
             serialized_message.length());

    ssize_t written = 0;
    if (callbacks->write(message_buf, &written, true) < 0) {
        throw Connection_error("TCP connection error.");
    }
}

boost::shared_ptr<Message>
State::receive() {
    boost::shared_ptr<Message> msg;

    char header_data[sizeof(uint64_t)];
    Nonowning_buffer header_buf(header_data, sizeof(header_data));
            
    ssize_t bytes_read = 0; 

    lg.dbg("Receiving the header, %d bytes.", sizeof(header_data));

    int error = callbacks->read(header_buf, &bytes_read, true);
    if (error) {
        throw Connection_error("TCP connection error.");
    }

    int message_length;
    istringstream hss(string(header_data, sizeof(header_data)));
    if (!(hss >> hex >> message_length)) {
        throw Connection_error("Message header parsing failed.");
    }

    lg.dbg("Receiving the message, %d bytes.", message_length);
            
    char message_data[message_length];
    Nonowning_buffer message_buf(message_data, sizeof(message_data));
    
    bytes_read = 0;
    error = callbacks->read(message_buf, &bytes_read, true);

    string x(message_data, sizeof(message_data));
    istringstream mss(x);
    boost::archive::text_iarchive ia(mss);
    Message* m;

    lg.dbg("Deserializing the message (read %d bytes).", bytes_read);
    //std::cerr << std::hex << x;
    //std::cerr.flush();

    try {
        ia & m;
        msg.reset(m);
    } 
    catch (const boost::archive::archive_exception& e) {
        lg.dbg("Unable to deserialize the message: %s", e.what());
        throw Connection_error("Message deserializing error.");
    }
    return msg;
}

Connection_error::Connection_error(const std::string& cause) 
    : msg(cause) {
}

Connection_error::~Connection_error() throw() { 
}

const char* 
Connection_error::what() const throw() {
    return msg.c_str();
};

ReceiveHello::ReceiveHello(State* prev) 
  : State(prev) { 
}

State*
ReceiveHello::advance() {
    try {        
        lg.dbg("Waiting for HELLO.");
        boost::shared_ptr<Message> m = receive();
        Hello_message* h = dynamic_cast<Hello_message*>(m.get());
        if (h == 0 || !(h->major_version == 1 && h->minor_version == 0)) {
            throw Connection_error("Incompatible protocol version.");
        }
        
        return new Connected(this);
    }
    catch (const Connection_error& error) {
        lg.dbg("Disconnecting, connection error: %s", error.what());
        return 0;
    }
}

InitiateHandshake::InitiateHandshake(Callbacks* callbacks) 
    : State(callbacks) {
    
}

InitiateHandshake::InitiateHandshake(State* prev) 
    : State(prev) {

}

State* 
InitiateHandshake::advance() {
    lg.dbg("Sending HELLO");
    try {
        send(Hello_message());
        return new ReceiveHello(this);
    }
    catch (const Connection_error& error) {
        lg.dbg("Disconnecting, connection error: %s", error.what());
        return 0;
    }
}

Connected::Connected(State* prev) 
    : State(prev) {

}

State* 
Connected::advance() {
    // TODO: client and server probably don't share the preference
    // over reading and writing.

    lg.dbg("Waiting for a message.");
    callbacks->queue_wait();
    lg.dbg("1");
    callbacks->read_wait();
    lg.dbg("2");
    callbacks->block();
    lg.dbg("Trying to get...");
    Message_ptr m = callbacks->queue_try_get();

    lg.dbg("Tried...");
    try {
        if (m.get()) {
            // Outbound message
            lg.dbg("Sending the message.");
            send(*m);
        } else {
            // Inbound message
            lg.dbg("Receiving a message.");
            callbacks->received(receive());
        }
    } 
    catch (const Connection_error& error) {
        lg.dbg("Disconnecting, connection error: %s", error.what());
        return new Disconnected(this);
    }
    return this;
}

Disconnected::Disconnected(State* prev) 
  : State(prev) { 
}

State*
Disconnected::advance() {
    callbacks->disconnected();
    return 0;
}

void 
Callbacks::disconnected() {
    /* Trigger all pending callbacks *and* triggers with connection error. */

    Co_scoped_mutex l(&mutex);

    for (hash_map<Message::Message_id, Message_callback>::iterator i =
             pending_callbacks.begin(); i != pending_callbacks.end(); ++i) {
        Message_callback& cb = i->second;
        cb(Message_ptr());
    }

    pending_callbacks.clear();
}

void
Callbacks::received(Message_ptr m) {
    if (m->ack_id) {
        hash_map<Message::Message_id, Message_callback>::iterator i = 
            pending_callbacks.find(m->ack_id);
        if (i == pending_callbacks.end()) {
            throw Connection_error("Unexpected ack message.");
        } else {
            i->second(m);
        }
    } else {
        m->process(this);
    }
}

void
Callbacks::queue_wait() { 
    outbound_messages_pending.wait(0); 
}

Message_ptr
Callbacks::queue_try_get() {
    using namespace std;
    
    if (outbound_messages_pending.try_down()) {
        Message_ptr p = outbound_messages.front();
        outbound_messages.pop_front();
        return p; 
    } else {
        return Message_ptr();
    }
}

void
Callbacks::enqueue(Message_ptr msg, Message_callback cb) {
    Co_scoped_mutex l(&mutex);

    msg->req_id = next_id++;
    
    outbound_messages.push_back(msg);
    outbound_messages_pending.up();
    lg.dbg("Enqueued a message.");
}

void
Callbacks::run_connection(State* s) {
    while (s) {
        State* p = s;
        s = p->advance();
        if (p != s) {
            delete p;
        }
    }
        
    sock->close();
}

void
Callbacks::process(Create_table_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Drop_table_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Get_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Get_next_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Put_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Modify_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Remove_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Put_row_trigger_message*) {
    throw Connection_error("Unexpected message.");
}

void
Callbacks::process(Trigger_message* msg) {
    throw Connection_error("Unexpected message.");
}

/* Tell Boost::Serialization about polymorphic classes to be
   serialized and de-serialized. */
BOOST_CLASS_EXPORT_GUID(Hello_message, "Storage_Hello")
BOOST_CLASS_EXPORT_GUID(Create_table_message, "Storage_Create_table")
BOOST_CLASS_EXPORT_GUID(Drop_table_message, "Storage_Drop_table")
BOOST_CLASS_EXPORT_GUID(Result_message, "Storage_Result")
BOOST_CLASS_EXPORT_GUID(Get_message, "Storage_Get")
BOOST_CLASS_EXPORT_GUID(Get_next_message, "Storage_Get_next")
BOOST_CLASS_EXPORT_GUID(Get_result_message, "Storage_Get_result")
BOOST_CLASS_EXPORT_GUID(Put_message, "Storage_Put")
BOOST_CLASS_EXPORT_GUID(Put_result_message, "Storage_Put_result")
BOOST_CLASS_EXPORT_GUID(Modify_message, "Storage_Modify")
BOOST_CLASS_EXPORT_GUID(Modify_result_message, "Storage_Modify_result")
BOOST_CLASS_EXPORT_GUID(Remove_message, "Storage_Remove")
BOOST_CLASS_EXPORT_GUID(Put_row_trigger_message, "Storage_Put_row_trigger")
//BOOST_CLASS_EXPORT_GUID(Put_table_trigger_message, "Storage_Put_table_trigger")
BOOST_CLASS_EXPORT_GUID(Put_trigger_result_message,"Storage_Put_trigger_result")
BOOST_CLASS_EXPORT_GUID(Trigger_message, "Storage_Trigger")

