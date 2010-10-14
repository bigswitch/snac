# Copyright 2008, 2009 (C) Nicira, Inc.
# 
# This file is part of NOX.
# 
# NOX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# NOX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NOX.  If not, see <http://www.gnu.org/licenses/>.
"""\
Utility base classes to ease storage/python translations
"""

import code
import logging
import re
from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from nox.ext.apps.storage import TransactionalConnection
from nox.netapps.storage.storage import Storage, StorageException

lg = logging.getLogger('StorageTableUtil')

def _plural_suffix(count):
    if count == 1:
        return ""
    return "s"


def get_connection_if_none(storage, conn=None):
    """Return deferred returning connection to transactional stroage.

    If conn is None, a new connection is obtained, otherwise, conn is
    simply returned in a deferred
    """
    def _get_conn_cb(res):
        result, conn = res
        if result[0] != Storage.SUCCESS:
            errmsg = "Failed to connect to transactional storage: %d (%s)"\
                     %(result[0], result[1])
            lg.error(errmsg)
            raise Exception(errmsg)
        return conn
    if conn is not None:
        return defer.succeed(conn)
    lg.debug("Getting a new transactional storage connection...")
    d = storage.get_connection()
    d.addCallback(_get_conn_cb)
    return d


def get_all_rows_for_query(storage, table_name, query={}, conn=None):
    ret = []
    def _done(res):
        return ret
    def _row_cb(row):
        ret.append(row)
    d = get_rows_for_query(storage, table_name, _row_cb, query, conn)
    d.addCallback(_done)
    return d

def _get_next_loop(cursor, row_handler, d):
    """Iterate through the storage get() results and invoke a handler for
    each row. Note the use of reactor's timer facilities to avoid
    adding a new callback per handled row to a deferred."""

    def process_result(res, cursor, row_handler, d2):
        result, row = res
        if result[0] == Storage.SUCCESS:
            row_handler(row)
            reactor.callLater(0, _get_next_loop, cursor, row_handler, d2)

        elif result[0] == Storage.NO_MORE_ROWS:
            return d2.callback(None)

        else:
            raise StorageException("Failed to get row: %s" % result)

    cursor.get_next().\
        addCallback(process_result, cursor, row_handler, d).\
        addErrback(d.errback) # Propagate the error to the caller.


def _remove_next_loop(conn, table_name, rows, removed_rows, d):
    """Iterate through the 'rows' and remove every row.  Note the use of
    reactor's timer facilities to avoid adding a new callback per
    removed row to a deferred."""

    if len(rows) == 0:
        d.callback(None)
        return

    def process_result(res, conn, table_name, rows, removed_rows, d):
        if res is not None and res[0] != Storage.SUCCESS:
            raise Exception("Failed to remove row")

        removed_rows.append(row)
        reactor.callLater(0, _remove_next_loop, conn, table_name, rows, 
                          removed_rows, d)

    row = rows.pop()
    conn.remove(table_name, row).\
        addCallback(process_result, conn, table_name, rows, removed_rows, d).\
        addErrback(d.errback) # Propagate the error to the caller.

def get_rows_for_query(storage, table_name, row_cb, query={}, conn=None):
    def _do_get(res, state='get_cursor', cursor=None):
        if state == 'get_cursor':
            conn = res
            d = conn.get(table_name, query)
            d.addCallback(_do_get, 'start_fetching_rows')
        elif state == 'start_fetching_rows':
            result, cursor = res
            if result[0] != Storage.SUCCESS:
                raise StorageException("Failed to get cursor for 'get' "\
                        "on table '%s': %s" %(table_name, result))

            # Note, the _get_next_loop will call d.callback once done.
            d = defer.Deferred().\
                addCallback(_do_get, 'close_cursor', cursor).\
                addErrback(_close_cursor_eb, cursor)
            _get_next_loop(cursor, row_cb, d)

        elif state == 'close_cursor':
            d = cursor.close()
            d.addCallback(_do_get, 'done_with_get', None)
        elif state == 'done_with_get':
            return
        else:
            raise Exception("Invalid state: '%s'" %state)
        return d
    query = query or {}
    d = get_connection_if_none(storage, conn)
    d.addCallback(_do_get)
    return d

def get_all_rows_for_unindexed_query(storage, table_name,
        table_index_tuple_list, exact_params, regex_str_params, conn=None):
    ret = []
    def _done(res):
        return ret
    def _row_cb(row):
        ret.append(row)
    d = get_rows_for_unindexed_query(storage, table_name, 
            table_index_tuple_list,_row_cb, exact_params, regex_str_params,
            conn)
    d.addCallback(_done)
    return d

def get_rows_for_unindexed_query(storage, table_name,
        table_index_tuple_list, row_cb, exact_params, regex_str_params,
        conn=None):
    def _do_get(conn):
        regex_params = dict([(k, re.compile(v)) \
                for k,v in regex_str_params.items()])
        def _row_cb(row):
            for key, exact_match in exact_params.items():
                if row[key] != exact_match:
                    return
            for key, regex in regex_params.items():
                if not regex.search(row[key]):
                    return
            row_cb(row)
        #find the matching index with the most columns
        indices = sorted(table_index_tuple_list,
            cmp=(lambda x,y: cmp(len(y),len(x))))
        exact_param_set = set(exact_params)
        indexed_query = {}
        for index in indices:
            if set(index) <= exact_param_set:
                for key in index:
                    indexed_query[key] = exact_params.pop(key)
                break
        d = get_rows_for_query(storage, table_name, _row_cb,
                indexed_query, conn)
        return d
    d = get_connection_if_none(storage, conn)
    d.addCallback(_do_get)
    return d


def _close_cursor_eb(failure, cursor):
    def _close_cb(res):
        return failure
    d = cursor.close()
    d.addCallbacks(_close_cb, _close_cb)
    return d


def call_in_txn(storage, method, *args, **kwargs):
    """Wrap call to method within storage transaction, rolling back on errback

    'method' must have a keyword argument of conn; a new TransactionalStorage
    connection will be obtained and passed as the 'conn' keyword argument
    to 'method'
    """
    def _txn_cb(res, prev_res):
        return prev_res
    def _close_txn(res, conn):
        d = conn.commit()
        d.addCallback(_txn_cb, res)
        return d
    def _abort_txn(res, conn):
        d = conn.rollback()
        d.addCallback(_txn_cb, res)
        return d
    def _get_conn(res):
        if res is not None:
            result, conn = res
            if result[0] != Storage.SUCCESS:
                raise Exception("Failed to connect to transactional " \
                                "storage: %d (%s)" %(result[0], result[1]))
        d = conn.begin(TransactionalConnection.EXCLUSIVE)
        kwargs['conn']=conn
        d.addCallback(method, *args, **kwargs)
        d.addCallback(_close_txn, conn)
        d.addErrback(_abort_txn, conn)
        return d
    if 'conn' in kwargs and kwargs['conn'] is not None:
        conn = kwargs['conn']
        mode = conn.get_transaction_mode()
        if mode != TransactionalConnection.EXCLUSIVE:
            return _get_conn(((Storage.SUCCESS, ''), conn))
        else:
            return method(None, *args, **kwargs)
    else:   
        d = storage.get_connection()
        d.addCallback(_get_conn)
    return d


def drop_tables(storage, table_names, conn=None):
    """Drops all tables listed in table_names in a single transaction
    Drop failures are silently ignored
    """
    def _do_drop(res, conn=None):
        ret = defer.Deferred()
        for table_name in table_names:
            d = conn.drop_table(table_name)
            d.addCallback(_table_dropped, ret)
            d.addErrback(_table_dropped, ret)
        return ret
    def _table_dropped(res, ret, drop_results=[]):
        drop_results.append(res)
        if len(drop_results) == len(table_names):
            ret.callback(None)
    def _done_cb(res):
        lg.debug("All %d tables have been dropped" %len(table_names))
        return res
    lg.debug("Dropping %d tables" %len(table_names))
    d = call_in_txn(storage, _do_drop, conn=conn)
    d.addCallback(_done_cb)
    return d


class StorageRecord(object):
    """An "abstract" class representing a storage "row"
      Subclasses should include the following static members:
        _columns : a name/type map of columns in the table
       __slots__ : must be reasigned as "__slots__ = _columns.keys()"

      Example: the following class represents table rows with 2 columns
        class DemoStorageRecord(StorageRecord):
            _columns = {'column1' : 'string', 'column2' : 0}
            __slots__ = _columns.keys()

            def __init__(self):
                pass

        DemoStorageRecord.get_storage_table_def()
            #returns {'COLUMN1' : 'string', 'COLUMN2' : 0}

        dsr = DemoStorageRecord()
        dsr.column1 = 'abc'
        dsr.column2 = 4
        dsr.noexistantcolumn = 1 #FAILS
        dsr.to_storage_row() #returns {'COLUMN1' : 'abc, "COLUMN2 : 4}
    """

    #_columns must be replaced with a name/type map of columns in the table
    _columns = { 'guid' : tuple }

    #__slots__ must be reasiggned in each subclass (use the same line below)
    __slots__ = _columns.keys()

    #_default_type_values should be sane for most implementations
    _default_type_values = { type('') : '', type(0l) : 0l,
                             type(0.0) : 0.0, type(0) : 0 }

    @classmethod
    def get_storage_col_type(cls, col):
        """Return the storage type for column 'col'
        """
        return cls._columns[col]

    @classmethod
    def get_storage_table_def(cls):
        """Return name-type pairs suitable for storage table creation
        """
        ret = {}
        for var in cls.__slots__:
            #By convention, we store columns names in db as UPPERCASE
            ret[var.upper()] = cls.get_storage_col_type(var)
        return ret

    @classmethod
    def from_storage_row(cls, row_dict):
        """Return a new instance populated from name-value pairs from dict

        raises KeyError if dict does not contain required values
        """
        dbcols = [col.upper() for col in cls._columns.keys()]
        missing_keys = set(dbcols) - set(row_dict.keys())
        if len(missing_keys) > 0:
            raise KeyError,"Missing required fields in row_dict: %s"\
                    %str(missing_keys)
        instance = cls.__new__(cls)
        for var in cls.__slots__:
            setattr(instance, var, row_dict[var.upper()])
        setattr(instance, 'guid', row_dict[u'GUID'])
        return instance

    @classmethod
    def get_columns(cls):
        return cls.get_storage_table_def().keys()

    def to_storage_row(self, include_guid=False):
        """Return name-value pairs suitable for passing to storage
        """
        ret = {}
        for var in self.__slots__:
            val = getattr(self, var)
            if val is None:
                t = self.get_storage_col_type(var)
                if type(t) == type:
                    val = self._default_type_values[t]
                else:
                    val = self._default_type_values[type(t)]
            ret[var.upper()] = val
        if include_guid and hasattr(self, 'guid'):
            ret['GUID'] = self.guid
        return ret


class StorageTable():
    """\
    A class representing a storage table with StorageRecord rows

    If cache_contents is True, the full table will be cached and
    synchronous reads will be enabled.
    """
    def __init__(self, storage, table_name, row_class, table_indices = (),
                 cache_contents=False, version=0):
        self.storage = storage
        self.table_name = table_name
        self.table_indices = dict(table_indices) # {idx_name -> (cols)}
        self.row_class = row_class
        self.cache_contents = cache_contents
        self.version = version

        self.row_cache = None # {GUID -> record}
        self.cache_indices = None # {idx_cols->(idx_name, {key->{GUID->rec}})}

    def _get_db_index_def(self):
        ret = []
        for idx, cols in self.table_indices.items():
            ret.append((idx, tuple([col.upper() for col in cols])))
        return tuple(ret)

    def ensure_table_exists(self, conn=None):
        """Verify table exists in storage, creating if necessary

        Returns deferred which will fire successfully when the table is
        created (or existence is verified)
        """
        lg.debug("Ensuring table '%s' exists"%self.table_name)
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._ensure_table_exists)
        return d

    def _ensure_table_exists(self, conn):
        d = conn.create_table(self.table_name,
                              self.row_class.get_storage_table_def(),
                              self._get_db_index_def(), 
                              self.version)
        if self.cache_contents and self.row_cache is None:
            #TODO: add trigger to maintain cache on external changes
            d.addCallback(self._cache_table_contents_cb, conn)
        d.addCallback(self.ensure_table_exists_cb)
        d.addErrback(self.ensure_table_exists_eb)
        return d

    def _cache_record(self, rec):
        assert(hasattr(rec, 'guid'))
        self.row_cache[rec.guid] = rec
        for idx in self.table_indices.keys():
            col_list = sorted(self.table_indices[idx])
            idx_cols = ';'.join([cn.upper() for cn in col_list])
            idx_key = ';'.join([str(getattr(rec, cn)) for cn in col_list])
            cache_idx = self.cache_indices.get(idx_cols) or (None, {})
            idx_val = cache_idx[1].get(idx_key) or {}
            idx_val[rec.guid] = rec
            cache_idx[1][idx_key] = idx_val
            self.cache_indices[idx_cols] = (idx, cache_idx[1])
        return rec

    def _cache_records(self, recs):
        for rec in recs:
            self._cache_record(rec)
        return recs

    def _uncache_records(self, recs):
        for rec in recs:
            guid = rec.guid
            del self.row_cache[guid]
            for idx in self.table_indices.keys():
                cols = sorted(self.table_indices[idx])
                idx_cols = ';'.join([cn.upper() for cn in cols])
                idx_key = ';'.join([str(getattr(rec, cn)) for cn in cols])
                cache_idx = self.cache_indices.get(idx_cols) or (None, {})
                del cache_idx[1][idx_key][guid]
                if len(cache_idx[1][idx_key]) == 0:
                    del cache_idx[1][idx_key]
        return recs

    def _cache_table_contents_cb(self, res, conn, state=0):
        lg.debug("Caching contents of table '%s'"  %self.table_name)
        if state == 0:
            self.row_cache = None #reset if already cached
            d = self.get_all_recs_for_query({})
            d.addCallback(self._cache_table_contents_cb, conn, state=1)
            return d
        elif state == 1:
            self.row_cache = self.row_cache or {}
            if self.cache_indices is None:
                self.cache_indices = {}
                for idx in self.table_indices.keys():
                    col_list = sorted(self.table_indices[idx])
                    idx_cols = ';'.join([cn.upper() for cn in col_list])
                    self.cache_indices[idx_cols] = (idx, {})
            self._cache_records(res)
            lg.debug("Table '%s' cached" %self.table_name)
            return (Storage.SUCCESS, r'')
        else:
            raise Exception("Invalid State")

    def ensure_table_exists_cb(self, res):
        """Called upon successfully creating or validating table exists
        """
        lg.debug("Done ensuring table '%s' exists"%self.table_name)
        return res

    def ensure_table_exists_eb(self, failure):
        """Called upon failure while creating or validating table existence
        """
        lg.debug("Failed to ensure table '%s' exists"%self.table_name)
        return failure

    @staticmethod
    def _to_db_query(query):
        #By convention, we store columns in storage in UPPERCASE
        return dict([(key.upper(), val) for (key, val) in query.items()])

    def get_all_recs_for_query(self, query, conn=None):
        """Returns deferred returning tuple of row_class instances
        corresponding to all records returned by query

        Not suitable for queries returning many records as this will cache
        them all in memory before callback is issued
        """
        if self.row_cache is not None:
            lg.debug("Getting all records in '%s' matching query '%s' (cached)"
                    %(self.table_name, str(query)))
            d = defer.Deferred()
            try:
                ret = self.get_all_recs_for_query_s(query)
                d.callback(ret)
            except Exception, e:
                d.errback(Failure(e))
        else:
            lg.debug("Getting all records in '%s' matching query '%s'"
                    %(self.table_name, str(query)))
            d = get_all_rows_for_query(self.storage, self.table_name,
                    query=self._to_db_query(query), conn=conn)
            d.addCallback(self._rows_to_recs)
        return d

    def get_all_recs_for_unindexed_query(self, exact_params,
            regex_str_params, conn=None):
        """Returns deferred returning tuple of row_class instances
        corresponding to all records matching exact params and
        regex_str_params.

        If possible, an indexed query will be made using some or all
        parameters from exact_params, and the resulting rows will be
        filtered by the remaining exact_params and regex_str_params.
        """
        index_tuples = self.table_indices.values()
        db_index_tuples = [[s.upper() for s in cols] for cols in index_tuples]
        d = get_all_rows_for_unindexed_query(self.storage, self.table_name,
                db_index_tuples,
                self._to_db_query(exact_params), 
                self._to_db_query(regex_str_params), conn=conn)
        d.addCallback(self._rows_to_recs)
        return d

    def get_all_recs_for_query_s(self, query):
        """Synchronous interface returning tuple of row_class instances
        corresponding to all records returned by query

        If class was not instantiated with cache_contents=True, a
        TypeError is raised.
        """
        if not self.cache_contents:
            raise TypeError("Synchronous access not supported when "
                             "initialized with cache_contents=False")
        if self.row_cache is None:
            raise TypeError("Table not initialized")
        if query == {}:
            return self.row_cache.values()
        idx_cols = ';'.join([col.upper() for col in sorted(query.keys())])
        idx_vals = ';'.join([str(query[col]) for col in sorted(query.keys())])
        assoc_idx = self.cache_indices.get(idx_cols)
        if assoc_idx is None:
            raise Exception("No matching index found for query")
        idx_name, idx = assoc_idx
        val_hash = idx.get(idx_vals)
        if val_hash is not None:
            return val_hash.values()
        return []

    def _rows_to_recs(self, rows):
        recs = []
        for row in rows:
            recs.append(self.row_class.from_storage_row(row))
        return recs

    def _abort_txn_eb(self, res, conn, state=0, orig_failure=None):
        if state == 0:
            d = conn.rollback()
            d.addCallback(self._abort_txn_eb, conn, state=1, orig_failure=res)
            return d
        elif state == 1:
            return orig_failure
        else:
            raise Exception("Invalid state: "+str(state))

    def _close_cursor_eb(self, res, cursor, state=0, orig_failure=None):
        if state == 0:
            d = cursor.close()
            d.addCallback(self._close_cursor_eb, cursor, state=1,
                    orig_failure=res)
            #same behavior if cursor close fails
            d.addErrback(self._close_cursor_eb, cursor, state=1,
                    orig_failure=res)
            return d
        elif state == 1:
            return orig_failure
        else:
            raise Exception("Invalid state: "+str(state))

    def modify_all_records(self, records=None, modified=None, conn=None):
        def _modify_all(res, records, modified, conn=conn):
            if res is not None:
                modified.append(res)
            if len(records):
                rec = records.pop()
                d = self.modify_record(rec, conn)
                d.addCallback(_modify_all, records, modified, conn)
                return d
            else:
                return defer.succeed(modified)
        d = call_in_txn(self.storage, _modify_all, records[:], [],
                conn=conn)
        return d

    def modify_record(self, record, conn=None):
        def _modify_rec(conn):
            d = conn.modify(self._table_name,
            record.to_storage_row(include_guid=True))
            d.addCallback(_construct_rec_from_result, record)
            return d
        def _construct_rec_from_result(res, record):
            if res[0] != Storage.SUCCESS:
                return Failure("Failed to modify record")
            return record
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(_modify_rec)
        if self.cache_contents:
            d.addCallback(self._cache_record)
        return d

    def remove_all_rows_for_query(self, query={}, conn=None):
        """Removes all rows matching query
        Returns tuple of row_class instances of deleted rows
        """
        lg.debug("Removing all rows in table '%s' matching query '%s'"
                %(self.table_name, query))
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._remove_all_rows_for_query, 'entry', None,
                query=self._to_db_query(query))
        if self.cache_contents:
            d.addCallback(self._uncache_records)
        return d

    def _remove_all_rows_for_query(self, res, state, conn, cursor=None,
                                  rows=None, query={}, removed_rows=None,
                                  close_txn=True):
        rows = rows or []
        removed_rows = removed_rows or []
        if state == 'entry':
            #start transaction if not already in one
            conn = res
            mode = conn.get_transaction_mode()
            if mode != TransactionalConnection.EXCLUSIVE:
                d = conn.begin(TransactionalConnection.EXCLUSIVE)
                d.addCallback(self._remove_all_rows_for_query, 'txn_ready',
                        conn, query=query)
                d.addErrback(self._abort_txn_eb, conn)
            else:
                return self._remove_all_rows_for_query((Storage.SUCCESS,
                    ''), 'txn_ready', conn, query=query, close_txn=False)

        elif state == 'txn_ready':
            #transaction ready, need to get all rows
            if res[0] != Storage.SUCCESS:
                raise Exception("Failed to start transaction")
            d = conn.get(self.table_name, query)
            d.addCallback(self._remove_all_rows_for_query, 'got_cursor', conn,
                    close_txn=close_txn)

        elif state == 'got_cursor':
            #got cursor, start fetching rows
            result, cursor = res
            if result[0] != Storage.SUCCESS:
                raise Exception("Failed to get cursor")

            # Note, the _get_next_loop will call d.callback once done.
            d = defer.Deferred().\
                addCallback(self._remove_all_rows_for_query, 'close_cursor',
                            conn, cursor, rows, query, removed_rows, 
                            close_txn).\
                addErrback(self._close_cursor_eb, cursor)
            _get_next_loop(cursor, lambda row: rows.append(row), d)

        elif state == 'close_cursor':
            # First close the cursor and then proceed to the remove
            # next loop, after which the 'rows_removed' state follows.
            # Note, the _remove_next_loop will call d.callback once
            # done.
            d = defer.Deferred().\
                addCallback(self._remove_all_rows_for_query, 'rows_removed',
                            conn, cursor, rows, query, removed_rows, close_txn)
            cursor.close().\
                addCallback(lambda ignore:
                                _remove_next_loop(conn, self.table_name, rows,
                                                  removed_rows, d)).\
                addErrback(d.errback)

        elif state == 'rows_removed':
            def complete(result_ignored, removed_rows):
                return [self.row_class.from_storage_row(row)
                        for row in removed_rows]
            
            if close_txn:
                d = conn.commit().\
                    addCallback(complete, removed_rows)
            else:
                return complete(None, removed_rows)

        else:
            raise Exception("Invalid state")
        return d

    def put_record(self, record, conn=None):
        """Put record in table
        A new connection will be obtained if conn is None

        Returns deferred returning row_class instance of row put
        """
        lg.debug("Adding 1 record to table %s" %self.table_name)
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._put_record, record)
        if self.cache_contents:
            d.addCallback(self._cache_record)
        return d

    def _construct_rec_from_put_result(self, res, record):
        result, guid = res
        if result[0] != Storage.SUCCESS:
            return Failure("Failed to put record")
        record.guid = guid
        row = record.to_storage_row()
        row['GUID'] = guid
        return record.from_storage_row(row)

    def _put_record(self, conn, record):
        d = conn.put(self._table_name, record.to_storage_row())
        d.addCallback(self._construct_rec_from_put_result, record)
        return d

    def put_record_no_dup(self, record, unique_index_tuple, conn=None):
        """Put record only if no records exists with matching values in
        columns indexed by unique_index_tuple

        Returns deferred returning row_class instance of row put
        """
        lg.debug("Adding 1 record to table '%s' if not duplicate"
                %self.table_name)
        assert(type(unique_index_tuple) == tuple)
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._put_record_no_dup, 0, conn, record,
                list(unique_index_tuple))
        if self.cache_contents:
            d.addCallback(self._cache_record)
        return d

    def _put_record_no_dup(self, res, state, conn, record, unique_index_list,
                           cursor=None, existing_rows=False, put_result=None,
                           close_txn=True):
        if state == 0:
            #start transaction if not already in one
            conn = res
            mode = conn.get_transaction_mode()
            if mode != TransactionalConnection.EXCLUSIVE:
                d = conn.begin(TransactionalConnection.EXCLUSIVE)
                d.addCallback(self._put_record_no_dup, 1, conn, record,
                        unique_index_list)
                d.addErrback(self._abort_txn_eb, conn)
            else:
                return self._put_record_no_dup((Storage.SUCCESS, r''),
                        1, conn, record, unique_index_list, close_txn=False)
        elif state == 1:
            #transaction started, get cursor for next unique_index query
            if res[0] != Storage.SUCCESS:
                raise Exception("Failed to start transaction")
            if len(unique_index_list) == 0:
                #go directly to put
                return self._put_record_no_dup((Storage.SUCCESS,r''), 2,
                        conn, record, unique_index_list, existing_rows=False,
                        close_txn=close_txn)
            else:
                query = {}
                rec_dict = record.to_storage_row()
                idx = unique_index_list.pop()
                idx_cols = self.table_indices.get(idx)
                if idx_cols is None:
                    d = defer.Deferred()
                    d.errback("Index '%s' does not exist" %idx)
                    return d
                for col in idx_cols:
                    col = col.upper()
                    query[col] = rec_dict[col]
                d = conn.get(self.table_name, query)
                d.addCallback(self._put_record_no_dup, 2, conn, record,
                        unique_index_list, close_txn=close_txn)
        elif state == 2:
            #got cursor, look for a matching row
            result, cursor = res
            if result[0] != Storage.SUCCESS:
                raise Exception("Failed to get cursor")
            d = cursor.get_next()
            d.addCallback(self._put_record_no_dup, 3, conn, record,
                    unique_index_list, cursor, close_txn=close_txn)
            d.addErrback(self._close_cursor_eb, cursor)
        elif state == 3:
            #check result and close cursor
            result, row = res
            d = cursor.close()
            if result[0] == Storage.NO_MORE_ROWS:
                #no matching records, check the next
                if len(unique_index_list) > 0:
                    # Check the next index.  Note, recursion is
                    # acceptable here since the # of indices will be
                    # very small in any case.
                    return self._put_record_no_dup((Storage.SUCCESS,r''), 1,
                            conn, record, unique_index_list,
                            close_txn=close_txn)
                else:
                    d.addCallback(self._put_record_no_dup, 4, conn, record,
                            unique_index_list, existing_rows=False,
                            close_txn=close_txn)
            elif result[0] == Storage.SUCCESS:
                #matching rows, close cursor and return error
                d.addCallback(self._put_record_no_dup, 4, conn, record,
                        unique_index_list, existing_rows=True,
                        close_txn=close_txn)
            else:
                raise Exception("Error searching for duplicate records")
        elif state == 4:
            #close okay
            if existing_rows:
                d = defer.Deferred()
                d.errback((Storage.INVALID_ROW_OR_QUERY,
                        r'Row with matching columns already exists'))
            else:
                d = self.put_record(record, conn)
                d.addCallback(self._put_record_no_dup, 5, conn, record,
                        unique_index_list, existing_rows=existing_rows,
                        close_txn=close_txn)
        elif state == 5:
            #put returned
            if close_txn:
                #there is only one put, so we can commit regardless of result
                d = conn.commit()
                d.addCallback(self._put_record_no_dup, 6, conn, record,
                        unique_index_list, put_result=res)
            else:
                return self._put_record_no_dup(res, 6, conn, record,
                        unique_index_list, put_result=res)
        elif state == 6:
            #committed
            return put_result
        else:
            raise Exception("Invalid state")
        return d

    def put_all_records(self, recs, conn=None):
        """Put all records in a single transaction

        Returns tuple of row_class instances that were added
        """
        lg.debug("Adding all %d records to table %s" %(len(recs),
                self.table_name))
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._put_all_records_cb, 'entry', list(recs), None)
        if self.cache_contents:
            d.addCallback(self._cache_records)
        return d

    def put_all_records_no_dup(self, recs, unique_index_tuple, conn=None):
        """Put all records in a single transaction, failing if any records
        exist with matching values in columns indexed by unique_index_tuple

        Returns tuple of row_class instances that were added
        """
        lg.debug("Adding %d record%s to table '%s' if not duplicate"
                %(len(recs), _plural_suffix(len(recs)), self.table_name))
        d = get_connection_if_none(self.storage, conn=conn)
        d.addCallback(self._put_all_records_cb, 'entry', list(recs), None,
                unique_index_tuple=unique_index_tuple)
        if self.cache_contents:
            d.addCallback(self._cache_records)
        return d

    def _put_all_records_cb(self, res, state, recs, conn, added=None,
                            close_txn=True, unique_index_tuple=None):
        added = added or []
        if state == 'entry':
            #start transaction if not already in one
            conn = res
            mode = conn.get_transaction_mode()
            if mode != TransactionalConnection.EXCLUSIVE:
                d = conn.begin(TransactionalConnection.EXCLUSIVE)
                d.addCallback(self._put_all_records_cb, 'txn_ready',
                        recs, conn, unique_index_tuple=unique_index_tuple)
                d.addErrback(self._abort_txn_eb, conn)
            else:
                return self._put_all_records_cb((Storage.SUCCESS, r''),
                        'txn_ready', recs, conn, added, False)
        elif state == 'txn_ready':
            if res[0] != Storage.SUCCESS:
                raise Exception("Failed to start transaction")
            return self._put_all_records_cb(None, 'putting_recs', recs, conn,
                    close_txn=close_txn, unique_index_tuple=unique_index_tuple)
        elif state == 'putting_recs':
            if res is not None:
                added.append(res)
            if len(recs) > 0:
                record = recs.pop(0)
                if unique_index_tuple is not None:
                    d = self.put_record_no_dup(record, unique_index_tuple,
                            conn)
                else:
                    d = self.put_record(record, conn)
                    #d = conn.put(self.table_name, record.to_storage_row())
                d.addCallback(self._put_all_records_cb, 'putting_recs', recs,
                        conn, added, close_txn=close_txn,
                        unique_index_tuple=unique_index_tuple)
            else:
                if close_txn:
                    d = conn.commit()
                    d.addCallback(self._put_all_records_cb, 'return', recs,
                            conn, added)
                else:
                    return self._put_all_records_cb(None, 'return', recs, conn,
                            added)
        elif state == 'return':
            return added
        else:
            raise Exception("Invalid state")
        return d

