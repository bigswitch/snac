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
#include "dht-storage.hh"

#include <boost/bind.hpp>
#include <boost/foreach.hpp>
#include <boost/variant/apply_visitor.hpp>
#include <boost/variant/get.hpp>
#include <boost/variant/static_visitor.hpp>

#include "hash_set.hh"
#include "sha1.hh"
#include "transactional-storage-blocking.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::applications::storage;
using namespace vigil::container;

static Vlog_module lg("dht-storage");

/* TODO:
 *
 * 1) The class does not use locking for now, since a) it's not
 *    strictly speaking required in this single-node implementation of
 *    the storage, and b) on NOX, Python is invoked while in a
 *    critical section and therefore (the invoked) Python applications
 *    can't call back to the C++ storage implementation -- as they do
 *    if they use any storage functionality -- if it uses
 *    locking. This should be refactored.
 *
 */

#define RETURN_ERROR(CODE, MESSAGE)                                     \
    do {                                                                \
        post(boost::bind(cb, Result(Result::CODE, #MESSAGE)));          \
        return;                                                         \
    } while (0);

Async_DHT_storage::Async_DHT_storage(const container::Context* c,
                                     const json_object*)
    : Component(c) {

}

Index_list 
Async_DHT_storage::to_list(const Async_DHT_storage::Index_map& m) {
    Index_list l;
    BOOST_FOREACH(Index_map::value_type v, m) { l.push_back(v.second); }
    return l;
}

void
Async_DHT_storage::create_table(const Table_name& table,
                                const Column_definition_map& columns_,
                                const Index_list& indices_,
                                const Create_table_callback& cb) {
    //Co_scoped_mutex l(&mutex);

    Column_definition_map columns = columns_;
    columns["GUID"] = GUID();
    
    // Index names should have table name as a prefix
    Index_list indices = indices_;
    BOOST_FOREACH(Index_list::value_type& i, indices) {
        i.name = table + "_" + i.name;
    }

    if (tables.find(table) != tables.end()) {
        if (is_equal(columns, indices, 
                     tables[table].first, to_list(tables[table].second))) {
            lg.dbg("No need to create a table: %s", table.c_str());
            post(boost::bind(cb, Result()));
        } else {
            post(boost::bind(cb, Result(Result::EXISTING_TABLE, 
                                        "Table already exists with a different "
                                        "schema.")));
        }

        return;
    }

    lg.dbg("Creating a table: %s", table.c_str());

    /* Check for duplicate index entries */
    hash_set<Index_name> dupecheck;
    BOOST_FOREACH(Index_list::value_type i,indices) { dupecheck.insert(i.name);}
    if (dupecheck.size() != indices.size()) {
        post(boost::bind(cb, Result(Result::INVALID_ROW_OR_QUERY,
                                    "duplicate indices defined.")));
        return;
    }

    /* Update the persistent storage's meta data tables */
    Put_list puts;
    {
        Row r;
        r["NOX_TABLE"] = table;
        r["NOX_TYPE"] = (int64_t)NONPERSISTENT;
        r["NOX_VERSION"] = (int64_t)0;
        puts.push_back(boost::bind(&Async_transactional_connection::put,
                                   connection, "NOX_SCHEMA_META", r, _1));
    }

    BOOST_FOREACH(Column_definition_map::value_type v, columns) {
        Column_name n = v.first;
        Column_type_collector t;
        boost::apply_visitor(t, v.second);

        Row r;
        r["NOX_TABLE"] = table;
        r["NOX_COLUMN"] = n;
        r["NOX_TYPE"] = t.type;
        puts.push_back(boost::bind(&Async_transactional_connection::put,
                                   connection, "NOX_SCHEMA_TABLE", r, _1));
    }

    BOOST_FOREACH(Index_list::value_type v, indices) {
        Index i = v;
        BOOST_FOREACH(Column_list::value_type c, i.columns) {
            Row r;
            r["NOX_TABLE"] = table;
            r["NOX_INDEX"] = i.name;
            r["NOX_COLUMN"] = c;
            puts.push_back(boost::bind(&Async_transactional_connection::put,
                                       connection, "NOX_SCHEMA_INDEX", r, _1));
        }
    }

    const boost::function<void(const Result)> finish =
        boost::bind(&Async_DHT_storage::create_table_end, this,
                    _1, table, columns, indices, cb);

    connection->begin(Async_transactional_connection::EXCLUSIVE,
                      boost::bind(&Async_DHT_storage::create_table_step, this,
                                  _1, GUID(), puts, finish));
}

void
Async_DHT_storage::create_table_step(const Result& result, const GUID& guid,
                                     const Put_list& puts_,
                                     const boost::function<void(const Result)>&
                                     end) {
    lg.dbg("Storing a meta table row.");

    /* Failure or nothing left. */
    if (result.code != Result::SUCCESS || puts_.empty()) {
        post(boost::bind(end, result));
        return;
    }

    /* Otherwise, put() the next row. */
    Put_list puts = puts_;
    boost::function<void(const Put_callback)> f = puts.front();
    puts.pop_front();

    f(boost::bind(&Async_DHT_storage::create_table_step, this,
                  _1, _2, puts, end));
}

static void rollbacked(const Result& original_result, const Result&,
                       const Async_DHT_storage::Create_table_callback& cb) {
    cb(original_result);
}

void
Async_DHT_storage::create_table_end(const Result& result,
                                    const Table_name& table,
                                    const Column_definition_map& columns,
                                    const Index_list& indices,
                                    const Create_table_callback& cb) {
    if (result.is_success()) {
        /* Create the index rings */
        Index_map m;

        BOOST_FOREACH(Index_list::value_type i, indices) {
            Index v = i;
            m[v.name] = v;
            index_dhts[v.name] = Index_DHT_ptr(new Index_DHT(v.name, this));
        }

        /* Create the table ring */
        content_dhts[table] = Content_DHT_ptr(new Content_DHT(table, this));
        tables[table] = make_pair(columns, m);

        //lg.dbg("COMMITing an EXCLUSIVE transaction.");
        connection->commit(cb);
    } else {
        //lg.dbg("ROLLBACKing an EXCLUSIVE transaction.");
        connection->rollback(boost::bind(&rollbacked, result, _1, cb));
    }
}

void
Async_DHT_storage::drop_table(const Table_name& table,
                              const Drop_table_callback& cb) {
    //Co_scoped_mutex l(&mutex);

    if (tables.find(table) == tables.end()) {
        post(boost::bind(cb, Result(Result::NONEXISTING_TABLE, table +
                                    " does not exist.")));
        return;
    }

    lg.dbg("Dropping a table %s.", table.c_str());
    connection->begin(Async_transactional_connection::EXCLUSIVE,
                      boost::bind(&Async_DHT_storage::drop_table_step_0, this,
                                  _1, table, cb));
}

void
Async_DHT_storage::drop_table_step_0(const Result& result, 
                                     const Table_name& table,
                                     const Drop_table_callback& cb) {
    const boost::function<void(const Result)> end =
        boost::bind(&Async_DHT_storage::drop_table_end, this, _1, table, cb);

    /* Remove the persistent storage meta table entries */
    list<Table_name> tables_to_clean;
    tables_to_clean.push_back("NOX_SCHEMA_META");
    tables_to_clean.push_back("NOX_SCHEMA_TABLE");
    tables_to_clean.push_back("NOX_SCHEMA_INDEX");

    /* Failure, rollback the transaction or if nothing left, quit. */
    if (result.code != Result::SUCCESS || tables_to_clean.empty()) {
        post(boost::bind(end, result));
        return;
    }

    Query q;
    q["NOX_TABLE"] = table;
    connection->get(tables_to_clean.front(), q,
                    boost::bind(&Async_DHT_storage::drop_table_step_1, this,
                                _1, _2, table, tables_to_clean, end));
}

void
Async_DHT_storage::drop_table_step_1(const Result& result,
                                     const Async_transactional_cursor_ptr& cur,
                                     const Table_name& table,
                                     const list<Table_name>& tables_to_clean,
                                     const boost::function<void(const Result)>&
                                     end) {
    /* Failure, rollback the transaction or if nothing left, quit. */
    if (result.code != Result::SUCCESS || tables_to_clean.empty()) {
        post(boost::bind(end, result));
        return;
    }

    /* Find the next row. */
    cur->get_next(boost::bind(&Async_DHT_storage::drop_table_step_2, this,
                              _1, _2, cur, table, tables_to_clean, end));
}

void
Async_DHT_storage::drop_table_step_2(const Result& result,
                                     const Row& row,
                                     const Async_transactional_cursor_ptr& cur,
                                     const Table_name& table,
                                     const list<Table_name>& tables_to_clean,
                                     const boost::function<void(const Result)>&
                                     end) {
    /* If nothing found, close the cursor and move on the next meta
       table. */
    if (result.code == Result::NO_MORE_ROWS) {
        list<Table_name> t = tables_to_clean;
        t.pop_front();

        cur->close(boost::bind(&Async_DHT_storage::drop_table_step_3, this,
                               _1, table, t, end));
        return;
    }

    /* Abort the remove()'s. */
    if (result.code != Result::SUCCESS) {
        post(boost::bind(end, result));
        return;
    }

    /* Remove the row and move to the next one. */
    connection->remove(tables_to_clean.front(), row,
                       boost::bind(&Async_DHT_storage::drop_table_step_1, this,
                                   _1, cur, table, tables_to_clean, end));
}

void
Async_DHT_storage::drop_table_step_3(const Result& result,
                                     const Table_name& table,
                                     const list<Table_name>& t,
                                     const boost::function
                                     <void(const Result)>& end) {
    if (t.empty()) {
        post(boost::bind(end, result));
        return;
    }

    Query q;
    q["NOX_TABLE"] = table;
    connection->get(t.front(), q,
                    boost::bind(&Async_DHT_storage::drop_table_step_1, this,
                                _1, _2, table, t, end));
}

void
Async_DHT_storage::drop_table_end(const Result& result,
                                  const Table_name& table,
                                  const Drop_table_callback& cb) {
    if (result.code == Result::SUCCESS) {
        //lg.dbg("COMMITing the table drop.");

        /* Remove the main table */
        content_dhts.erase(table);

        /* Remove the indices */
        BOOST_FOREACH(Index_map::value_type i, tables[table].second) {
            index_dhts.erase(i.first);
        }

        tables.erase(table);

        /* Commit is not guaranteed to fail. */
        connection->commit(cb);
    } else {
        //lg.dbg("ROLLBACKing the table drop: %s", result.message.c_str());
        connection->rollback(boost::bind(&rollbacked, result, _1, cb));
    }
}

class type_checker
    : public boost::static_visitor<bool> {
public:
    template <typename T, typename U>
    bool operator()(const T&, const U&) const { return false; }

    template <typename T>
    bool operator()(const T&, const T&) const { return true; }
};

bool
Async_DHT_storage::validate_column_types(const Table_name& table,
                                         const Column_value_map& c,
                                         const Result::Code& err_code,
                                         const boost::function
                                         <void(const Result&)>& cb) const {
    Table_definition_map::const_iterator t = tables.find(table);
    if (t == tables.end()) {
        post(boost::bind
             (cb, Result(err_code, "table '" + table + "' doesn't exist.")));
        return false;
    }

    const Table_definition& tdef = t->second;
    const Column_definition_map& cdef = tdef.first;

    BOOST_FOREACH(Column_value_map::value_type t, c) {
        const Column_name& cn = t.first;
        const Column_value cv = t.second;
        Column_definition_map::const_iterator j = cdef.find(cn);
        if (j == cdef.end() ||
            !boost::apply_visitor(type_checker(), cv, j->second)) {
            post(boost::bind(cb, Result(err_code, "column '" + cn + "' "
                                        "doesn't exist or has invalid type ")));
            return false;
        }
    }

    return true;
}

void
Async_DHT_storage::get(const Table_name& table,
                       const Query& query,
                       const Get_callback& cb) {
    //Co_scoped_mutex l(&mutex);
    Context ctxt(table);

    if (!validate_column_types(table, query, Result::INVALID_ROW_OR_QUERY,
                               boost::bind(cb, _1, Context(), Row()))) {
        return;
    }

    Content_DHT_ptr& content_ring = content_dhts[table];

    if (query.empty()) {
        post(boost::bind(&Content_DHT::get, content_ring, content_ring,
                         ctxt, Reference(), false, cb));

    } else {
        Query::const_iterator q = query.find("GUID");
        if (q == query.end()) {
            try {
                const Index index = identify_index(table, query);
                ctxt.index = index.name;

                const Index_DHT_ptr& index_ring = index_dhts[index.name];
                post(boost::bind(&Index_DHT::get, index_ring, content_ring,
                                 ctxt, Reference(Reference::ANY_VERSION,
                                                 compute_sguid(index.columns,
                                                               query)), cb));
            } catch (const exception&) {
                post(boost::bind(cb, Result(Result::INVALID_ROW_OR_QUERY,
                                            "no matching index"),
                                 Context(), Row()));
            }

        } else {
            /* Find the content row directly w/o the use of index. */
            post(boost::bind(&Content_DHT::get, content_ring, content_ring,
                             ctxt, Reference(Reference::ANY_VERSION,
                                             boost::get<GUID>(q->second)),
                             false, cb));
        }
    }
}

void
Async_DHT_storage::get_next(const Context& ctxt,
                            const Get_callback& cb) {
    Context new_ctxt(ctxt);
    Index_DHT_ptr index_ring;
    Content_DHT_ptr content_ring;
    {
        //Co_scoped_mutex l(&mutex);

        if (content_dhts.find(new_ctxt.table) == content_dhts.end()) {
            post(boost::bind(cb, Result(Result::CONCURRENT_MODIFICATION,
                                        "Table removed while iterating."),
                             ctxt, Row()));
            return;
        }

        content_ring = content_dhts[new_ctxt.table];

        if (new_ctxt.index != "") {
            /* The original query used a secondary index */
            if (index_dhts.find(new_ctxt.index) == index_dhts.end()) {
                post(boost::bind(cb, Result(Result::CONCURRENT_MODIFICATION,
                                            "Table removed while iterating."),
                                 ctxt, Row()));
                return;
            }

            index_ring = index_dhts[new_ctxt.index];
        }
    }

    if (index_ring) {
        /* The original query used a secondary index */
        index_ring->get_next(content_ring, new_ctxt, cb);
    } else {
        /* Original query did not use a secondary index. Search for
           the next, and wrap if necessary. */
        content_ring->get_next(content_ring, new_ctxt, cb);
    }
}

void
Async_DHT_storage::put(const Table_name& table,
                       const Row& row,
                       const Async_storage::Put_callback& cb) {
    Context ctxt(table);
    Content_DHT_ptr content_ring;
    GUID_index_ring_map sguids;
    {
        //Co_scoped_mutex l(&mutex);
        if (!validate_column_types(table, row, Result::INVALID_ROW_OR_QUERY,
                                   boost::bind(cb, _1, GUID()))) {
            return;
        }

        /* Pre-compute the index GUIDs per the index for the content
           ring. */
        Index_map& indices = tables[table].second;
        BOOST_FOREACH(Index_map::value_type v, indices) {
            sguids[v.second.name] =
                make_pair(index_dhts[v.second.name],
                          compute_sguid(v.second.columns,row));
        }

        content_ring = content_dhts[table];
    }

    // TODO: replication

    content_ring->put(content_ring, sguids, row, cb);
}

void
Async_DHT_storage::modify(const Context& ctxt,
                          const Row& row,
                          const Async_storage::Modify_callback& cb) {
    Content_DHT_ptr content_ring;
    GUID_index_ring_map sguids;
    {
        //Co_scoped_mutex l(&mutex);
        if (!validate_column_types(ctxt.table, row,
                                   Result::CONCURRENT_MODIFICATION,
                                   boost::bind(cb,_1,Context()))) { return; }

        /* Pre-compute the index GUIDs per the index for the content
           ring. */
        Index_map& indices = tables[ctxt.table].second;
        BOOST_FOREACH(Index_map::value_type v, indices) {
            sguids[v.first] = make_pair(index_dhts[v.first],
                                        compute_sguid(v.second.columns, row));

        }

        content_ring = content_dhts[ctxt.table];
    }

    /* Validate the row and the context match */
    if (row.find("GUID") != row.end() &&
        !(boost::get<GUID>(row.find("GUID")->second) == ctxt.current_row.guid)){
        post(boost::bind(cb, Result(Result::INVALID_ROW_OR_QUERY,
                                    "Row and context don't match."),
                         Context()));
        return;
    }

    // TODO: replication

    content_ring->modify(content_ring, ctxt, sguids, row, cb);
}

void
Async_DHT_storage::remove(const Context& ctxt,
                          const Async_storage::Remove_callback& cb) {
    Content_DHT_ptr content_ring;
    {
        //Co_scoped_mutex l(&mutex);

        if (tables.find(ctxt.table) == tables.end()) {
            RETURN_ERROR(CONCURRENT_MODIFICATION, table + " removed.");
        }

        content_ring = content_dhts[ctxt.table];
    }

    // TODO: replication

    content_ring->remove(content_ring, ctxt, cb);
}

void
Async_DHT_storage::debug(const Table_name& table) {
    lg.dbg("statistics for %s:", table.c_str());
    lg.dbg("main table, entries = %d", content_dhts[table]->size());
    BOOST_FOREACH(const Index_map::value_type& i, tables[table].second) {
        Index_name name = i.first;
        lg.dbg("index table, entries = %d", index_dhts[name]->size());
    }
    

    
}

#define RETURN_TRIGGER_ERROR(CODE, MESSAGE)                             \
    do {                                                                \
        post(boost::bind(cb, Result(Result::CODE, #MESSAGE),            \
                         Trigger_id("", Reference(),-1)));              \
        return;                                                         \
    } while (0);

void
Async_DHT_storage::put_trigger(const Context& ctxt, const Trigger_function& f,
                               const Async_storage::Put_trigger_callback& cb) {
    boost::shared_ptr<DHT> ring;
    {
        //Co_scoped_mutex l(&mutex);

        if (tables.find(ctxt.table) == tables.end()) {
            RETURN_TRIGGER_ERROR(CONCURRENT_MODIFICATION, "Table dropped.");
        }

        if (ctxt.index == "") {
            ring = content_dhts[ctxt.table];
        } else {
            Index_map& indices = tables[ctxt.table].second;
            Index_map::const_iterator i = indices.find(ctxt.index);
            if (i == indices.end()) {
                RETURN_TRIGGER_ERROR(CONCURRENT_MODIFICATION, "Index dropped.");
            }

            ring = index_dhts[i->first];
        }
    }

    ring->put_trigger(ring, ctxt, f, cb);
}

void
Async_DHT_storage::put_trigger(const Table_name& table, const bool sticky,
                               const Trigger_function& f,
                               const Async_storage::Put_trigger_callback& cb) {
    //Co_scoped_mutex l(&mutex);

    if (tables.find(table) == tables.end()) {
        RETURN_TRIGGER_ERROR(CONCURRENT_MODIFICATION, "Table dropped.");
    }

    content_dhts[table]->put_trigger(sticky, f, cb);
}

void
Async_DHT_storage::remove_trigger(const Trigger_id& tid,
                                  const Async_storage::Remove_callback& cb) {
    boost::shared_ptr<DHT> ring;
    {
        //Co_scoped_mutex l(&mutex);

        hash_map<DHT_name, Index_DHT_ptr>::iterator i =
            index_dhts.find(tid.ring);
        if (i != index_dhts.end()) {
            ring = i->second;
        } else {
            hash_map<DHT_name, Content_DHT_ptr>::iterator j =
                content_dhts.find(tid.ring);
            if (j != content_dhts.end()) {
                ring = j->second;
            } else {
                post(boost::bind(cb, Result(Result::CONCURRENT_MODIFICATION,
                                            "Table removed.")));
                return;
            }
        }
    }

    ring->remove_trigger(ring, tid, cb);
}

void
Async_DHT_storage::configure(const Configuration*) {

}

void
Async_DHT_storage::install() {
    Async_transactional_storage* storage;
    resolve(storage);

    if (!storage) { throw runtime_error("transactional storage not found"); }

    Sync_transactional_storage s(storage);
    Sync_transactional_storage::Get_connection_result res = s.get_connection();
    Result result = res.get<0>();
    if (!result.is_success()) {
        throw runtime_error("unable to get a connection");
    }
    Sync_transactional_connection_ptr c = res.get<1>();
    connection = c->connection;

    lg.dbg("Reading the meta data tables.");

    /* First identify the tables to read the meta data for */
    Sync_transactional_connection::Get_result g =
        c->get("NOX_SCHEMA_META", Query());
    result = g.get<0>();
    Sync_transactional_cursor_ptr cursor = g.get<1>();

    if (!result.is_success()) {
        throw runtime_error("unable to read the meta data");
    }

    while (true) {
        Sync_transactional_cursor::Get_next_result r = cursor->get_next();
        Result result = r.get<0>();
        Row row = r.get<1>();

        if (result == Result::NO_MORE_ROWS) { 
            cursor->close();
            break; 
        }

        if (!result.is_success()) {
            cursor->close();
            throw runtime_error("unable to read the meta data");
        }

        if (boost::get<int64_t>(row["NOX_TYPE"]) == NONPERSISTENT) {
            tables[boost::get<string>(row["NOX_TABLE"])];
        }
    }

    /* Then read the column data */
    BOOST_FOREACH(Table_definition_map::value_type v, tables) {
        const Table_name& table = v.first;
        Query q;
        q["NOX_TABLE"] = table;

        Sync_transactional_connection::Get_result g =
            c->get("NOX_SCHEMA_TABLE", q);
        Result result = g.get<0>();
        Sync_transactional_cursor_ptr cursor = g.get<1>();

        if (!result.is_success()) {
            throw runtime_error("unable to read the meta data: " +
                                result.message);
        }   

        while(true) {
            Sync_transactional_cursor::Get_next_result g = cursor->get_next();
            Result r = g.get<0>();
            Row row = g.get<1>();

            if (r.code == Result::NO_MORE_ROWS) {
                cursor->close();
                break; 
            }

            if (!r.is_success()) {
                cursor->close();
                throw runtime_error("unable to read the meta data: " +
                                    r.message);
            }

            Column_name& col_name = boost::get<string>(row["NOX_COLUMN"]);
            switch (boost::get<int64_t>(row["NOX_TYPE"])) {
            case COLUMN_INT:
                tables[table].first[col_name] = (int64_t)0;
                break;
            case COLUMN_TEXT:
                tables[table].first[col_name] = string("");
                break;
            case COLUMN_DOUBLE:
                tables[table].first[col_name] = (double)0;
                break;
            case COLUMN_GUID:
                tables[table].first[col_name] = GUID();
                break;
            default:
                throw runtime_error("corrupted meta data");
            }
        }
    }

    /* Then read the index data */
    BOOST_FOREACH(Table_definition_map::value_type v, tables) {
        const Table_name& table = v.first;
        Query q;
        q["NOX_TABLE"] = table;

        Sync_transactional_connection::Get_result g =
            c->get("NOX_SCHEMA_INDEX", q);
        Result result = g.get<0>();
        Sync_transactional_cursor_ptr cursor = g.get<1>();

        if (!result.is_success()) {
            throw runtime_error("unable to read the meta data");
        }   

        while(true) {
            Sync_transactional_cursor::Get_next_result g = cursor->get_next();
            Result r = g.get<0>();
            Row row = g.get<1>();

            if (r.code == Result::NO_MORE_ROWS) {
                cursor->close();
                break; 
            }
            if (r.code != Result::SUCCESS) {
                cursor->close();
                throw runtime_error("unable to read the meta data");
            }

            const Index_name index_name =
                boost::get<string>(row["NOX_INDEX"]);
            tables[table].second[index_name].name = index_name;
            tables[table].second[index_name].columns.
                push_back(boost::get<string>(row["NOX_COLUMN"]));
        }
    }

    /* Initialize the table structures */
    BOOST_FOREACH(Table_definition_map::value_type v, tables) {
        assert(content_dhts.find(v.first) == content_dhts.end());
        content_dhts[v.first] = Content_DHT_ptr(new Content_DHT(v.first, this));

        BOOST_FOREACH(Index_map::value_type i, v.second.second) {
            if (index_dhts.find(i.first) != index_dhts.end()) {
                throw runtime_error("corrupted database");
            }

            index_dhts[i.first] = Index_DHT_ptr(new Index_DHT(i.first, this));
        }
    }
}

Index
Async_DHT_storage::identify_index(const Table_name& table,
                                  const Query& q) const {
    Table_definition_map::const_iterator t = tables.find(table);
    const Index_map& indices = t->second.second;

    BOOST_FOREACH(Index_map::value_type v, indices) {
        if (v.second == q) { return v.second; }
    }

    throw invalid_argument("cannot find the index");
}

REGISTER_COMPONENT(vigil::container::Simple_component_factory<Async_DHT_storage>,
                   Async_storage);
