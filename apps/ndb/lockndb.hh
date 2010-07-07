#ifndef CONTROLLER_LOCK_NDB_HH
#define CONTROLLER_LOCK_NDB_HH 1

#include <boost/noncopyable.hpp>
#include "threads/cooperative.hh"

namespace vigil {

class Lock;

/**
 * A simple lock manager for NDB API implementations. Locking policy
 * is: writes are exclusive, while multiple reads can be executed in
 * parallel.
 */
class LockManager 
    : boost::noncopyable
{
public:
    void acquire_read() { rwlock.read_lock(); }
    void release_read() { rwlock.read_unlock(); }

    void acquire_write() { rwlock.write_lock(); }
    void release_write() { rwlock.write_unlock(); }
private:
    Co_rwlock rwlock;
};

} // namespace vigil

#endif /* controller/lockndb.hh */

