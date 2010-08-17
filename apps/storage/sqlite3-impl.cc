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
#include <boost/algorithm/string/join.hpp>
#include <boost/bind.hpp>
#include <boost/foreach.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/variant/apply_visitor.hpp>

#include "fault.hh"
#include "sqlite3-impl.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::storage;

static Vlog_module lg("sqlite3-impl");

enum Trigger_types { SQL_INSERT = 0, SQL_DELETE, SQL_UPDATE };

typedef void(*SQLite_function)(sqlite3_context*, int, sqlite3_value**);

#define SQLITE3_EXEC(SQL)                                               \
    do {                                                                \
        string sql = string(SQL);                                       \
        lg.dbg("SQLite> '%s'", sql.c_str());                            \
        if (::sqlite3_exec(sqlite, sql.c_str(), 0, 0, 0)) {             \
            throw SQLite_error(sqlite);                                 \
        }                                                               \
    } while (0);

/* SQLite wrappers throw an exception in error conditions. */
class SQLite_error
    : public exception {
public:
    SQLite_error(sqlite3* sqlite) {
        char msg[512];
        ::snprintf(msg, sizeof(msg), "SQLite error %d: %s",
                   ::sqlite3_errcode(sqlite), ::sqlite3_errmsg(sqlite));
        // XXX translate the exception into public API error
        result = Result(Result::UNKNOWN_ERROR, string(msg));
    }

    SQLite_error(const Result& r)
        : result(r) {
    }

    Result get_result() const {
        return result;
    }

    const char* what() const throw() {
        return result.message.c_str();
    }

private:
    Result result;
};

struct Column_binder
    : public boost::static_visitor<>
{
    Column_binder(sqlite3_stmt* stmt_) : err(SQLITE_OK), k(1), stmt(stmt_) { }

    void operator()(const int64_t& i) const {
        //lg.dbg("SQLite> binding %d", i);
        err = ::sqlite3_bind_int64(stmt, k++, i);
    }

    void operator()(const string& s) const {
        //lg.dbg("SQLite> binding '%s'", s.c_str());
        err = ::sqlite3_bind_text(stmt, k++, s.c_str(), ::strlen(s.c_str()),
                                  SQLITE_TRANSIENT);
    }

    void operator()(const double& d) const {
        //lg.dbg("SQLite> binding %f", d);
        err = ::sqlite3_bind_double(stmt, k++, d);
    }

    void operator()(const GUID& guid) const {
        //lg.dbg("SQLite> binding %s", guid.str().c_str());
        int64_t v;
        ::memcpy(&v, guid.guid, sizeof(v));
        err = ::sqlite3_bind_int64(stmt, k++, v);
    }

    mutable int err;
    mutable int k;

private:
    mutable sqlite3_stmt* stmt;
};

#define SQLITE3_PREPARE(STMT, QUERY, VALUES)                            \
    do {                                                                \
        const char* unused_sql = '\0';                                  \
        string sql(QUERY);                                              \
        lg.dbg("SQLite> '%s'", sql.c_str());                            \
        STMT = 0;                                                       \
        int err = ::sqlite3_prepare_v2(sqlite, sql.c_str(),             \
                                       strlen(sql.c_str()),             \
                                       &STMT, &unused_sql);             \
        if (STMT) {                                                     \
            Column_binder binder(STMT);                                 \
            BOOST_FOREACH(Column_value_map::value_type v, VALUES) {     \
                boost::apply_visitor(binder, v.second);                 \
                if (binder.err != SQLITE_OK) { break; }                 \
                err = binder.err;                                       \
            }                                                           \
        }                                                               \
                                                                        \
        if (err) {                                                      \
            lg.dbg("unused = '%s'", unused_sql);                        \
            throw SQLite_error(sqlite);                                 \
        }                                                               \
    } while(0);

Statement::Statement(SQLite_impl* impl_, sqlite3* sqlite_,
                     const Table_name& table_)
    : impl(impl_), sqlite(sqlite_), stmt(0), table(table_) {
}

Statement::~Statement() {
    lg.dbg("Closing a statement");
    ::sqlite3_finalize(stmt);
}

void
Statement::get(const Query& row) {
    assert(stmt == 0);

    string query;
    BOOST_FOREACH(Row::value_type v, row) {
        query += query == "" ? v.first + " = ?" : " AND " + v.first + " = ?";
    }

    query = "SELECT * FROM " + table + (row.empty() ? "" : " WHERE ") + query;
    SQLITE3_PREPARE(stmt, query, row);
}

struct Indexed_column_value_visitor
    : public boost::static_visitor<>
{
    Indexed_column_value_visitor(sqlite3_stmt* stmt_, int k_) :
        stmt(stmt_), k(k_) { }

    void operator()(const int64_t&) const {
        v = (int64_t)::sqlite3_column_int64(stmt, k);
    }

    void operator()(const string&) const {
        v = string((char *)::sqlite3_column_text(stmt, k));
    }

    void operator()(const double&) const {
        v = ::sqlite3_column_double(stmt, k);
    }

    void operator()(const GUID&) const {
        v = GUID((int64_t)::sqlite3_column_int64(stmt, k));
    }

    mutable sqlite3_stmt* stmt;
    mutable int k;
    mutable Column_value v;
};

Row
Statement::get_next() {
    Row row;
    int err = ::sqlite3_step(stmt);
    switch (err) {
    case SQLITE_ROW:
        for (int k = 0; k < ::sqlite3_column_count(stmt); ++k) {
            string key(::sqlite3_column_name(stmt, k));
            Indexed_column_value_visitor visitor(stmt, k);
            boost::apply_visitor(visitor, impl->tables[table].first[key]);
            row[key] = visitor.v;
        }

        return row;

    case SQLITE_DONE:
        ::sqlite3_reset(stmt);
        return row;

    default:
        throw SQLite_error(sqlite);
    }
}

GUID
Statement::put(const Row& row) {
    string val, query;

    assert(stmt == 0);

    BOOST_FOREACH(Row::value_type v, row) {
        query += query == "" ? v.first : ", " + v.first;
        val += val == "" ? "?" : ", ?";
    }

    query = "INSERT INTO " + table + "(" + query + ") VALUES (" + val + ")";
    SQLITE3_PREPARE(stmt, query, row);
    if (::sqlite3_step(stmt) != SQLITE_DONE) {
        throw SQLite_error(sqlite);
    }

    return GUID((int64_t)::sqlite3_last_insert_rowid(sqlite));
}

void
Statement::check_row_exists(const Row& row) {
    Query q;
    if (row.find("GUID") == row.end()) {
        q = row;
    } else {
        q["GUID"] = boost::get<GUID>(row.find("GUID")->second);
    }

    get(q);
    if (get_next().empty()) {
        throw SQLite_error(Result(Result::INVALID_ROW_OR_QUERY,
                                  "Row not found"));
    }

    ::sqlite3_finalize(stmt);
    stmt = 0;
}

void
Statement::modify(const Row& row_) {
    check_row_exists(row_);

    assert(stmt == 0);

    const GUID guid = boost::get<GUID>(row_.find("GUID")->second);
    Row row = row_;
    row.erase("GUID");

    string query;
    BOOST_FOREACH(Row::value_type v, row) {
        query += query == "" ? v.first + " = ?" : ", " + v.first + " = ?";
    }

    query = "UPDATE " + table + " SET " + query + " WHERE GUID = ?";
    SQLITE3_PREPARE(stmt, query, row);
    if (::sqlite3_bind_int64(stmt, row.size() + 1, guid.get_int())) {
        throw SQLite_error(sqlite);
    }

    if (::sqlite3_step(stmt) != SQLITE_DONE) {
        throw SQLite_error(sqlite);
    }
}

void
Statement::remove(const Row& row) {
    check_row_exists(row);

    assert(stmt == 0);

    string query;
    BOOST_FOREACH(Row::value_type v, row) {
        query += query == "" ? v.first + " = ?" : " AND " + v.first + " = ?";
    }

    query = "DELETE FROM " + table + (row.empty() ? "" : " WHERE ") + query;
    SQLITE3_PREPARE(stmt, query, row);
    if (::sqlite3_step(stmt) != SQLITE_DONE) {
        throw SQLite_error(sqlite);
    }
}

SQLite_impl::SQLite_impl(SQLite_storage* s, const char* database)
    : next_tid(0), storage(s) {

    lg.dbg("Opening the SQLite database at '%s'.", database);

    if (::sqlite3_open(database, &sqlite)) {
        throw SQLite_error(sqlite);
    }

    SQLITE3_EXEC("CREATE TABLE IF NOT EXISTS NOX_SCHEMA_META ("
                 "GUID INTEGER PRIMARY KEY NOT NULL,"
                 "NOX_TABLE TEXT NOT NULL,"
                 "NOX_TYPE INTEGER NOT NULL,"
                 "NOX_VERSION INTEGER NOT NULL)");
    SQLITE3_EXEC("CREATE TABLE IF NOT EXISTS NOX_SCHEMA_TABLE ("
                 "GUID INTEGER PRIMARY KEY NOT NULL,"
                 "NOX_TABLE TEXT NOT NULL,"
                 "NOX_COLUMN TEXT NOT NULL,"
                 "NOX_TYPE INTEGER NOT NULL)");
    SQLITE3_EXEC("CREATE TABLE IF NOT EXISTS NOX_SCHEMA_INDEX ("
                 "GUID INTEGER PRIMARY KEY NOT NULL,"
                 "NOX_TABLE TEXT NOT NULL,"
                 "NOX_INDEX TEXT NOT NULL,"
                 "NOX_COLUMN TEXT NOT NULL)");

    /* Add the hard-coded meta tables to the internal structures. */
    tables["NOX_SCHEMA_META"].first["GUID"] = GUID();
    tables["NOX_SCHEMA_META"].first["NOX_TABLE"] = "";
    tables["NOX_SCHEMA_META"].first["NOX_TYPE"] = (int64_t)0;
    tables["NOX_SCHEMA_META"].first["NOX_VERSION"] = (int64_t)1;
    tables["NOX_SCHEMA_META"].second["NOX_SCHEMA_META_INDEX_1"].name =
        string("NOX_SCHEMA_META_INDEX_1");
    tables["NOX_SCHEMA_META"].second["NOX_SCHEMA_META_INDEX_1"].columns.
        push_back("NOX_TABLE");
    tables["NOX_SCHEMA_TABLE"].first["GUID"] = GUID();
    tables["NOX_SCHEMA_TABLE"].first["NOX_TABLE"] = "";
    tables["NOX_SCHEMA_TABLE"].first["NOX_COLUMN"] = "";
    tables["NOX_SCHEMA_TABLE"].first["NOX_TYPE"] = (int64_t)0;
    tables["NOX_SCHEMA_TABLE"].second["NOX_SCHEMA_TABLE_INDEX_1"].name =
        string("NOX_SCHEMA_TABLE_INDEX_1");
    tables["NOX_SCHEMA_TABLE"].second["NOX_SCHEMA_TABLE_INDEX_1"].columns.
        push_back("NOX_TABLE");
    tables["NOX_SCHEMA_INDEX"].first["GUID"] = GUID();
    tables["NOX_SCHEMA_INDEX"].first["NOX_TABLE"] = "";
    tables["NOX_SCHEMA_INDEX"].first["NOX_INDEX"] = "";
    tables["NOX_SCHEMA_INDEX"].first["NOX_COLUMN"] = "";
    tables["NOX_SCHEMA_INDEX"].second["NOX_SCHEMA_INDEX_INDEX_1"].name =
        string("NOX_SCHEMA_INDEX_INDEX_1");
    tables["NOX_SCHEMA_INDEX"].second["NOX_SCHEMA_INDEX_INDEX_1"].columns.
        push_back("NOX_TABLE");

    lg.dbg("Reading the meta data tables in.");
    try {
    /* Read the schema */
    hash_set<Table_name> persistent_tables;
    {
    Statement stmt(this, sqlite, "NOX_SCHEMA_META");
    stmt.get(Query());
    for (Row row = stmt.get_next(); !row.empty(); row = stmt.get_next()) {
        if (boost::get<int64_t>(row["NOX_TYPE"]) == PERSISTENT) {
            persistent_tables.insert(boost::get<string>(row["NOX_TABLE"]));
        }
    }
    }

    {
    Statement stmt(this, sqlite, "NOX_SCHEMA_TABLE");
    stmt.get(Query());
    for (Row row = stmt.get_next(); !row.empty(); row = stmt.get_next()) {
        const Table_name table = boost::get<string>(row["NOX_TABLE"]);
        if (persistent_tables.find(table) == persistent_tables.end()){continue;}

        const Column_name column = boost::get<string>(row["NOX_COLUMN"]);
        const int64_t type = boost::get<int64_t>(row["NOX_TYPE"]);
        switch (type) {
        case COLUMN_INT:
            tables[table].first[column] = (int64_t)0;
            break;
        case COLUMN_TEXT:
            tables[table].first[column] = "";
            break;
        case COLUMN_DOUBLE:
            tables[table].first[column] = (double)0;
            break;
        case COLUMN_GUID:
            tables[table].first[column] = GUID();
            break;
        default:
            throw SQLite_error(Result(Result::UNKNOWN_ERROR,
                                      "corrupted database"));
        }
    }
    }

    {
    Statement stmt(this, sqlite, "NOX_SCHEMA_INDEX");
    stmt.get(Query());
    for (Row row = stmt.get_next(); !row.empty(); row = stmt.get_next()) {
        const Table_name table = boost::get<string>(row["NOX_TABLE"]);
        if (persistent_tables.find(table) == persistent_tables.end()){continue;}

        const Index_name index = boost::get<string>(row["NOX_INDEX"]);
        const Column_name column = boost::get<string>(row["NOX_COLUMN"]);
        tables[table].second[index].name = index;
        tables[table].second[index].columns.push_back(column);
    }
    }

    /* Initialize the SQLite trigger callbacks */
    BOOST_FOREACH(Table_definition_map::value_type v, tables) {
        create_trigger_functions(v.first, v.second.first);
    }

    /* Initialize the table structures */
    BOOST_FOREACH(Table_definition_map::value_type v, tables) {
        table_triggers[v.first] = Trigger_def_list();
        sticky_table_triggers[v.first] = Trigger_def_list();

        BOOST_FOREACH(Index_map::value_type i, v.second.second) {
            row_triggers[v.first][i.first] = hash_map<GUID, Trigger_def_list>();
        }
    }

    } catch (const boost::bad_get& e) {
        throw SQLite_error(Result(Result::UNKNOWN_ERROR,
                                  "corrupted database schema"));
    }
}

SQLite_impl::~SQLite_impl() {
    ::sqlite3_close(sqlite);
}

static void trigger_callback(sqlite3_context* ctxt, int n,
                             sqlite3_value** params) {
    assert(n > 2);

    SQLite_impl* impl = static_cast<SQLite_impl*>(sqlite3_user_data(ctxt));
    const int64_t operation = ::sqlite3_value_int64(params[0]);
    const Table_name table((char*)(::sqlite3_value_text(params[1])));

    params += 2;
    n -= 2;

    switch (operation) {
    case SQL_INSERT:
        return impl->insert_callback(table, ctxt, n, params);

    case SQL_UPDATE:
        return impl->update_callback(table, ctxt, n, params);

    case SQL_DELETE:
        return impl->delete_callback(table, ctxt, n, params);

    default:
        assert(0);
    }
}

struct Column_value_visitor
    : public boost::static_visitor<>
{
    Column_value_visitor(const Column_name& n_, sqlite3_value* s_) :
        n(n_), s(s_) { }

    void operator()(const int64_t&) const {
        v = (int64_t)::sqlite3_value_int64(s);
    }

    void operator()(const string&) const {
        v = string((const char*)::sqlite3_value_text(s));
    }

    void operator()(const double&) const {
        v = ::sqlite3_value_double(s);
    }

    void operator()(const GUID&) const {
        v = GUID((int64_t)::sqlite3_value_int64(s));
    }

    mutable Column_name n;
    mutable sqlite3_value* s;
    mutable Column_value v;
};

static bool is_trigger_match(const Column_value_map& trigger_row,
                             const Column_value_map& row) {
    BOOST_FOREACH(Column_value_map::value_type cv, trigger_row) {
        if (row.find(cv.first) == row.end() ||
            *row.find(cv.first) != cv) {
            return false;
        }
    }

    return true;
}

void SQLite_impl::process_trigger(const Table_name& table,
                                  const Column_value_map& row,
                                  const Trigger_reason reason) {
    assert(tables.find(table) != tables.end());

    // For all indices in a table, compute the secondary GUID and
    // gather the matching trigger(s) if there's any.
    BOOST_FOREACH(Index_map::value_type v, tables[table].second) {
        const Index_name index = v.first;
        const GUID sguid = compute_sguid(v.second.columns, row);
        if (row_triggers[table][index].find(sguid) ==
            row_triggers[table][index].end()){
            lg.dbg("No matching sguid found for '%s': %s", index.c_str(),
                   sguid.str().c_str());
            continue;
        }

        lg.dbg("Matching sguid found for '%s'", index.c_str());

        Trigger_def_list left;
        BOOST_FOREACH(Trigger_def tdef, row_triggers[table][index][sguid]){
            Trigger_id tid = tdef.get<0>();
            Row r = tdef.get<1>();
            Trigger_function tfunc = tdef.get<2>();

            if (!is_trigger_match(r, row)) {
                left.push_back(tdef);
                lg.dbg("No matching row found for '%s'", index.c_str());
            } else {
                lg.dbg("Matching row found for '%s'", index.c_str());
                invoked_triggers.push_back(boost::bind(tfunc, tid,row,reason));
                //rollback_log.push_back
                //    (boost::bind(&SQLite_impl::internal_put_trigger, this,
                //                 tid, r, false, tfunc));
            }
        }

        if (left.empty()) {
            row_triggers[table][index].erase(sguid);
        } else {
            row_triggers[table][index][sguid] = left;
        }
    }

    BOOST_FOREACH(Trigger_def tdef, table_triggers[table]) {
        Trigger_id tid = tdef.get<0>();
        Row r = tdef.get<1>();
        Trigger_function tfunc = tdef.get<2>();
        invoked_triggers.push_back(boost::bind(tfunc, tid, row, reason));

        //rollback_log.push_back
        //    (boost::bind(&SQLite_impl::internal_put_trigger, this,
        //                 tid, r, false, tfunc));

    }
    table_triggers[table] = Trigger_def_list();

    BOOST_FOREACH(Trigger_def tdef, sticky_table_triggers[table]) {
        Trigger_id tid = tdef.get<0>();
        Row r = tdef.get<1>();
        Trigger_function tfunc = tdef.get<2>();
        invoked_triggers.push_back(boost::bind(tfunc, tid, row, reason));
    }
}

// XXX: collapse the following functions into one, if the current
// trigger semantics are OK

void
SQLite_impl::insert_callback(const Table_name& table,
                             sqlite3_context* ctxt, int n,
                             sqlite3_value** params) {
    lg.dbg("SQLite INSERT callback>");

    int i = 0;
    Row row;

    BOOST_FOREACH(Column_definition_map::value_type v, tables[table].first) {
        Column_value_visitor t(v.first, params[i]);
        boost::apply_visitor(t, v.second);
        row[v.first] = t.v;

        ++i;
    }

    process_trigger(table, row, INSERT);
}

void
SQLite_impl::update_callback(const Table_name& table,
                             sqlite3_context* ctxt, int n,
                             sqlite3_value** params) {
    lg.dbg("SQLite UPDATE callback>");

    Row new_row;
    Row old_row;
    int i = 0;

    BOOST_FOREACH(Column_definition_map::value_type v, tables[table].first) {
        Column_value_visitor t1(v.first, params[i + 0]);
        boost::apply_visitor(t1, v.second);
        new_row[v.first] = t1.v;

        Column_value_visitor t2(v.first, params[i + n/2]);
        boost::apply_visitor(t2, v.second);
        old_row[v.first] = t2.v;

        ++i;
    }

    process_trigger(table, old_row, MODIFY);
}

void
SQLite_impl::delete_callback(const Table_name& table,
                             sqlite3_context* ctxt, int n,
                             sqlite3_value** params) {
    lg.dbg("SQLite DELETE callback>");

    Row old_row;
    int i = 0;

    BOOST_FOREACH(Column_definition_map::value_type v, tables[table].first) {
        Column_value_visitor t(v.first, params[i + 0]);
        boost::apply_visitor(t, v.second);
        old_row[v.first] = t.v;

        ++i;
    }

    process_trigger(table, old_row, REMOVE);
}

static void callback(SQLite_storage* storage, 
                     const SQLite_impl::Callback_list& callbacks) {
    BOOST_FOREACH(SQLite_impl::Callback cb, callbacks) { storage->post(cb); }
}

Result_callback
SQLite_impl::gather_callbacks(const boost::function<void()>& cb) {
    invoked_triggers.push_back(cb);
    Result_callback result = 
        boost::bind(&callback, storage, invoked_triggers);
    invoked_triggers.clear();
    return result;
}

void
SQLite_impl::auto_begin(const Async_transactional_connection::
                        Transaction_mode& m) {
    if (m == Async_transactional_connection::AUTO_COMMIT) {
        internal_begin();
    }
}

void
SQLite_impl::auto_commit(const Async_transactional_connection::
                         Transaction_mode& m) {
    if (m == Async_transactional_connection::AUTO_COMMIT) {
        internal_commit();
    }
}

void
SQLite_impl::auto_rollback(const Async_transactional_connection::
                           Transaction_mode& m){
    if (m == Async_transactional_connection::AUTO_COMMIT) {
        internal_rollback();
    }
}

void
SQLite_impl::internal_begin() {
    SQLITE3_EXEC("BEGIN");
}

Result_callback
SQLite_impl::begin(const Async_transactional_connection::Begin_callback& cb) {
    try {
        internal_begin();
    }
    catch (const SQLite_error& e) {
        lg.err("BEGIN error: %s", e.what());
        // XXX
    }


    return boost::bind(cb, Result());
}

void
SQLite_impl::internal_commit() {
    SQLITE3_EXEC("COMMIT");

    rollback_log.clear();
}

Result_callback
SQLite_impl::commit(const Async_transactional_connection::Commit_callback& cb) {
    try {
        internal_commit();

        return boost::bind(cb, Result());
    } catch (const SQLite_error& e) {
        lg.err("COMMIT error: %s", e.what());
        // XXX: what's the state we leave the database into

        return boost::bind(cb, e.get_result());
    }
}

void
SQLite_impl::internal_rollback() {
    try {
        SQLITE3_EXEC("ROLLBACK");
    }
    catch (const SQLite_error& e) {
        lg.err("ROLLBACK error: %s", e.what());
        // XXX
    }

    BOOST_FOREACH(boost::function<void()> f, rollback_log) {
        f();
    }

    rollback_log.clear();
}

Result_callback
SQLite_impl::rollback(const Async_transactional_connection::Rollback_callback& cb) {
    internal_rollback();

    return boost::bind(cb, Result());
}

Index
SQLite_impl::identify_index(const Table_name& table, const Query& q) const {
    Table_definition_map::const_iterator t = tables.find(table);
    if (t == tables.end()) {
        throw SQLite_error(Result(Result::NONEXISTING_TABLE,
                                  "Table '" + table + "' not found"));
    }

    const Index_map& indices = t->second.second;

    BOOST_FOREACH(Index_map::value_type v, indices) {
        lg.dbg("Comparing with index '%s'", v.first.c_str());
        if (v.second == q) { return v.second; }
    }

    throw SQLite_error(Result(Result::INVALID_ROW_OR_QUERY,
                              "cannot find the index"));
}

void
SQLite_impl::store_table_definition(const Table_name& table,
                                    const Table_definition& tdef) {
    tables[table] = tdef;
}

void
SQLite_impl::remove_table_definition(const Table_name& table) {
    tables.erase(table);
}

void
SQLite_impl::create_trigger_functions(const Table_name& table,
                                      const Column_value_map& cv) {
    // Insert the insert/modify/delete triggers to the database
    // for the table.
    string old_table_columns;
    string new_table_columns;
    BOOST_FOREACH(Column_definition_map::value_type c, cv) {
        new_table_columns += new_table_columns.size() == 0 ?
            "NEW." + c.first : ", NEW." + c.first;
        old_table_columns += old_table_columns.size() == 0 ?
            "OLD." + c.first : ", OLD." + c.first;
    }

    const string trigger_name("TRIGGER_FOR_" + table);
    const int columns = cv.size();

    SQLite_function func = &trigger_callback;
    if (::sqlite3_create_function(sqlite,("INSERT_CALLBACK_"+table).c_str(),
                                  2 + columns, SQLITE_UTF8, this, func,0,0) ||
        ::sqlite3_create_function(sqlite, ("UPDATE_CALLBACK_" + table).c_str(),
                                  2 + columns * 2,SQLITE_UTF8,this,func,0,0) ||
        ::sqlite3_create_function(sqlite, ("DELETE_CALLBACK_" + table).c_str(),
                                  2 + columns, SQLITE_UTF8, this, func, 0, 0)) {
        throw SQLite_error(sqlite);
    }

    SQLITE3_EXEC("CREATE TEMP TRIGGER " + trigger_name + "_INSERT" +
                 " AFTER INSERT ON " + table +
                 " BEGIN " +
                 "SELECT INSERT_CALLBACK_" + table +
                 "(" + boost::lexical_cast<string>(SQL_INSERT) + ", '" +
                 table + "', " + new_table_columns + "); " +
                 "END;");
    SQLITE3_EXEC("CREATE TEMP TRIGGER " + trigger_name + "_UPDATE" +
                 " AFTER UPDATE ON " + table +
                 " BEGIN " +
                 "SELECT UPDATE_CALLBACK_" + table +
                 "(" +boost::lexical_cast<string>(SQL_UPDATE)+", '"+table+"', "+
                 new_table_columns + ", " + old_table_columns + "); " +
                 "END;");
    SQLITE3_EXEC("CREATE TEMP TRIGGER " + trigger_name + "_DELETE" +
                 " AFTER DELETE ON " + table +
                 " BEGIN "  +
                 "SELECT DELETE_CALLBACK_" + table +
                 "(" +boost::lexical_cast<string>(SQL_DELETE)+", '"+table+"', "+
                 old_table_columns + "); " +
                 "END;");
}

Index_list
SQLite_impl::to_list(const SQLite_impl::Index_map& m) {
    Index_list l;
    BOOST_FOREACH(Index_map::value_type v, m) { l.push_back(v.second); }
    return l;
}

Result_callback
SQLite_impl::create_table(const Async_transactional_connection::
                          Transaction_mode& mode,
                          const Table_name& table,
                          const Column_definition_map& cv_,
                          const Index_list& indices_,
                          const int version,
                          const Async_transactional_connection::
                          Create_table_callback& cb) {
    // Every table must have a primary key column
    Column_definition_map cv = cv_;
    cv["GUID"] = GUID();

    // ... and a corresponding index
    Index_list indices = indices_;
    Index primary_guid_index;
    primary_guid_index.name = "PRIMARY_GUID_INDEX";
    primary_guid_index.columns.push_back("GUID");
    indices.push_back(primary_guid_index);

    // Index names should have table name as a prefix
    BOOST_FOREACH(Index_list::value_type& i, indices) {
        i.name = table + "_" + i.name;
    }

    try {
        lg.dbg("CREATE TABLE");
        auto_begin(mode);

        if (tables.find(table) != tables.end()) {
            if (is_equal(cv, indices,
                         tables[table].first, to_list(tables[table].second))) {
                lg.dbg("No need to create a table: %s", table.c_str());

                auto_commit(mode);
                return gather_callbacks(boost::bind(cb, Result()));

            } else {
                throw SQLite_error(Result(Result::EXISTING_TABLE,
                                          "Table already exists with a "
                                          "different schema."));
            }
        }

        Row r1;
        r1["NOX_TABLE"] = table;
        r1["NOX_TYPE"] = (int64_t)PERSISTENT;
        r1["NOX_VERSION"] = (int64_t)version;

        Statement(this, sqlite, "NOX_SCHEMA_META").put(r1);

        // Store the table and indices to the meta tables and create
        // the actual table, and its indices
        string query;
        BOOST_FOREACH(Column_definition_map::value_type v, cv) {
            Column_name n = v.first;
            Column_type_collector t;
            boost::apply_visitor(t, v.second);

            if (n == "GUID") {
                query += (query == "" ? n : ", " + n) + " " +
                    "INTEGER PRIMARY KEY";
            } else {
                query += (query == "" ? n : ", " + n) + " " + t.sql_type;
            }

            Row r;
            r["NOX_TABLE"] = table;
            r["NOX_COLUMN"] = n;
            r["NOX_TYPE"] = t.type;

            Statement(this, sqlite, "NOX_SCHEMA_TABLE").put(r);
        }

        SQLITE3_EXEC("CREATE TABLE " + table +"("+query+")");

        Index_map m;
        BOOST_FOREACH(Index_list::value_type v, indices) {
            Index i = v;

            SQLITE3_EXEC("CREATE INDEX " + i.name + " ON " + table + "("+
                         boost::algorithm::join(i.columns, ",")+")");

            BOOST_FOREACH(Column_list::value_type c, i.columns) {
                Row r;
                r["NOX_TABLE"] = table;
                r["NOX_INDEX"] = i.name;
                r["NOX_COLUMN"] = c;
                Statement(this, sqlite, "NOX_SCHEMA_INDEX").put(r);
            }

            m[i.name] = i;
        }

        create_trigger_functions(table, cv);

        // Update the meta data tables and store the updates to the
        // memory structures to the rollback log
        store_table_definition(table, Table_definition(cv, m));
        rollback_log.push_back
            (boost::bind(&SQLite_impl::remove_table_definition, this, table));

        auto_commit(mode);

        return gather_callbacks(boost::bind(cb, Result()));
    }
    catch (const SQLite_error& e) {
        auto_rollback(mode);

        return gather_callbacks(boost::bind(cb, e.get_result()));
    }
}

Result_callback
SQLite_impl::drop_table(const Async_transactional_connection::
                        Transaction_mode& mode, const Table_name& table,
                        const Async_transactional_connection::
                        Drop_table_callback& cb) {
    try {
        auto_begin(mode);

        if (tables.find(table) == tables.end()) {
            throw SQLite_error(Result(Result::NONEXISTING_TABLE, table +
                                      " does not exist."));
        }

        // Drop the table in the persistent storage, as well as remove
        // the meta table entries.
        SQLITE3_EXEC("DROP TABLE " + table);

        Row r;
        r["NOX_TABLE"] = table;

        Statement(this, sqlite, "NOX_SCHEMA_META").remove(r);
        Statement(this, sqlite, "NOX_SCHEMA_TABLE").remove(r);
        Statement(this, sqlite, "NOX_SCHEMA_INDEX").remove(r);

        rollback_log.push_back
            (boost::bind(&SQLite_impl::store_table_definition, this,
                         table, tables.find(table)->second));
        remove_table_definition(table);

        auto_commit(mode);

        return gather_callbacks(boost::bind(cb, Result()));
    }
    catch (const SQLite_error& e) {
        auto_rollback(mode);

        return gather_callbacks(boost::bind(cb, e.get_result()));
    }
}

boost::tuple<Trigger_function, Row, bool>
SQLite_impl::internal_remove_trigger(const Trigger_id& tid) {

    if (tid.for_table) {
        for (Trigger_def_list::iterator i = table_triggers[tid.ring].begin();
             i != table_triggers[tid.ring].end(); ++i) {
            Trigger_id t = i->get<0>();
            if (t == tid) {
                table_triggers[tid.ring].erase(i);
                return boost::tuple<Trigger_function, Row, bool>();
            }
        }

        for (Trigger_def_list::iterator i =
                 sticky_table_triggers[tid.ring].begin();
             i != sticky_table_triggers[tid.ring].end(); ++i) {
            Trigger_id t = i->get<0>();
            if (t == tid) {
                sticky_table_triggers[tid.ring].erase(i);
                return boost::tuple<Trigger_function, Row, bool>();
            }
        }
    } else {
        for (Index_trigger_map::iterator k = row_triggers[tid.ring].begin();
             k != row_triggers[tid.ring].end(); ++k) {
            for (GUID_trigger_map::iterator j = k->second.begin();
                 j != k->second.end(); ++j) {
                for (Trigger_def_list::iterator i = j->second.begin();
                     i != j->second.end(); ++i) {
                    Trigger_id t = i->get<0>();
                    if (t == tid) {
                        j->second.erase(i);
                        if (j->second.empty()) {
                            k->second.erase(j);
                        }

                        return boost::tuple<Trigger_function, Row, bool>();
                    }
                }
            }
        }
    }

    return boost::tuple<Trigger_function, Row, bool>();
}

void
SQLite_impl::internal_put_trigger(const Trigger_id& tid, const Row& row,
                                  bool sticky, const Trigger_function& tfunc) {
    if (tid.for_table) {
        if (sticky) {
            sticky_table_triggers[tid.ring].push_back
                (Trigger_def(tid, row, tfunc));
        } else {
            table_triggers[tid.ring].push_back(Trigger_def(tid, row, tfunc));
        }
    } else {
        Index i = identify_index(tid.ring, row);

        const GUID sguid = compute_sguid(i.columns, row);
        row_triggers[tid.ring][i.name][sguid].push_back
            (boost::tuple<Trigger_id, Row, Trigger_function>(tid, row, tfunc));
        lg.dbg("Inserted a row trigger for index '%s', sguid %s",i.name.c_str(),
               sguid.str().c_str());

    }
}

Result_callback
SQLite_impl::put_trigger_1(const Async_transactional_connection::
                           Transaction_mode& mode, const Table_name& table,
                           const Row& row, const Trigger_function& tfunc,
                           const Async_transactional_connection::
                           Put_trigger_callback& cb) {
    try {
        auto_begin(mode);

        Trigger_id tid(table, Reference(), ++next_tid);
        internal_put_trigger(tid, row, false, tfunc);
        rollback_log.push_back
            (boost::bind(&SQLite_impl::internal_remove_trigger, this, tid));
        auto_commit(mode);

        return boost::bind(cb, Result(), tid);
    } catch (const SQLite_error& e) {
        auto_rollback(mode);
        return boost::bind(cb, e.get_result(), Trigger_id());
    }
}

Result_callback
SQLite_impl::put_trigger_2(const Async_transactional_connection::
                           Transaction_mode& mode, const Table_name& table,
                           const bool sticky, const Trigger_function& tfunc,
                           const Async_transactional_connection::
                           Put_trigger_callback& cb) {
    try {
        auto_begin(mode);

        Trigger_id tid(table, ++next_tid);
        internal_put_trigger(tid, Row(), sticky, tfunc);
        rollback_log.push_back
            (boost::bind(&SQLite_impl::internal_remove_trigger, this, tid));

        auto_commit(mode);
        return boost::bind(cb, Result(), tid);
    } catch (const SQLite_error& e) {
        auto_rollback(mode);
        return boost::bind(cb, e.get_result(), Trigger_id());
    }
}

Result_callback
SQLite_impl::remove_trigger(const Async_transactional_connection::
                            Transaction_mode& mode, const Trigger_id& tid,
                            const Async_transactional_connection::
                            Remove_trigger_callback& cb) {
    try {
        auto_begin(mode);

        boost::tuple<Trigger_function, Row, bool> tf =
            internal_remove_trigger(tid);
        rollback_log.push_back
            (boost::bind(&SQLite_impl::internal_put_trigger, this, tid,
                         tf.get<1>(), tf.get<2>(), tf.get<0>()));

        auto_commit(mode);
        return boost::bind(cb, Result());
    } catch (const SQLite_error& e) {
        auto_rollback(mode);
        return boost::bind(cb, e.get_result());
    }
}

Result_callback
SQLite_impl::get(const Table_name& table, const Query& query,
                 const SQLite_impl::Get_callback& cb) {
    Statement* s = 0;
    try {
        if (!query.empty()) { identify_index(table, query); }

        s = new Statement(this, sqlite, table);
        s->get(query);
        return boost::bind(cb, Result(), s);
    }
    catch (const SQLite_error& e) {
        if (s) { delete s; }
        return boost::bind(cb, e.get_result(), (Statement*)0);
    }
}

Result_callback
SQLite_impl::get_next(Statement* stmt,
                      const Async_transactional_cursor::Get_next_callback& cb) {
    try {
        Row row = stmt->get_next();
        return boost::bind(cb,
                           Result(row.empty() ?
                                  Result::NO_MORE_ROWS : Result::SUCCESS), row);
    }
    catch (const SQLite_error& e) {
        return boost::bind(cb, e.get_result(), Row());
    }
}

Result_callback
SQLite_impl::close(Statement* stmt,
                   const Async_transactional_cursor::Close_callback& cb) {
    delete stmt;

    return boost::bind(cb, Result());
}

class type_checker
    : public boost::static_visitor<bool> {
public:
    template <typename T, typename U>
    bool operator()(const T&, const U&) const { return false; }

    template <typename T>
    bool operator()(const T&, const T&) const { return true; }
};

void
SQLite_impl::validate_column_types(const Table_name& table,
                                   const Column_value_map& c) const {
    Table_definition_map::const_iterator t = tables.find(table);
    if (t == tables.end()) {
        throw SQLite_error(Result(Result::NONEXISTING_TABLE,
                                  table + " table doesn't exist"));
    }

    const Table_definition& tdef = t->second;
    const Column_definition_map& cdef = tdef.first;

    BOOST_FOREACH(Column_value_map::value_type t, c) {
        const Column_name& cn = t.first;
        const Column_value cv = t.second;
        Column_definition_map::const_iterator j = cdef.find(cn);
        if (j == cdef.end() ||
            !boost::apply_visitor(type_checker(), cv, j->second)) {
            throw SQLite_error(Result(Result::INVALID_ROW_OR_QUERY,
                                      cn + " column doesn't exist "
                                      "or has invalid type"));
        }
    }
}

Result_callback
SQLite_impl::put(const Async_transactional_connection::Transaction_mode& mode,
                 const Table_name& table, const Row& row_,
                 const Async_transactional_connection::Put_callback& cb) {
    try {
        Row row = row_;
        auto_begin(mode);

        validate_column_types(table, row);

        // For any missing columns, insert their default values
        Table_definition_map::const_iterator t = tables.find(table);
        const Table_definition& tdef = t->second;
        const Column_definition_map& cdef = tdef.first;

        BOOST_FOREACH(Column_value_map::value_type t, cdef) {
            const Column_name& cn = t.first;
            const Column_value cv = t.second;
            Column_definition_map::const_iterator j = row.find(cn);
            if (j == row.end() && cn != "GUID") {
                Column_type_collector t;
                boost::apply_visitor(t, cv);
                row[cn] = t.storage_type;
            }
        }

        GUID guid = Statement(this, sqlite, table).put(row);

        auto_commit(mode);
        return gather_callbacks(boost::bind(cb, Result(), guid));
    }
    catch (const SQLite_error& e) {
        auto_rollback(mode);

        // Regardless of the error, gather the callbacks to invoke.
        return gather_callbacks(boost::bind(cb, e.get_result(), GUID()));
    }
}

Result_callback
SQLite_impl::modify(const Async_transactional_connection::
                    Transaction_mode& mode,
                    const Table_name& table, const Row& row,
                    const Async_transactional_connection::Modify_callback& cb) {
    try {
        auto_begin(mode);

        validate_column_types(table, row);
        Statement(this, sqlite, table).modify(row);
        auto_commit(mode);
        return gather_callbacks(boost::bind(cb, Result()));
    }
    catch (const SQLite_error& e) {
        auto_rollback(mode);

        // Regardless of the error, gather the callbacks to invoke.
        return gather_callbacks(boost::bind(cb, e.get_result()));
    }
}

Result_callback
SQLite_impl::remove(const Async_transactional_connection::
                    Transaction_mode& mode,
                    const Table_name& table, const Row& row,
                    const Async_transactional_connection::Remove_callback& cb) {
    try {
        auto_begin(mode);

        validate_column_types(table, row);
        Statement(this, sqlite, table).remove(row);

        auto_commit(mode);

        return gather_callbacks(boost::bind(cb, Result()));
    }
    catch (const SQLite_error& e) {
        auto_rollback(mode);

        // Regardless of the error, gather the callbacks to invoke.
        return gather_callbacks(boost::bind(cb, e.get_result()));
    }
}

Lock_id::Lock_id()
    : id(NO_LOCK_ID)
#ifndef NDEBUG
    , s(0)
#else
#ifdef PROFILING
    , s(0)
#endif
#endif
{
}

#define TRACE_LOCK(MGR)                                            \
    s = MGR->is_lock_trace_enabled();                              \
    if (s) {                                                       \
        string trace = dump_backtrace();                           \
        timer = s->post(boost::bind(&Lock_id::timeout, trace),     \
                        make_timeval(30, 0));                      \
    }

Lock_id::Lock_id(const Lock_manager* mgr, const int id_)
    : id(id_) {
#ifndef NDEBUG
    TRACE_LOCK(mgr);
#else
#ifdef PROFILING
    TRACE_LOCK(mgr);
#endif
#endif
}

void
Lock_id::release() const {
#ifndef NDEBUG
    if (s) {
        timer.cancel();
    }
#else
#ifdef PROFILING
    if (s) {
        timer.cancel();
    }
#endif
#endif
}

bool
Lock_id::operator==(const Lock_id& other) const {
    return id == other.id;
}

void
Lock_id::timeout(const string& trace) {
    lg.err("Lock not released: %s\n", trace.c_str());
}

const int Lock_id::NO_LOCK_ID = 0;

Lock_manager::Lock_manager(SQLite_storage* storage_)
    : next_lock_id(Lock_id::NO_LOCK_ID), storage(storage_) {

}

Lock_id
Lock_manager::get_next_lock_id() const {
    ++next_lock_id;

    /* If wrapped, don't assign the special no-lock id */
    if (next_lock_id == Lock_id::NO_LOCK_ID) {
        ++next_lock_id;
    }

    return Lock_id(this, next_lock_id);
}

void
Lock_manager::get_shared(const Lock_id& id,
                         const Lock_manager::Callback& cb) const {
    // If already locked (shared or exclusive), nothing to do.
    if (shared.count(id) > 0 || exclusive.count(id) > 0) {
        if (shared.count(id) > 0) {
            lg.dbg("Already have shared lock for %d in get_shared.", id.id);
        }
        else {
            lg.dbg("Already have exclusive lock for %d in get_shared.", id.id);
        }
        storage->post(boost::bind(cb, id));
        return;
    }

    assert(id == NO_LOCK);

    Lock_id new_lock_id = get_next_lock_id();
    lg.dbg("Getting shared for id:%d, s:%zu e:%zu", new_lock_id.id, shared.count(new_lock_id), exclusive.count(new_lock_id));

    // If exclusive lock acquired or pending, wait ...
    if (!exclusive.empty() || !pending_exclusive.empty()) {
        lg.dbg("Waiting for a shared lock (%d): exclusive access in progress "
               "or pending.", new_lock_id.id);
        pending_shared.push_back(make_pair(new_lock_id, cb));
        return;
    }

    // Lock acquired
    shared.insert(new_lock_id);

    lg.dbg("Shared lock acquired %d.", new_lock_id.id);

    storage->post(boost::bind(cb, new_lock_id));
}

void
Lock_manager::get_exclusive(const Lock_id& id,
                            const Lock_manager::Callback& cb) const {
    // If already exclusive locked, nothing to do.
    if (exclusive.count(id)) {
        lg.dbg("Already have exclusive lock for %d in get_exclusive.", id.id);
        storage->post(boost::bind(cb, id));
        return;
    }

    Lock_id new_lock_id;
    if (id == NO_LOCK) {
        new_lock_id = get_next_lock_id();
    } else {
        assert(shared.count(id));
        new_lock_id = id;
    }

    lg.dbg("Getting exclusive for id:%d, s:%zu e:%zu", new_lock_id.id, shared.count(new_lock_id), exclusive.count(new_lock_id));

    // If a lock acquired or pending, wait ...
    if (shared.size() > 1 || !exclusive.empty() || !pending_exclusive.empty()) {
        lg.dbg("Waiting for an exclusive lock(%d); either multiple shared "
               "locks, or exclusive access in progress/pending.",
               new_lock_id.id);
        pending_exclusive.push_back(make_pair(new_lock_id, cb));
        return;
    }

    // If not the only shared lock, upgrade not allowed
    if (!shared.empty() && shared.count(new_lock_id) == 0) {
        lg.dbg("Waiting for an exclusive lock (%d); a shared lock already "
               "acquired.", new_lock_id.id);
        Lock_set::iterator it = shared.begin();
        for(; it != shared.end(); ++it)
          lg.dbg("current lock holder: %d \n", it->id);

        pending_exclusive.push_back(make_pair(new_lock_id, cb));
        return;
    }

    // Remove shared lock, just in case, if this was a lock upgrade.
    shared.erase(new_lock_id);
    exclusive.insert(new_lock_id);

    lg.dbg("Exclusive lock acquired %d.", new_lock_id.id);
    storage->post(boost::bind(cb, new_lock_id));
}

Lock_id
Lock_manager::release(const Lock_id& id) const {
    assert(!(id == NO_LOCK));

    lg.dbg("Releasing lock id:%d, s:%zu e:%zu",
           id.id, shared.count(id), exclusive.count(id));
    shared.erase(id);
    exclusive.erase(id);
    id.release();

    // Prefer pending exclusive lock acquires
    if (shared.empty() && exclusive.empty() && !pending_exclusive.empty()) {
        pair<Lock_id, Callback>& s = pending_exclusive.front();
        exclusive.insert(s.first);
        storage->post(boost::bind(s.second, s.first));
        lg.dbg("... and acquired exclusive %d", s.first.id);
        pending_exclusive.pop_front();
        return NO_LOCK;
    }

    // Only if there's no exclusive lock acquires pending, acquire
    // shared locks
    while (exclusive.empty() && pending_exclusive.empty() &&
           !pending_shared.empty()) {
        pair<Lock_id, Callback>& s = pending_shared.front();
        shared.insert(s.first);
        storage->post(boost::bind(s.second, s.first));
        lg.dbg("... and acquired shared %d", s.first.id);
        pending_shared.pop_front();
    }

    return NO_LOCK;
}

SQLite_storage*
Lock_manager::is_lock_trace_enabled() const {
    return storage->trace_locks ? storage : 0;
}

const Lock_id Lock_manager::NO_LOCK = Lock_id();

SQLite_storage::SQLite_storage(const container::Context* c,
                               const json_object*)
    : Component(c), lockmgr(this), trace_locks(false) {

}

void
SQLite_storage::configure(const container::Configuration* conf) {
    database = "testing.sqlite"; // XXX: deprecate this

    container::Component_argument_list args = conf->get_arguments();
    if (args.empty()) {
        lg.warn("Transactional storage file not given in the command line; "
                "defaulting to '%s'", database.c_str());
    } else {
        database = args.front(); args.pop_front();

        if (!args.empty()) {
            trace_locks = args.front() == "trace_locks";
        }

        // XXX: support IP:port tuple here for remote connectivity
    }

    pool.add_worker(new SQLite_impl(this, database.c_str()), 0);
}

void
SQLite_storage::install() {

}

void
SQLite_storage::get_connection(const Get_connection_callback& cb) const {
    boost::shared_ptr<SQLite_connection>
        conn(new SQLite_connection(const_cast<SQLite_storage*>(this)));
    conn->weak_this = conn;
    post(boost::bind(cb, Result(), Async_transactional_connection_ptr(conn)));
}

std::string
SQLite_storage::get_location() const {
    return database;
}


SQLite_connection::SQLite_connection(SQLite_storage* s)
    : storage(s), lock_id(Lock_manager::NO_LOCK), 
      mode(AUTO_COMMIT), next_cursor_id(0) {

}

SQLite_connection::~SQLite_connection() {

}

const Async_transactional_connection::Transaction_mode
SQLite_connection::get_transaction_mode() {
    return mode;
}

void
SQLite_connection::lock_acquired(const Lock_id lock_id,
                                 const boost::function<void()>& next_step) {
    this->lock_id = lock_id;

    next_step();

    assert(this->lock_id == lock_id);
}

static void cursor_open_error(const Result& r,
                              const Async_transactional_connection::
                              Get_callback& cb) {
    cb(r, Async_transactional_cursor_ptr());
}

void
SQLite_connection::allocate_cursor(const Result& r, Statement* s,
                                   const Async_transactional_connection::
                                   Transaction_mode& mode,
                                   boost::shared_ptr<SQLite_cursor> cursor,
                                   const Async_transactional_connection::
                                   Get_callback& cb) {
    if (r.is_success()) {
        ((SQLite_cursor*)cursor.get())->stmt = s;
        cb(r, cursor);
    } else {
        const Result_callback rcb = boost::bind(&cursor_open_error, r, cb);
        cursor_closed(cursor, mode, rcb);

    }
}

void
SQLite_connection::store_cursor(Async_transactional_cursor_ptr cursor,
                                const boost::function<void()>& cb) {
    cursors_open[((SQLite_cursor*)cursor.get())->cursor_id] = cursor;

    cb();
}

static void basic_callback(const Result_callback& cb,
                           const boost::shared_ptr<SQLite_connection>&) {
    cb();
}

void
SQLite_connection::get(const Table_name& table, const Query& query,
                       const Async_transactional_connection::Get_callback& cb) {
    // Steps: 1) acquire lock, 2) store the cursor reference
    // count, 3) execute get() in a native thread, 4) allocate a
    // cursor object.
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    boost::shared_ptr<SQLite_cursor> cursor
        (new SQLite_cursor(this_, 0, ++next_cursor_id, mode));
    cursor->weak_this = cursor;

    SQLite_impl::Get_callback step4 =
        boost::bind(&SQLite_connection::allocate_cursor, this_,
                    _1, _2, mode, cursor, cb);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::get, _1, table, query, step4);
    boost::function<void(Result_callback)> f2 =
        boost::bind(&basic_callback, _1, this_);
    boost::function<void()> step3 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, f2);
    boost::function<void()> step2 =
        boost::bind(&SQLite_connection::store_cursor, this_, cursor, step3);
    storage->lockmgr.get_shared
        (lock_id, boost::bind(&SQLite_connection::lock_acquired, this_, _1,
                              step2));
}

SQLite_cursor::SQLite_cursor(boost::shared_ptr<SQLite_connection> impl_,
                             Statement* stmt_,
                             const Cursor_id cursor_id_,
                             const Async_transactional_connection::
                             Transaction_mode mode_)
    : impl(impl_), stmt(stmt_), cursor_id(cursor_id_), mode(mode_) {
}

SQLite_cursor::~SQLite_cursor() {

}

static void basic_callback_2(const Result_callback& cb,
                             const boost::shared_ptr<SQLite_cursor>&) {
    cb();
}

void
SQLite_cursor::get_next(const Get_next_callback& cb) {
    if (!stmt) {
        impl->storage->post(boost::bind(cb, Result(Result::UNKNOWN_ERROR,
                                                   "Cursor closed."), Row()));
        return;
    }

    boost::shared_ptr<SQLite_cursor> this_(weak_this);

    // Steps: 1) execute get_next in a native thread, 2) release the
    // lock iff possible.
    impl->storage->
        pool.execute(boost::bind(&SQLite_impl::get_next, _1, stmt, cb),
                     boost::bind(&basic_callback_2, _1, this_));
}

void
SQLite_cursor::close(const Async_transactional_cursor::Close_callback& cb) {
    if (!stmt) {
        impl->storage->post(boost::bind(cb, Result(Result::UNKNOWN_ERROR,
                                                   "Cursor closed.")));
        return;
    }

    lg.dbg("Closing a cursor (%d)", cursor_id);

    // XXX: implement a safety timeout for non-closed cursors

    // Steps: 1) close the SQLite cursor in a native thread, 2)
    // decrease the cursor reference count, 3) release the lock if
    // possible.
    boost::shared_ptr<SQLite_cursor> this_(weak_this);

    Statement* s = stmt;
    stmt = 0;

    boost::function<void(const Result_callback&)> step2 =
        boost::bind(&SQLite_connection::cursor_closed, impl, this_, mode, _1);
    impl->storage->pool.execute(boost::bind(&SQLite_impl::close, _1, s, cb),
                                step2);
}

void
SQLite_connection::cursor_closed(const boost::shared_ptr<SQLite_cursor>& cursor,
                                 const Async_transactional_connection::
                                 Transaction_mode& mode,
                                 const Result_callback& cb) {
    cursors_open.erase(cursor->cursor_id);

    // Step 3...
    release_lock(mode, cb);
}

void
SQLite_connection::put_trigger(const Table_name& table, const Row& row,
                               const Trigger_function& tfunc,
                               const Async_transactional_connection::
                               Put_trigger_callback& cb) {
    // Steps: 1) acquire lock, 2) execute put_trigger() in a native
    // thread, 3) release the lock
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::put_trigger_1, _1, mode, table, row,tfunc,cb);
    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id, boost::bind(&SQLite_connection::lock_acquired, this_, _1,
                              step2));
}

void
SQLite_connection::put_trigger(const Table_name& table,
                               const bool sticky,
                               const Trigger_function& tfunc,
                               const Put_trigger_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    // Steps: 1) acquire lock, 2) execute put_trigger() in a native
    // thread, 3) release the lock
    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::put_trigger_2, _1, mode, table, sticky,
                    tfunc, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id, boost::bind(&SQLite_connection::lock_acquired, this_, _1,
                              step2));
}

void
SQLite_connection::remove_trigger(const Trigger_id& tid,
                                  const Async_transactional_connection::
                                  Remove_trigger_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    // Steps: 1) acquire lock, 2) execute put_trigger() in a native
    // thread, 3) release the lock
    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::remove_trigger, _1, mode, tid, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id, boost::bind(&SQLite_connection::lock_acquired, this_, _1,
                              step2));
}

void
SQLite_connection::create_table(const Table_name& t,
                                const Column_definition_map& c,
                                const Index_list& i,
                                const int version,
                                const Async_transactional_connection::
                                Create_table_callback& cb) {
    // Steps: 1) acquire lock, 2) execute create_table() in a native
    // thread, 3) release the lock
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::create_table, _1, mode, t, c, i, version, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id,
         boost::bind(&SQLite_connection::lock_acquired, this_, _1, step2));
}

void
SQLite_connection::drop_table(const Table_name& t,
                              const Async_transactional_connection::
                              Drop_table_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    // Steps: 1) acquire lock, 2) execute drop_table() in a native
    // thread, 3) release the lock
    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::drop_table, _1, mode, t, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id,
         boost::bind(&SQLite_connection::lock_acquired, this_, _1, step2));
}

void
SQLite_connection::put(const Table_name& table, const Row& row,
                       const Async_transactional_connection::Put_callback& cb) {
    // Steps: 1) acquire lock, 2) execute put() in a native
    // thread, 3) release the lock
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::put, _1, mode, table, row, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id,
         boost::bind(&SQLite_connection::lock_acquired, this_, _1, step2));
}

void
SQLite_connection::modify(const Table_name& t, const Row& row,
                          const Async_transactional_connection::
                          Modify_callback& cb) {
    // Steps: 1) acquire exclusive lock, 2) execute the modification
    // in a native thread, 3) release the lock
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::modify, _1, mode, t, row, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id,
         boost::bind(&SQLite_connection::lock_acquired, this_, _1, step2));
}

void
SQLite_connection::remove(const Table_name& t, const Row& row,
                          const Async_transactional_connection::
                          Remove_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    // Steps: 1) acquire exclusive lock, 2) execute the removal
    // in a native thread, 3) release the lock
    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::remove, _1, mode, t, row, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    storage->lockmgr.get_exclusive
        (lock_id,
         boost::bind(&SQLite_connection::lock_acquired, this_, _1, step2));
}

void
SQLite_connection::release_lock(const Async_transactional_connection::
                                Transaction_mode& m,
                                const Result_callback& cb) {
    if (m == AUTO_COMMIT && cursors_open.empty()) {
        lg.dbg("Releasing lock %d", lock_id.id);
        lock_id = storage->lockmgr.release(lock_id);
    }
    else {
        lg.dbg("Not releasing lock lockid:%d %s", lock_id.id,
                (m != AUTO_COMMIT ? "not in auto commit" : "cursors open"));
    }

    cb();
}

void
SQLite_connection::begin(const Transaction_mode& m,
                         const Async_transactional_connection::
                         Begin_callback& cb) {
    if (mode != AUTO_COMMIT && m != AUTO_COMMIT) {
        storage->post(boost::bind(cb, Result(Result::UNKNOWN_ERROR,
                                             "Auto commit mode already left")));
        return;
    }

    boost::shared_ptr<SQLite_connection> this_(weak_this);

    mode = m;

    switch (mode) {
    case AUTO_COMMIT:
    case DEFERRED:
        {
            // Nothing to do as the lock is acquired on the way
            boost::function<void()> step2a = boost::bind(cb, Result());
            storage->post(step2a);
        }
        return;

    case EXCLUSIVE:
        boost::function<void(const Result_callback&)> step3 =
            boost::bind(&basic_callback, _1, this_);
        SQLite_impl_pool::T f1 =
            boost::bind(&SQLite_impl::begin, _1, cb);
        boost::function<void()> step2b =
            boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);
        storage->lockmgr.
            get_exclusive(Lock_manager::NO_LOCK,
                          boost::bind(&SQLite_connection::lock_acquired, this,
                                      _1, step2b));
        return;
    }
}

void
SQLite_connection::close_cursors(const Result&,
                                 const boost::function<void()>& cb) {
    if (cursors_open.empty()) {
        cb();
    } else {
        //lg.dbg("Cursors open %d", cursors_open.size());
        Cursor_map::iterator i = cursors_open.begin();
        Async_transactional_cursor_ptr cursor = i->second;
        cursors_open.erase(i);
        cursor->close
            (boost::bind(&SQLite_connection::close_cursors, this, _1, cb));
    }
}

void
SQLite_connection::commit(const Async_transactional_connection::
                          Commit_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    if (mode == AUTO_COMMIT) {
        storage->post(boost::bind(cb, Result(Result::UNKNOWN_ERROR, "Connection"
                                             " already in AUTO_COMMIT mode.")));
        return;
    }

    lg.dbg("Commiting and changing back to AUTO_COMMIT.");
    mode = AUTO_COMMIT;

    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::commit, _1, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    close_cursors(Result(), step2);
}

void
SQLite_connection::rollback(const Async_transactional_connection::
                            Rollback_callback& cb) {
    boost::shared_ptr<SQLite_connection> this_(weak_this);

    if (mode == AUTO_COMMIT) {
        storage->post(boost::bind(cb, Result(Result::UNKNOWN_ERROR, "Connection"
                                             " already in AUTO_COMMIT mode.")));
        return;
    }

    lg.dbg("Rollbacking and changing back to AUTO_COMMIT.");
    mode = AUTO_COMMIT;

    boost::function<void(const Result_callback&)> step3 =
        boost::bind(&SQLite_connection::release_lock, this_, mode, _1);
    SQLite_impl_pool::T f1 =
        boost::bind(&SQLite_impl::rollback, _1, cb);
    boost::function<void()> step2 =
        boost::bind(&SQLite_impl_pool::execute, &storage->pool, f1, step3);

    close_cursors(Result(), step2);
}

REGISTER_COMPONENT(container::Simple_component_factory<SQLite_storage>,
                   Async_transactional_storage);
