#include <vector>
#include <boost/lexical_cast.hpp>
#include "sqlitendb.hh"
#include "timeval.hh"
#include "vlog.hh"

using namespace vigil;
static Vlog_module lg("ndb");

namespace vigil {

class NullExtractor 
    : public NDB {
public:
    OpStatus init(const Callback& = 0) { return OK; }

    OpStatus create_table(const std::string&,
                          const std::list<std::pair<std::string, Op::ValueType> >&,
                          const std::list<std::list<std::string> >&,
                          const Callback& = 0) {
        return OK;
    }
    
    OpStatus drop_table(const std::string&,
                        const Callback& = 0) {
        return OK;
    }
    
    OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&,
                     const Callback& = 0)  {
        return OK;
    }
    
    OpStatus execute(const std::list<boost::shared_ptr<PutOp> >&,
                     const std::list<boost::shared_ptr<GetOp> >&,
                     const Callback& = 0) {
        return OK;
    }

    OpStatus sync(const Callback& = 0) {
        return OK;
    }

    OpStatus connect_extractor(NDB*) { 
        return OK; 
    }
    
    timeval get_commit_period() {
        timeval tv;
        return tv;
    }

    Co_cond* get_commit_change_condition() {
        return 0;
    }
};

NDB::OpStatus
SQLiteNDB::init(const NDB::Callback& f) {
    using namespace std;

    assert(f == 0);

    string query("BEGIN");    
    int err = SQLITE_OK;
    boost::shared_ptr<PreparedStatement> s;

    if (cached_statements.find(query) == cached_statements.end()) {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Preparing: %s", query.c_str());
        }
        const char *unused_sql;
        ::sqlite3_stmt *stmt; 

        err = ::sqlite3_prepare_v2(sqlite, query.c_str(), 
                                   strlen(query.c_str()), 
                                   &stmt, &unused_sql);
        s.reset(new PreparedStatement(stmt, query));
    } else {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Cached: %s", query.c_str());
        }
        s = cached_statements[query];
    }

    const Op::Results_ptr 
        results = Op::Results_ptr(new Op::Results());
    err = s->execute(results);
    
    if (err != SQLITE_DONE) {
        lg.err("Unable to execute the BEGIN statement: %d", err);
        return convert_error(err);
    } else {
        err = SQLITE_OK;
    }
    
    cache_statement(s);
    
    connect_extractor(new NullExtractor());

    return convert_error(err);
}

NDB::OpStatus
SQLiteNDB::execute(const std::list<boost::shared_ptr<GetOp> >& q,
                   const NDB::Callback& f) {
    using namespace std;

    assert(f == 0);

    int err = SQLITE_OK;
    list<Op::Results_ptr> collected_results;

    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end(); ++i) {
        if (tables.find((*i)->get_table()) == tables.end()) {
            lg.err("Table not defined: %s", (*i)->get_table().c_str());
            return GENERAL_ERROR;
        }
    }
    
    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {

        Op::Results_ptr results = Op::Results_ptr(new Op::Results());
        err = execute(**i, results);

        if (err != SQLITE_OK) {
            break;
        }

        collected_results.push_back(results);        
    }
    if (err != SQLITE_OK) {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Unable to execute the statement: %d", err);
        }
        return convert_error(err);
    }

    // Once all GetOps have been executed successfully, inject the
    // results to the parameters.
    for (list<boost::shared_ptr<GetOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {        
        (*i)->set_results(collected_results.front());
        collected_results.pop_front();
    }   

    for (Extractor_List::iterator i = extractors.begin();
         i != extractors.end(); ++i) {
        (*i)->execute(q, f);
    }

    return OK;
}

int
SQLiteNDB::execute(const GetOp &get,
                   Op::Results_ptr& results) const {
    using namespace std;

    int err = SQLITE_OK;    

    boost::shared_ptr<PreparedStatement> stmt = prepare(get, &err);
    if (err != SQLITE_OK) {
        lg.err("Unable to create a statement: %d", err);
        return err;
    }

    // Bind the variables
    const Op::Select_ptr select = get.get_select();
    err = stmt->bind(select);
    if (err != SQLITE_OK) {
        lg.err("Unable to bind the statement variables: %d", err);
        return err;
    }
    
    lg.dbg("Executing SQL.");

    err = stmt->execute(results);
    if (err != SQLITE_DONE) {
        lg.err("Unable to execute the statement: %d", err);
        return err;
    } else {
        err = SQLITE_OK;
    }

    cache_statement(stmt);

    return err;
}

NDB::OpStatus
SQLiteNDB::execute(const std::list<boost::shared_ptr<PutOp> >& q, 
                   const std::list<boost::shared_ptr<GetOp> >& d,
                   const NDB::Callback& f) {
    using namespace std;

    assert(f == 0);

    // Sanity check for the tables
    for (list<boost::shared_ptr<GetOp> >::const_iterator i = d.begin();
         i != d.end(); ++i) {
        if (tables.find((*i)->get_table()) == tables.end()) {
            lg.err("Table not defined: %s", (*i)->get_table().c_str());
            return GENERAL_ERROR;
        }
    }

    for (list<boost::shared_ptr<PutOp> >::const_iterator i = q.begin(); 
         i != q.end(); ++i) {
        if (tables.find((*i)->get_table()) == tables.end()) {
            lg.err("Table not defined: %s", (*i)->get_table().c_str());
            return GENERAL_ERROR;
        }
    }
            
    // First, check the dependencies
    int err = SQLITE_OK;

    for (list<boost::shared_ptr<GetOp> >::const_iterator i = d.begin();
         i != d.end();
         ++i) {
        lg.dbg("Executing a GetOp dependency.");

        Op::Results_ptr new_results(new Op::Results());
        err = execute(**i, new_results);
        if (err != SQLITE_OK) {
            lg.err("Unable to check the dependencies: %d", err);
            return convert_error(err);
        }

        // Compare the results
        struct equal_to<Op::Results_ptr> f;
        if (!f(new_results, (*i)->get_results())) {
            lg.dbg("Dependency check fails.");
            return DEPENDENCY_ERROR;
        }
    }

    // Second, execute the puts.
    for (list<boost::shared_ptr<PutOp> >::const_iterator i = q.begin(); 
         i != q.end();
         ++i) {
        lg.dbg("Executing a PutOp.");

        boost::shared_ptr<PutOp> put = *i;        

        // Delete rows, if any
        if (put->get_replace().get()) {
            boost::shared_ptr<PreparedStatement> stmt = 
                prepare_delete(*put, &err);
            if (err != SQLITE_OK) {
                lg.err("Unable to create a statement: %d", err);
                return convert_error(err);
            }
            
            // Bind the variables
            const Op::Select_ptr select = put->get_replace();
            err = stmt->bind(select);    
            if (err != SQLITE_OK) {
                lg.err("Unable to bind the statement variables: %d", err);
                return convert_error(err);
            }
            
            lg.dbg("Executing DELETE.");
            
            const Op::Results_ptr results = Op::Results_ptr(new Op::Results());
            err = stmt->execute(results);
            
            if (err != SQLITE_DONE) {
                lg.err("Unable to execute the statement: %d", err);
                return convert_error(err);
            }

            cache_statement(stmt);
        }

        // Insert rows, if any
        if (put->get_row().get()) {
            boost::shared_ptr<PreparedStatement> stmt = 
                prepare_insert(*put, &err);
            if (err != SQLITE_OK) {
                lg.err("Unable to create a statement: %d", err);
                return convert_error(err);
            }
            
            // Bind the variables
            const Op::Row_ptr row = put->get_row();
            err = stmt->bind(row);    
            if (err != SQLITE_OK) {
                lg.err("Unable to bind the statement variables: %d", err);
                return convert_error(err);
            }
            
            lg.dbg("Executing INSERT.");
            const Op::Results_ptr results = Op::Results_ptr(new Op::Results());
            err = stmt->execute(results);
            
            if (err != SQLITE_DONE) {
                lg.err("Unable to execute the statement: %d", err);
                return convert_error(err);
            }

            cache_statement(stmt);

        }
    }

    /// XXX: transactional semantics for put

    for (Extractor_List::iterator i = extractors.begin();
         i != extractors.end(); ++i) {
        (*i)->execute(q, d, f);
    }

    return OK;
}

NDB::OpStatus
SQLiteNDB::sync(const NDB::Callback& f) {
    using namespace std;

    assert(f == 0);

    lg.dbg("COMMITing...");

    string query("COMMIT");    
    int err = SQLITE_OK;
    boost::shared_ptr<PreparedStatement> s;

    if (cached_statements.find(query) == cached_statements.end()) {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Preparing: %s", query.c_str());
        }
        const char *unused_sql;
        ::sqlite3_stmt *stmt; 

        err = ::sqlite3_prepare_v2(sqlite, query.c_str(), 
                                   strlen(query.c_str()), 
                                   &stmt, &unused_sql);
        s.reset(new PreparedStatement(stmt, query));
    } else {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Cached: %s", query.c_str());
        }
        s = cached_statements[query];
    }

    const Op::Results_ptr results = Op::Results_ptr(new Op::Results());
    err = s->execute(results);
    
    if (err != SQLITE_DONE) {
        lg.err("Unable to execute the COMMIT statement: %d", err);
        return convert_error(err);
    }
    
    cache_statement(s);

    // Forward the call, if necessary.
    for (Extractor_List::iterator i = extractors.begin();
         i != extractors.end(); ++i) {
        (*i)->sync(f);
    }

    return init();
}

NDB::OpStatus 
SQLiteNDB::connect_extractor(NDB* e) {
    extractors.push_back(e);
    return OK;
}

NDB::OpStatus 
SQLiteNDB::convert_error(int error) {
    switch (error) {
    case SQLITE_OK:
        return OK;

    default:
        return GENERAL_ERROR;
    }
}

boost::shared_ptr<PreparedStatement> 
SQLiteNDB::prepare(const GetOp &op, int *err) const {
    using namespace std;
    
    const Op::Select_ptr select = op.get_select();
    const string table = op.get_table();
    
    lg.dbg("Generating a SQL SELECT statement.");
    
    string query = string("SELECT * FROM ") +
        table;
    for (Op::Select::const_iterator i = 
             select->begin(); 
         i != select->end();
         ++i) {
        
        if ((*i)->type == Op::NONE) {
            query += i == select->begin() ?
                " WHERE " + ((*i)->key) + " IS NULL":
                " AND " + ((*i)->key) + " IS NULL";
        } else {
            query += i == select->begin() ?
                " WHERE " + ((*i)->key) + " = ?":
                " AND " + ((*i)->key) + " = ?";
        }
    }

    if (cached_statements.find(query) == cached_statements.end()) {
        if (lg.is_dbg_enabled()) {
            lg.dbg("Preparing: %s", query.c_str());
        }
        const char *unused_sql;
        ::sqlite3_stmt *stmt; 

        *err = ::sqlite3_prepare_v2(sqlite, query.c_str(), 
                                    strlen(query.c_str()), 
                                    &stmt, &unused_sql);
        boost::shared_ptr<PreparedStatement> 
            s(new PreparedStatement(stmt, query));
        return s;
    } else {
        *err = SQLITE_OK;
        if (lg.is_dbg_enabled()) {
            lg.dbg("Cached: %s", query.c_str());
        }
        return cached_statements[query];
    }
}

NDB::OpStatus 
SQLiteNDB::create_table(const std::string& table,
                        const std::list<std::pair<std::string, Op::ValueType> >& columns,
                        const std::list<std::list<std::string> >& indices,
                        const Callback& f) {
    using namespace std;

    assert(f == 0);

    if (tables.find(table) != tables.end()) {
        return INVALID_SCHEMA_TYPE;
    }

    string query = string("CREATE TABLE ") + table + "(";

    for (list<pair<string, Op::ValueType> >::const_iterator i = 
             columns.begin(); i != columns.end(); ++i) {
        pair<string, Op::ValueType> c = *i;

        query += i == columns.begin() ? c.first : ", " + c.first;

        switch (c.second) {
        case Op::NONE:
            return INVALID_SCHEMA_TYPE;

        case Op::INT:
            query += " INTEGER";
            break;

        case Op::DOUBLE:
            query += " DOUBLE";
            break;

        case Op::TEXT:
            query += " TEXT";
            break;

        case Op::BLOB:
            query += " BLOB";
            break;
        };
    }

    query += ")";    

    if (lg.is_dbg_enabled()) {
        lg.dbg("Executing a SQL CREATE TABLE statement: %s", query.c_str());
    }

    int err = ::sqlite3_exec(sqlite, query.c_str(), 0, 0, 0);
    if (err != SQLITE_OK) {
        return convert_error(err);
    }

    int index = 1;
    for (list<list<string> >::const_iterator i = 
             indices.begin(); i != indices.end(); ++i) {
        
        string index_name = string(table) + "_" + boost::lexical_cast<string>(index++);
        string query = string("CREATE INDEX ") + index_name + " ON " + table + "(";

        list<string> c = *i;
        
        for (list<string>::const_iterator j = c.begin(); j != c.end(); ++j) {
            query += j == c.begin() ? *j : ", " + *j;
        }

        query += ")";    

        if (lg.is_dbg_enabled()) {
            lg.dbg("Executing a SQL CREATE INDEX statement: %s", query.c_str());
        }

        err = ::sqlite3_exec(sqlite, query.c_str(), 0, 0, 0);
        if (err != SQLITE_OK) {
            drop_table(table);
            return convert_error(err);
        }
    }

    // Store the table information and forward the call.
    tables[table] = columns;

    for (Extractor_List::iterator i = extractors.begin(); 
         i != extractors.end(); ++i) {
        (*i)->create_table(table, columns, indices, f);
    }

    return OK;
}

NDB::OpStatus 
SQLiteNDB::drop_table(const std::string& table, const Callback& f) {
    using namespace std;

    assert(f == 0);

    string query = string("DROP TABLE IF EXISTS ") + table;

    if (lg.is_dbg_enabled()) {
        lg.dbg("Executing a SQL DROP TABLE statement: %s", query.c_str());
    }

    int err = ::sqlite3_exec(sqlite, query.c_str(), 0, 0, 0);

    // Remove the table information and stop the dumping process.
    if (err == SQLITE_OK) {
        tables.erase(table);

        for (Extractor_List::iterator i = extractors.begin();
             i != extractors.end(); ++i) {
            (*i)->drop_table(table, f);
        }
    }

    return convert_error(err);
}

boost::shared_ptr<PreparedStatement> 
SQLiteNDB::prepare_insert(const PutOp& op, int *err) const {
    using namespace std;
    
    const Op::Row_ptr row = op.get_row();
    const string table = op.get_table();

    lg.dbg("Generating a SQL INSERT statement.");
    
    string query = string("INSERT INTO ") +
        table +
        "(";
    string val("");
    for (Op::Row::const_iterator i = row->begin(); i != row->end(); ++i) {
        query += i == row->begin() ?
            ((*i)->key) :
            ", " + ((*i)->key);
        // Hardcode NULL values in SQL, seems to work better with
        // SQLite
        if ((*i)->type == Op::NONE) { 
            val += i == row->begin() ? 
                "NULL" :
                ", NULL";
        } else {
            val += i == row->begin() ?
                "?" :
                ", ?";
        }
    }
    query += ") VALUES (" + val + ")";

    if (cached_statements.find(query) == cached_statements.end()) {
        const char *unused_sql;
        ::sqlite3_stmt *stmt; 

        *err = ::sqlite3_prepare_v2(sqlite, query.c_str(), 
                                    strlen(query.c_str()), 
                                    &stmt, &unused_sql);
        boost::shared_ptr<PreparedStatement> 
            s(new PreparedStatement(stmt, query));
        return s;
    } else {
        *err = SQLITE_OK;
        if (lg.is_dbg_enabled()) {
            lg.dbg("Cached SQL statement: %s", query.c_str());
        }
        return cached_statements[query];
    }
}

boost::shared_ptr<PreparedStatement> 
SQLiteNDB::prepare_delete(const PutOp& op, int *err) const {
    using namespace std;
    
    const Op::Select_ptr select = op.get_replace();
    const string table = op.get_table();

    lg.dbg("Generating a SQL DELETE statement.");
    
    string query = string("DELETE FROM ") +
        table;
    for (Op::Select::const_iterator i = select->begin(); i != select->end();
         ++i) {
        
        query += i == select->begin() ?
            " WHERE " + ((*i)->key) + " = ?":
            " AND " + ((*i)->key) + " = ?";
    }
    if (lg.is_dbg_enabled()) {
        lg.dbg("%s", query.c_str());        
    }

    if (cached_statements.find(query) == cached_statements.end()) {
        const char *unused_sql;
        ::sqlite3_stmt *stmt; 

        *err = ::sqlite3_prepare_v2(sqlite, query.c_str(), 
                                    strlen(query.c_str()), 
                                    &stmt, &unused_sql);
        boost::shared_ptr<PreparedStatement> 
            s(new PreparedStatement(stmt, query));
        return s;
    } else {
        *err = SQLITE_OK;
        if (lg.is_dbg_enabled()) {
            lg.dbg("Found cached SQL statement: %s", query.c_str());
        }
        return cached_statements[query];
    }
}

void 
SQLiteNDB::cache_statement(const boost::shared_ptr<PreparedStatement>& stmt) const {
    cached_statements[stmt->get_query()] = stmt;
        
    if (lg.is_dbg_enabled()) {
        lg.dbg("Total %d cached SQL statements.", cached_statements.size());
    }
}

int 
PreparedStatement::bind(const Op::Select_ptr& select) const {
    using namespace std;

    lg.dbg("Binding SQL variables.");

    int k = 0;
    int err = SQLITE_OK;

    for (Op::Select::const_iterator j = select->begin(); j != select->end();
         ++j) {
        boost::shared_ptr<Op::KeyValue> kv = *j;
        ++k;

        switch (kv->type) {
        case Op::NONE:
            // NULL values are hardcoded into SQL, since it seems to
            // work better with SQLite.
            --k;
            break;

        case Op::INT:
            err = ::sqlite3_bind_int64(stmt, k, kv->int_val);
            break;

        case Op::DOUBLE:
            err = ::sqlite3_bind_double(stmt, k, kv->double_val);
            break;

        case Op::BLOB:
            err = ::sqlite3_bind_blob(stmt, k, kv->blob_val,
                                      kv->blob_len,
                                      SQLITE_TRANSIENT);
            break;

        case Op::TEXT:
            err = ::sqlite3_bind_text(stmt, k, kv->text_val.c_str(), 
                                      strlen(kv->text_val.c_str()), 
                                      SQLITE_TRANSIENT);
            // XXX: is transient optimal?
            break;
        }
        
        if (err != SQLITE_OK) { break; }
    }

    return err;
}

int PreparedStatement::execute(const Op::Results_ptr& results) const {
    using namespace std;
    int err = SQLITE_OK;
    do {
        boost::shared_ptr<vector<Op::KeyValue_ptr> > 
            row(new vector<Op::KeyValue_ptr>);
        err = ::sqlite3_step(stmt);
        
        switch (err) {
        case SQLITE_ROW:
            for (int k = 0; k < ::sqlite3_column_count(stmt); ++k) {
                const string key(::sqlite3_column_name(stmt, k));
                
                Op::KeyValue* s = 0;
                switch (::sqlite3_column_type(stmt, k)) {
                case SQLITE_NULL:
                    s = new Op::KeyValue(key);
                    break;
                case SQLITE_INTEGER:
                    s = new Op::KeyValue(key,
                                         (int64_t)::
                                         sqlite3_column_int64(stmt, k));
                    break;

                case SQLITE_FLOAT:
                    s = new Op::KeyValue(key,
                                         ::sqlite3_column_double(stmt, k));
                    break;

                case SQLITE_TEXT:
                    s = new Op::KeyValue(key, 
                                         string((char *)
                                                ::sqlite3_column_text(stmt, k)));
                    break;

                case SQLITE_BLOB:
                    s = new Op::KeyValue(key, 
                                         ::sqlite3_column_bytes(stmt, k),
                                         (const uint8_t*)::sqlite3_column_blob(stmt, k));
                    break;
                }
                
                Op::KeyValue_ptr r(s);
                row->push_back(r);
            }
        
            // Sort the row.
            // XXX: unnecessary copying.
            {
                ColumnKeyComp f;
                sort(row->begin(), row->end(), f);
                Op::Row_ptr r(new Op::Row(row->begin(), row->end()));
                results->push_back(r);
            }
    
            break;
            
        default:
            break;
        }
    } while (err == SQLITE_ROW);

    ::sqlite3_reset(stmt);
    return err;
}

} // namespace vigil
