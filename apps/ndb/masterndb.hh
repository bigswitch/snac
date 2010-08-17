#ifndef CONTROLLER_NDB_MASTER_HH
#define CONTROLLER_NDB_MASTER_HH 1

#include <sqlite3.h>
#include <algorithm>
#include <list>

#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/thread.hpp>

#include "hash_map.hh"
#include "ndb.hh"
#include "lockndb.hh"
#include "threads/cooperative.hh"
#include "threads/native-pool.hh"
#include "vlog.hh"
#include "sqlitendb.hh"

namespace vigil {

struct trigger_hash
    : public std::unary_function<Op::Select_ptr, std::size_t> 
{
    std::size_t 
    operator()(const Op::Select_ptr& select) const {
        uint32_t x = 0;

        for (Op::Select::const_iterator i = select->begin();
             i != select->end(); ++i) {
            const char *key = (*i)->key.c_str();
            x = vigil::fnv_hash(key, strlen(key), x);
        }
        return x;
    }
};

struct trigger_equal_to
    : public std::unary_function<Op::Select_ptr, bool>
{
    bool 
    operator()(const Op::Select_ptr& s1,
               const Op::Select_ptr& s2) const {
        using namespace std;

        Op::Select::const_iterator i = s1->begin();
        Op::Select::const_iterator j = s2->begin();

        while (true) {
            if (i == s1->end() || j == s2->end()) {
                return (i == s1->end() && j == s2->end());
            }

            if ((*i)->key != (*j)->key) {
                return false;
            }

            ++i; ++j;
        }
    }
};

/**
 * Network database.
 * 
 * For documentation of the interface, please see
 * doc/Network_Database.txt.
 *
 */
class MasterNDB
    : public NDB, public container::Component
{
public:
    MasterNDB(const container::Context*,
              const json_object*);

    OpStatus init(const boost::function<void(OpStatus)>& = 0);

    OpStatus create_table(const std::string&,
                          const ColumnDef_List&,
                          const IndexDef_List&,
                          const Callback& = 0);

    OpStatus drop_table(const std::string&,
                        const NDB::Callback& = 0); 

    OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&,
                     const NDB::Callback& = 0); 

    OpStatus execute(const std::list<boost::shared_ptr<PutOp> >&,
                     const std::list<boost::shared_ptr<GetOp> >&,
                     const NDB::Callback& = 0); 

    OpStatus sync(const NDB::Callback& = 0);
    
    OpStatus connect_extractor(NDB*);

protected:
    void configure(const container::Configuration*);

    void install();

private:
    // Invalidation management methods

    void insert_callbacks(const std::list<boost::shared_ptr<GetOp> >&,
                          const NDB::Callback& = 0,
                          const OpStatus& = OK);

    void trigger_callbacks(const std::list<boost::shared_ptr<PutOp> >&,
                           const NDB::Callback& = 0,
                           const OpStatus& = OK);

    void trigger_callback(const std::string&,
                          const Op::Row&);

    void syncer();

    void init_sqlite(SQLiteNDB*);

    const LockManager lockmgr;
    
    /** Triggers */
    typedef hash_map<
        Op::Select_ptr,
        boost::shared_ptr<std::list<boost::function<void()> > >,
        trigger_hash,
        trigger_equal_to> Trigger_map;
    
    
    hash_map<std::string, boost::shared_ptr<Trigger_map> >
    triggers;

    Native_thread_pool<OpStatus, SQLiteNDB> n;

    Co_thread sync_thread;

    bool running;

    SQLiteNDB* s;
};

// Once a row change occurs, to determine the affected cached queries
// the master computes all combinations of the row.

template <typename T,
          template <typename,
                    typename = std::allocator<T> > class Cont>
inline
void 
combinations(const typename Cont<T>::iterator& b,
             const typename Cont<T>::iterator& e,
             const int n,
             const boost::function<void(const Cont<T>&)>& cb,
             const Cont<T>& r = Cont<T>()) {
    using namespace std;

    if (n == 0) {
        cb(r);
        return;
    }

    typename Cont<T>::iterator e2 = e;
    for (int i = 0; i < n - 1; ++i) {
        --e2;
    }

    for (typename Cont<T>::iterator i = b; i != e2; ++i) {
        typename Cont<T>::iterator b2 = i;
        ++b2;
        Cont<T> r2 = r;
        r2.push_back(*i);
        combinations(b2, e, n - 1, cb, r2);
    }
}

} // namespace vigil

#endif /* controller/masterndb.hh */
