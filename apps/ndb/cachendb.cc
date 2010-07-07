#include "cachendb.hh"
#include <boost/bind.hpp>

namespace vigil {
    
static Vlog_module lg("ndb");

NDB::OpStatus
CacheNDB::execute(const std::list<boost::shared_ptr<GetOp> >& q) 
{
    lockmgr.acquire_read();
    OpStatus result = storage.execute(q);
    lockmgr.release_read();

    if (result != OK) {
        return result;
    }

    for (std::list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end(); 
         ++i) {
        if (!(*i)->has_results()) {
            // No hit!

            // Replace the application callback(s) with our
            // invalidation callback.
            for (std::list<boost::shared_ptr<GetOp> >::const_iterator j = 
                     q.begin(); 
                 j != q.end(); 
                 ++j) {
                const boost::shared_ptr<GetOp> op = *j;
                const Op::Callback cb = op->get_callback();
                op->set_callback(boost::bind(&Storage::invalidate, 
                                             &storage, 
                                             op->get_select(), 
                                             op->get_callback()));
            }

            // Query the next hop.
            result = nexthop->execute(q);
            if (result != OK) {
                return result;
            }

            lockmgr.acquire_write();
            storage.insert(q);
            lockmgr.release_write();

            return OK;
        }
    }

    // It's a hit.
    return OK;
}

NDB::OpStatus
CacheNDB::execute(const std::list<boost::shared_ptr<PutOp> >& q,
                  const std::list<boost::shared_ptr<GetOp> >& d) {
    // PutOps bypass cache.
    return nexthop->execute(q, d);
}

// Cache storage implementation

NDB::OpStatus
Storage::execute(const std::list<boost::shared_ptr<GetOp> >& q) {
    using namespace std;
    lg.dbg("Checking the cache.");

    // First, collect the responses we have.
    list<Op::Results_ptr> results;

    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {
        std::map<Op::Select_ptr,
            boost::shared_ptr<std::list<Op::Row_ptr> > >::
            iterator pos;
        pos = queries.find((*i)->get_select());
        if (pos == queries.end()) {
            // Nothing found...
            return NDB::OK;
        }

        Op::Results_ptr rs(new list<Op::Row_ptr>);
        boost::shared_ptr<list<Op::Row_ptr> > q = queries[(*i)->get_select()];

        for (list<Op::Row_ptr>::const_iterator j = q->begin(); 
             j != q->end();
             ++j) {
            rs->push_back(*j);
        }

        results.push_back(rs);
    }

    // Then, if we've them all, inject them into the queries.
    list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin();
    list<Op::Results_ptr>::iterator j = results.begin();
    while (i != q.end()) {
        (*i)->set_results(*j);
        ++i; ++j;
    }

    return NDB::OK;
}

void 
Storage::insert(const std::list<boost::shared_ptr<GetOp> >& q) {
    using namespace std;

    lg.dbg("Updating the cache.");

    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {
        Op::Select_ptr select = (*i)->get_select();
        boost::shared_ptr<list<Op::Row_ptr> > r = 
            (*i)->get_results();

        // Add to queries
        boost::shared_ptr<list<Op::Row_ptr> > l(new list<Op::Row_ptr>);
        queries[select] = l;
        
        for (list<Op::Row_ptr>::const_iterator j = r->begin();
             j != r->end();
             ++j) {
            if (rows.find(*j) != rows.end()) {
                // Cache has it.

                // XXX: check for duplicate queries.

            } else {
                // Cache has no row -> add it.
                rows[*j] = list<Op::Select_ptr>();
            }

            rows[*j].push_back(select);
            l->push_back(*j);
        }
    }
}

void 
Storage::invalidate(const Op::Select_ptr& q,
                    const Op::Callback& original_cb) {
    using namespace std;
    lg.dbg("Invalidating a cache entry.");

    list<Op::Select_ptr> l; 
    l.push_back(q);

    while (l.size() > 0) {
        Op::Select_ptr select = l.front();
        
        map<Op::Select_ptr,
            boost::shared_ptr<list<Op::Row_ptr> > >::
            iterator pos = queries.find(select);
        if (pos != queries.end()) {
            pair<Op::Select_ptr,
                boost::shared_ptr<list<Op::Row_ptr> > > r = *pos;
            
            
            for (list<Op::Row_ptr>::iterator i = r.second->begin();
                 i != r.second->end(); ++i) {
                map<Op::Row_ptr, list<Op::Select_ptr> >::iterator p = 
                    rows.find(*i);
                if (p != rows.end()) {
                    for (list<Op::Select_ptr>::iterator j = rows[*i].begin();
                         j != rows[*i].end();
                         ++j) {
                        l.push_back(*j);
                    }
                    rows.erase(*i);
                }
            }

            queries.erase(pos);
        }

        l.pop_front();
    }

    // Finally, inform the application.
    original_cb();
}

}
