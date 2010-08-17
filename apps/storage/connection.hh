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
#ifndef STORAGE_CONNECTION_HH
#define STORAGE_CONNECTION_HH 1

#include <list>

/* Don't change the order of boost serialization and archive
   headers. It matters for the serialization implementation. */
#include <boost/serialization/serialization.hpp>
#include <boost/serialization/hash_map.hpp>
#include <boost/serialization/list.hpp>
#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/split_free.hpp>
#include <boost/serialization/string.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/serialization/variant.hpp>
#include <boost/archive/text_oarchive.hpp>
#include <boost/archive/text_iarchive.hpp>
#include <boost/serialization/export.hpp>

#include <boost/bind.hpp>
#include <boost/shared_ptr.hpp>

#include "buffer.hh"
#include "hash_map.hh"
#include "netinet++/ipaddr.hh"
#include "storage.hh"
#include "tcp-socket.hh"
#include "threads/cooperative.hh"
#include "timeval.hh"

namespace vigil { 
namespace applications { 
namespace storage {

class Callbacks;
class Message;
class Result_message;
class Create_table_message;
class Drop_table_message;
class Get_message;
class Get_next_message;
class Put_message;
class Modify_message;
class Modify_result_message;
class Remove_message;
class Put_row_trigger_message;
    //class Put_table_trigger_message;
class Put_trigger_result_message;
    //class Remove_trigger_message;
class Trigger_message;

/**
 * Connection library is a set of connection states.  The library user
 * merely picks the initial state and then lets the state machine to
 * run.  States implement all the necessary connection management
 * functionality and the only task left for the user is to integrate
 * by using 'Callbacks'.
 */
class State {
public:
    State(State*);
    virtual ~State() { };
    virtual State* advance() = 0;

protected:
    State(Callbacks*);

    /* Throws an exception in case of an error. */
    void send(const Message&);

    /* Throws an exception in case of an error. */
    boost::shared_ptr<Message> receive();

    Callbacks* callbacks;
};

/*
 * State to initiate a handshake on an already established connection.
 * For a server to use onto an accepted connection.
 */
class InitiateHandshake
    : public State {
public:
    InitiateHandshake(Callbacks*);
    InitiateHandshake(State*); 

    State* advance();
};

class Connection_error : 
        public std::exception {
public:
    explicit Connection_error(const std::string&);
    virtual ~Connection_error() throw();
    virtual const char* what() const throw();

private:
    std::string msg;
};

typedef boost::shared_ptr<Message> Message_ptr;

class Message {
public:
    virtual ~Message() { };
    virtual void process(Callbacks*) {
        throw "Unexpected message";
    }

    typedef uint32_t Message_id;

    Message_id req_id;
    Message_id ack_id;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & req_id;
        ar & ack_id;
    }
};

/**
 * To use the connection class, an implementation of the Callbacks
 * interface has to be provided.  The callbacks provide the necessary
 * integration mechanism between the connection implementation and its
 * user.
 */
class Callbacks {
public:
    typedef boost::function<void(Message_ptr)> Message_callback;

    Callbacks() : next_id(0) { }
    virtual ~Callbacks() { };

    /* Inheriting classes should override message types they
       support. */
    virtual void process(Create_table_message*);
    virtual void process(Drop_table_message*);
    virtual void process(Get_message*);
    virtual void process(Get_next_message*);
    virtual void process(Put_message*);
    virtual void process(Modify_message*);
    virtual void process(Remove_message*);
    virtual void process(Put_row_trigger_message*);
    //virtual void process(Put_table_trigger_message*);
    //virtual void process(Remove_trigger_message*);
    virtual void process(Trigger_message*);

    /* Connection closed */
    void disconnected();

    void received(Message_ptr);

    /* Get the next outbound message. Returns empty pair if none. */
    Message_ptr queue_try_get();
    
    /* Prepare for waiting outboung message. */
    void queue_wait();

    void enqueue(Message_ptr, Message_callback);

    void read_wait() { sock->read_wait(); } 

    void block() { Co_thread::block(); }

    int read(Buffer& buffer,ssize_t* bytes_read,  bool block) { 
        return sock->read_fully(buffer, bytes_read, block); 
    }

    int write(const Buffer& buffer, ssize_t* bytes_written, bool block) { 
        return sock->write_fully(buffer, bytes_written, block); 
    }

    void run_connection(State* initial_state);

protected:
    /* TCP connection */
    std::auto_ptr<Tcp_socket> sock;

private:
    /* Queue */
    Co_sema outbound_messages_pending;
    std::list<Message_ptr> outbound_messages;

    /* Pending callbacks */    
    hash_map<Message::Message_id, Message_callback> pending_callbacks;

    /* Mutex protecting the queue */
    Co_mutex mutex;

    Message::Message_id next_id;
};

/* Storage operations are mapped to messages */

class Hello_message
    : public Message {
public:
    Hello_message() 
        : major_version(1), minor_version(0) {
        
    }

    int major_version;
    int minor_version;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);
        ar & major_version;
        ar & minor_version;
    }
};

class Create_table_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }
    
    Table_name table;
    Column_definition_map columns;
    Index_list indices;
    
protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);
        ar & table;
        ar & columns;
        ar & indices;
    }
};

class Drop_table_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }
    
    Table_name table;
    
protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);
        ar & table;
    }
};

class Result_message 
    : public Message
{
public:
    Result result;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & result;
    }
};

class Get_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Table_name table;
    Query query;
    
protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & table;
        ar & query;
    }
};

class Get_next_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Context ctxt;
    
protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & ctxt;
    }
};

class Get_result_message 
    : public Result_message
{
public:
    Context ctxt;
    Row row;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Result_message>(*this);

        ar & ctxt;
        ar & row;
    }
};

class Put_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Table_name table;
    Row row;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & table;
        ar & row;
    }
};

class Put_result_message 
    : public Result_message
{
public:
    GUID guid;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Result_message>(*this);

        ar & guid;
    }
};

class Modify_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Context ctxt;
    Row row;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & ctxt;
        ar & row;
    }
};

class Modify_result_message 
    : public Result_message
{
public:
    Context ctxt;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Result_message>(*this);

        ar & ctxt;
    }
};

class Remove_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Context ctxt;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & ctxt;
    }
};

class Put_row_trigger_message
    : public Message {
public:
    void process(Callbacks* callbacks) { 
        callbacks->process(this);
    }

    Context ctxt;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & ctxt;
    }
};

class Put_trigger_result_message 
    : public Result_message
{
public:
    Trigger_id tid;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Result_message>(*this);

        ar & tid;
    }
};

class Trigger_message
    : public Message {
public:
    void process(Callbacks* callbacks) {
        callbacks->process(this);
    }

    Trigger_id tid;
    Row row;

protected:
    friend class boost::serialization::access;

    template<typename Archive>
    void serialize(Archive & ar, const unsigned int version) {
        ar & boost::serialization::base_object<Message>(*this);

        ar & tid;
        ar & row;
    }
};

} // namespace storage
} // namespace applications
} // namespace vigil

namespace boost { 
namespace serialization {

/* Boost serialization template specializations for vigil hash_map. */

template<class Archive, class Key, class Tp, class Hash, class Equal,
         class Allocator>
inline void load(Archive& ar, 
                 vigil::hash_map<Key, Tp, Hash, Equal, Allocator>& m, 
                 const unsigned int version) {
    using namespace boost::serialization::stl;
    using namespace vigil;

    load_collection<Archive, hash_map<Key, Tp, Hash, Equal, Allocator>,
        archive_input_unique<Archive, hash_map<Key, Tp, Hash,Equal,Allocator> >,
        no_reserve_imp<hash_map<Key, Tp, Hash, Equal, Allocator> > >(ar, m);
}

template<class Archive, class Key, class Tp, class Hash, class Equal,
         class Allocator>
inline void save(Archive& ar, 
                 const vigil::hash_map<Key, Tp, Hash, Equal, Allocator>& m, 
                 const unsigned int version) {
    using namespace boost::serialization::stl;
    using namespace vigil;

    save_collection<Archive, hash_map<Key, Tp, Hash, Equal, Allocator> >(ar, m);
}

template<class Archive, class Key, class Tp, class Hash, class Equal,
         class Allocator>
inline void serialize(Archive& ar, 
                      vigil::hash_map<Key, Tp, Hash, Equal, Allocator>& m, 
                      const unsigned int version) {
    boost::serialization::split_free(ar, m, version);
}

/* Boost serialization template specializations for storage API classes */

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::GUID& guid, 
                      const unsigned int version) {
    ar & guid.guid;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Reference& ref, 
                      const unsigned int version) {
    ar & ref.version;
    ar & ref.guid;
    ar & ref.wildcard;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Context& ctxt, 
                      const unsigned int version) {
    ar & ctxt.table;
    ar & ctxt.index;
    ar & ctxt.index_row;
    ar & ctxt.initial_row;
    ar & ctxt.current_row;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Trigger_id& tid, 
                      const unsigned int version) {
    ar & tid.for_table;
    ar & tid.ring;
    ar & tid.ref;
    ar & tid.tid;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Index& index, 
                      const unsigned int version) {
    ar & index.name;
    ar & index.columns;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Column_value& c, 
                      const unsigned int version) {
    ar & c;
}

template<class Archive>
inline void serialize(Archive& ar, 
                      vigil::applications::storage::Result& result, 
                      const unsigned int version) {
    ar & result.code;
    ar & result.message;
}

} // namespace serialization
} // namespace boost

#endif

