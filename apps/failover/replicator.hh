/* Copyright 2008 (C) Nicira, Inc. */
#ifndef REPLICATOR_HH
#define REPLICATOR_HH 1

#include "component.hh"
#include "storage/transactional-storage.hh"
#include "threads/cooperative.hh"

namespace vigil {
namespace applications {
namespace replicator {

/* Transactional storage replicator.
 *
 * Copies the SQLite database file every N seconds to a configurable
 * directory. */
class Storage_replicator
    : public container::Component {
public:
    Storage_replicator(const container::Context*, const json_object*);
    static void getInstance(const container::Context*, Storage_replicator*&);

    /* Make a snapshot of the database. Adds a timestamp to the file
       name, if unique is set.  Returns an empty string in
       unsuccessful. */
    std::string snapshot(const std::string& destination, bool unique) const;

protected:
    void configure(const container::Configuration*);
    void install();

private:
    /* Replication thread */
    void run() const;

    /* Replication interval */
    timeval replication_delay;

    /* Database file */
    std::string database;

    /* Destination file path */
    std::string destination;

    /* Mutex preventing simultaneous snapshots */
    mutable Co_mutex mutex;

    /* The replicated storage */
    storage::Async_transactional_storage* storage;

    /* Replication thread */
    Co_thread thread;

    /* create unique filename on each rotation */
    bool unique;
};

} // replicator
} // applications
} // vigil 

#endif
