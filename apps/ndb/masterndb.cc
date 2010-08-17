#include "masterndb.hh"
#include <boost/bind.hpp>
#include "threads/native-pool.hh"
#include "timeval.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;

static Vlog_module lg("ndb");

namespace vigil {

MasterNDB::MasterNDB(const Context* c,
                     const json_object*)
    : Component(c), n(1), running(true), s(0) {

};

void 
MasterNDB::configure(const container::Configuration*) {
    s = new SQLiteNDB("");
}

void
MasterNDB::install() {
    n.add_worker(s, boost::bind(&MasterNDB::init_sqlite, this, s));
    sync_thread.start(boost::bind(&MasterNDB::syncer, this));
};

void 
MasterNDB::init_sqlite(SQLiteNDB* s) {
    s->init();
}

NDB::OpStatus 
MasterNDB::init(const boost::function<void(OpStatus)>& f) {
    return OK;
}

NDB::OpStatus 
MasterNDB::create_table(const string& table,
                        const list<pair<string, Op::ValueType> >& columns,
                        const list<list<string> >& indices,
                        const NDB::Callback& f) {
    if (!f.empty()) {
        n.execute(boost::bind(&NDB::create_table, _1, 
                              table, columns, indices, (NDB::Callback)0), f);
        return OK;
    } else {
        return n.execute(boost::bind(&NDB::create_table, _1, 
                                     table, columns, indices, (NDB::Callback)0));
    }
}

NDB::OpStatus 
MasterNDB::drop_table(const string& table,
                      const NDB::Callback& f) {
    if (!f.empty()) {
        n.execute(boost::bind(&NDB::drop_table, _1, 
                              table, (NDB::Callback)0), f);
        return OK;
    } else {
        return n.execute(boost::bind(&NDB::drop_table, _1, 
                                     table, (NDB::Callback)0));
    }
}

NDB::OpStatus
MasterNDB::execute(const list<boost::shared_ptr<GetOp> >& q,
                   const NDB::Callback& f) {
    typedef NDB::OpStatus(NDB::* ex)(const list<boost::shared_ptr<GetOp> >&,
                                     const Callback&);
    
    if (!f.empty()) {
        n.execute(boost::bind(static_cast<ex>(&NDB::execute), _1, q, (Callback)0), 
                  boost::bind(&MasterNDB::insert_callbacks, this, q, f, _1));
        return OK;

    } else {
        OpStatus result = 
            n.execute(boost::bind(static_cast<ex>(&NDB::execute), _1, q, (Callback)0)); 
        insert_callbacks(q);
        return result;
    }
}

NDB::OpStatus
MasterNDB::execute(const list<boost::shared_ptr<PutOp> >& q,
                   const list<boost::shared_ptr<GetOp> >& d,
                   const NDB::Callback& f) {
    typedef NDB::OpStatus(NDB::* ex)(const list<boost::shared_ptr<PutOp> >&,
                                     const list<boost::shared_ptr<GetOp> >&,
                                     const Callback&);
    if (!f.empty()) {
        n.execute(boost::bind(static_cast<ex>(&NDB::execute), _1, q, d, (NDB::Callback)0),
                  boost::bind(&MasterNDB::trigger_callbacks, this, q, f, _1));
        return OK;
    } else {
        OpStatus result = 
            n.execute(boost::bind(static_cast<ex>(&NDB::execute), _1, q, d, 
                                  (NDB::Callback)0));
        trigger_callbacks(q);
        return result;
    }
}

NDB::OpStatus 
MasterNDB::sync (const NDB::Callback& f) {
    if (!f.empty()) {
        n.execute(boost::bind(&NDB::sync, _1, (NDB::Callback)0), f);
        return OK;
    } else {
        return n.execute(boost::bind(&NDB::sync, _1, (NDB::Callback)0));
    }
}

NDB::OpStatus
MasterNDB::connect_extractor(NDB *ndb) {
    return s->connect_extractor(ndb);
}

void
MasterNDB::syncer() {
    while (running) {
        co_timer_wait(do_gettimeofday() + get_commit_period(), NULL);
        get_commit_change_condition()->wait();
        co_block();
        if (sync() != OK) {
            lg.err("Unable to sync the database to disk.");
        }
    }
}

void 
MasterNDB::insert_callbacks(const list<boost::shared_ptr<GetOp> >& q,
                            const NDB::Callback& f,
                            const NDB::OpStatus& result) {
    using namespace std;

    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {  
        const GetOp& get = **i;

        if (!get.get_callback()) {
            continue;
        }

        boost::shared_ptr<Trigger_map> p;
        
        if (triggers.find(get.get_table()) == triggers.end()) {
            p = boost::shared_ptr<Trigger_map>(new Trigger_map);
            triggers[get.get_table()] = p;
        } else {
            p = triggers[get.get_table()];
        }
        
        boost::shared_ptr<list<boost::function<void()> > > l;
        
        if (p->find(get.get_select()) == p->end()) {
            l = 
                boost::shared_ptr<list<boost::function<void()> > >
                (new list<boost::function<void()> >);
            
            (*p)[get.get_select()] = l;
        } else {
            l = (*p)[get.get_select()];
        }
        
        l->push_back(get.get_callback());
    }

    if (f) {
        f(result);
    }
}

void 
MasterNDB::trigger_callback(const string& table, 
                            const Op::Row& kv) {
    using namespace std;

    if (triggers.find(table) == triggers.end()) {
        return;
    }

    // This is unnecessary copying, but have to do for now since the
    // triggers table is keyed based on boost::shared_ptr<list> and
    // not on a plain list.
    Op::Row_ptr p(new Op::Row(kv.begin(), kv.end()));
    if ((*triggers[table]).find(p) == (*triggers[table]).end()) {
        return;
    }
    
    boost::shared_ptr<list<boost::function<void()> > > callbacks =
        (*triggers[table])[p];    
    for (list<boost::function<void()> >::const_iterator cb = callbacks->begin();
         cb != callbacks->end();
         ++cb) {
        (*cb)();
    }

    // Remove the triggers.
    (*triggers[table])[p] =
        boost::shared_ptr<list<boost::function<void()> > >
        (new list<boost::function<void()> >);
}

void 
MasterNDB::trigger_callbacks(const list<boost::shared_ptr<PutOp> >& q,
                             const NDB::Callback& f,
                             const NDB::OpStatus& result) {
    using namespace std;
    
    for (list<boost::shared_ptr<PutOp> >::const_iterator i = q.begin(); 
         i != q.end(); ++i) {
        const PutOp& put = **i;
        
        // Trigger any table-wide trigger.
        Op::Row r;
        trigger_callback(put.get_table(), r);
        
        // Trigger any get() depending on any combination of the put row.      
        Op::Row_ptr row = put.get_row();
        
        if (!row.get()) {
            continue;
        }
        
        for (int k = 1; k < row->size() + 1; ++k) {
            combinations<Op::KeyValue_ptr,
                list>(row->begin(), row->end(), k, 
                           boost::bind(&MasterNDB::trigger_callback, this, 
                                       put.get_table(), _1));
        }
    }

    if (f) {
        f(result);
    }
}

} // namespace vigil
