/* Copyright 2008 (C) Nicira, Inc. */
#include "replicator.hh"

#include <boost/bind.hpp>
#include <boost/lexical_cast.hpp>

#include <algorithm>

#include <fcntl.h>
#include <ctype.h>
#include <time.h>

#include "async_file.hh"
#include "buffer.hh"
#include "storage/sqlite3-impl.hh"
#include "storage/transactional-storage-blocking.hh"
#include "timeval.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::replicator;
using namespace vigil::applications::storage;

static Vlog_module lg("replicator");

/* Bytes to read with a single read() when copying the SQLite file. */
#define CHUNK_SIZE 2 * 1024

/* In seconds, can be overriden from command line */
#define DEFAULT_REPLICATION_INTERVAL 600 

Storage_replicator::Storage_replicator(const container::Context* c,
                                       const json_object*)
    : Component(c) {
        unique = false;
}

void
Storage_replicator::getInstance(const container::Context* ctxt, 
                                Storage_replicator*& h) {
    h = dynamic_cast<Storage_replicator*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(Storage_replicator).name())));
}

//
// args = <delay_time>,<filename>,true
//
void
Storage_replicator::configure(const container::Configuration* conf) {
    container::Component_argument_list args = conf->get_arguments();
    
    if (args.empty()) {
        replication_delay = make_timeval(DEFAULT_REPLICATION_INTERVAL, 0);
    } else {
        string i = args.front();
        try {
            replication_delay = make_timeval(boost::lexical_cast<int>(i), 0);
        } 
        catch (const boost::bad_lexical_cast& e) {
            throw runtime_error("Invalid replication interval ('" + i + "')");
        }
        args.pop_front();
    }

    resolve(storage);
    if (!storage) { throw runtime_error("transactional storage not found"); }

    SQLite_storage* impl = dynamic_cast<SQLite_storage*>(storage);
    if (!impl) { throw runtime_error("SQLite3 based transactional storage "
                                     "not found"); }
    database = impl->get_location();

    if (!args.empty()){
        destination = args.front() + ".auto";
        args.pop_front();
    }else{
        destination = database + ".bak";
    }

    if (!args.empty()){
        string u = args.front();
        std::transform(u.begin(), u.end(), u.begin(), ::tolower);
        if(u == "true"){
            unique = true;
        }
    }
}

void
Storage_replicator::install() {
    thread.start(boost::bind(&Storage_replicator::run, this));
}

#define FAIL_IFF_NEG(ERROR, MSG)                                        \
    do {                                                                \
        int err = ERROR;                                                \
        if (err < 0) {                                                  \
            char m[1024];                                               \
            ::strerror_r(-err, m, sizeof(m));                           \
            throw runtime_error(MSG + string(m));                       \
        }                                                               \
    } while (0);

void
Storage_replicator::run() const {
    while (true) {
        snapshot(destination, unique);
        co_sleep(replication_delay);
    }
}

string
Storage_replicator::snapshot(const string& destination, bool unique) const {
    Co_scoped_mutex lock(&mutex);

    Sync_transactional_storage s(storage);
    Sync_transactional_storage::Get_connection_result r = s.get_connection();
    Sync_transactional_connection_ptr conn = r.get<1>();

    const string f = destination + ".tmp"; 

    try {
        conn->begin(Async_transactional_connection::EXCLUSIVE);

        Async_file src, dst;
        
        lg.dbg("Snapshotting '%s' to '%s'.", database.c_str(), f.c_str());
        
        FAIL_IFF_NEG(src.open(database, O_RDONLY),
                     "Unable to open '" + database + "':");
        FAIL_IFF_NEG(dst.open(f, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR |
                              S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH),
                     "Unable to open '" + f + "':");
        
        const off_t dump_size = src.size();
        FAIL_IFF_NEG(dump_size, "Unable to stat '" + database + "':");
        
        off_t written = 0;
        for (off_t read_ = 0; read_ < dump_size; ) {
            Array_buffer buff(CHUNK_SIZE);
            ssize_t r = src.pread(read_, buff);
            FAIL_IFF_NEG(r, "Unable to read '" + database + "': ");
            buff.trim(r);
            read_ += r;
            
            for (; written < read_; ) {
                ssize_t w = dst.pwrite(written, buff);
                FAIL_IFF_NEG(w, "Unable to write '" + database + "':");
                
                buff.pull(w);
                written += w;
            }
        }
        
        conn->commit();
    }
    catch (const runtime_error& e) {
        lg.err("%s", e.what());
        conn->rollback();
        return "";
    }

    string final_path = destination;
    if (unique) {
        final_path += boost::lexical_cast<std::string>(::time(NULL));
    }
    
    int ret = Async_file::rename(f, final_path);
    if (ret) {
        lg.err("Unable to move database snapshot '%s' to '%s': %d",
               f.c_str(), final_path.c_str(), ret);        
        return "";
    } else {
        return final_path;
    }
}

REGISTER_COMPONENT(container::Simple_component_factory<Storage_replicator>,
                   Storage_replicator);
