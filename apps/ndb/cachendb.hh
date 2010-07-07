#ifndef CONTROLLER_CACHE_NDB_HH
#define CONTROLLER_CACHE_NDB_HH 1

#include <map>
#include <boost/function.hpp>
#include <list>
#include <boost/shared_ptr.hpp>
#include "ndb.hh"
#include "lockndb.hh"
#include "vlog.hh"

namespace vigil {

class Storage {
public:
    /* Check for a query.
     *
     * \param q is the query to check for.
     * \return XXX if a cache miss. 
     */
    NDB::OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&); 

    /* Store a result to a query. 
     *
     * \param q is the original search query.
     * \param v is the result to be cached.
     * \param c is the callback to be invoked once the entries become
     * stale.
     */
    void insert(const std::list<boost::shared_ptr<GetOp> >&);

    /* Remove a cached query and trigger any stored callbacks.
     *
     * \param q is the original search query.
     */
    void invalidate(const Op::Select_ptr&,
                    const Op::Callback&);
    
private:
    std::map<Op::Select_ptr,
             boost::shared_ptr<
                 std::list<
                     Op::Row_ptr
                     > > >  queries;
    
    std::map<Op::Row_ptr, std::list<Op::Select_ptr> > rows;
};

/*
 * Network database cache.
 * 
 * For documentation of the interface, please see
 * doc/Network_Database.txt.
 *
 */
class CacheNDB
    : public NDB
{
public:
    CacheNDB(const boost::shared_ptr<NDB>& nh) : nexthop(nh) { };

    OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&);

    OpStatus execute(const std::list<boost::shared_ptr<PutOp> >&,
                     const std::list<boost::shared_ptr<GetOp> >&);

private:
    const boost::shared_ptr<NDB> nexthop;

    LockManager lockmgr;

    Storage storage;

    // XXX: how to mark the rows for a specific key and vice versa.
    // callback -> a set of rows
};

} // namespace vigil

#endif /* controller/cachendb.hh */
