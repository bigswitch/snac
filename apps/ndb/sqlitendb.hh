#ifndef CONTROLLER_SQLITE_NDB_HH
#define CONTROLLER_SQLITE_NDB_HH 1

#include <list>
#include <sqlite3.h>
#include "ndb.hh"

namespace vigil {

/* A wrapper for SQLite3 prepared statement. */
class PreparedStatement {
public:
    PreparedStatement(sqlite3_stmt* s, const std::string& q) 
        : stmt(s), query(q) { };

    ~PreparedStatement() { sqlite3_finalize(stmt); };

    int bind(const Op::Select_ptr&) const;

    int execute(const Op::Results_ptr&) const;

    const std::string& get_query() const { return query; };

private:
    sqlite3_stmt* stmt;

    const std::string query;
};

struct ColumnKeyComp 
    : public std::binary_function<Op::KeyValue_ptr,
                                  Op::KeyValue_ptr,
                                  bool>
{
    bool operator()(const Op::KeyValue_ptr& kv1,
                    const Op::KeyValue_ptr& kv2) const {
        return kv1->key < kv2->key;
    }
};

class SQLiteNDB
    : public NDB
{
public:
    SQLiteNDB(const std::string& database) {
        // According to SQLite documentation it's thread-safe to pass
        // a database connection from thread to another if it holds no
        // locks.
        const int err = ::sqlite3_open(database.c_str(), &sqlite);
        if (err != SQLITE_OK) {
            char msg[256];
            snprintf(msg, sizeof msg, "unable to open SQLite engine: %d", err);
            throw std::runtime_error(msg);
        }        
    }

    ~SQLiteNDB() { sqlite3_close(sqlite); }

    OpStatus init(const Callback& = 0);

    OpStatus create_table(const std::string&,
                          const std::list<std::pair<std::string, Op::ValueType> >&,
                          const std::list<std::list<std::string> >&,
                          const Callback& = 0);

    OpStatus drop_table(const std::string&,
                        const Callback& = 0); 

    OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&,
                     const Callback& = 0); 

    OpStatus execute(const std::list<boost::shared_ptr<PutOp> >&,
                     const std::list<boost::shared_ptr<GetOp> >&,
                     const Callback& = 0); 

    OpStatus sync(const Callback& = 0);

    OpStatus connect_extractor(NDB*);

    timeval get_commit_period();
    Co_cond* get_commit_change_condition();

private:
    void set_commit_period(const timeval&);

    boost::shared_ptr<PreparedStatement> 
    prepare(const GetOp&, int*) const;

    boost::shared_ptr<PreparedStatement> 
    prepare_insert(const PutOp&, int*) const;

    boost::shared_ptr<PreparedStatement> 
    prepare_delete(const PutOp&, int*) const;

    int execute(const GetOp&, Op::Results_ptr&) const;

    void cache_statement(const boost::shared_ptr<PreparedStatement>&) const;

    OpStatus convert_error(int);

    /* Cached statements */
    mutable hash_map<std::string, boost::shared_ptr<PreparedStatement>
                     > cached_statements;

    /* Defined tables */
    hash_map<std::string,
             std::list<std::pair<std::string, Op::ValueType> > > tables;

    /* Connected extractors */
    typedef std::list<NDB*> Extractor_List;
    Extractor_List extractors;

    sqlite3* sqlite;
};

} // namespace vigil

#endif /* controller/sqlitendb.hh */
