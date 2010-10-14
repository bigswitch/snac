# Copyright 2008 (C) Nicira, Inc.
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

import logging
import copy
import simplejson
import types

from nox.lib.core import *

from nox.apps.storage import TransactionalStorage
from nox.apps.storage.storage import Storage, StorageException
from nox.apps.storage.StorageTableUtil import *

lg = logging.getLogger('storage_schema')


class NoxSchemaMetaRecord(StorageRecord):
    _columns = {'nox_table' : str, 'nox_type' : int}
    __slots__ = _columns.keys()

class NoxSchemaMetaTable(StorageTable):
    def __init__(self, storage):
        StorageTable.__init__(self, storage, 'NOX_SCHEMA_META',
                NoxSchemaMetaRecord, ())


class NoxSchemaTableRecord(StorageRecord):
    _columns = {'nox_table' : str, 'nox_column' : str, 'nox_type' : int}
    __slots__ = _columns.keys()

class NoxSchemaTableTable(StorageTable):
    def __init__(self, storage):
        StorageTable.__init__(self, storage, 'NOX_SCHEMA_TABLE',
                NoxSchemaTableRecord, ())


class NoxSchemaIndexRecord(StorageRecord):
    _columns = {'nox_table' : str, 'nox_index' : str, 'nox_column' : str}
    __slots__ = _columns.keys()

class NoxSchemaIndexTable(StorageTable):
    def __init__(self, storage):
        StorageTable.__init__(self, storage, 'NOX_SCHEMA_INDEX',
                NoxSchemaIndexRecord, ())


class DBSchemaEncoder(simplejson.JSONEncoder):

    SQL_type = { Storage.COLUMN_INT: "INT",
                 Storage.COLUMN_TEXT: "TEXT",
                 Storage.COLUMN_DOUBLE: "DOUBLE",
                 Storage.COLUMN_GUID: "GUID" }

    def default(self, obj):
        if isinstance(obj, DBTable):
            fld_names = []
            fld_types = []
            indexes = {}
            for n, t in obj.fields.iteritems():
                fld_names.append(n)
                fld_types.append(t)
            for o in obj.indexes.itervalues():
                indexes[o.name] = o.fields
            return { "table_name": obj.name,
                     "field_names" : fld_names,
                     "field_types" : fld_types }
        elif isinstance(obj, DBSchema):
            typename2id = {}
            typeid2name = {}
            for v,n in DBSchemaEncoder.SQL_type.iteritems():
                typename2id[n] = v
                typeid2name[v] = n
            return { "identifier" : "table_name",
                     "label" : "table_name",
                     "typename2id" : typename2id,
                     "typeid2name" : typeid2name,
                     "items": obj.tables.values() }
        else:
            return simplejson.JSONEncoder.default(self,obj)


class DBTable:
    def __init__(self, name=None):
        self.name = name
        self.fields = {}
        self.indexes = {}

    def json_encoding(self):
        return {"table": t.name, "fields": t.fields.keys() }


class DBIndex:
    def __init__(self, name=None):
        self.name = name
        self.fields = []


class DBSchema:
    def __init__(self, storage_type, dbname, cdb, cdb_conn):
        self.storage_type = storage_type
        self.dbname = dbname
        self.cdb = cdb
        self.conn = cdb_conn
        self.tables = {} # table-name -> DBTable objects 
        self.trigger_map = {} # table-name to trigger for NOX_*_TABLE tables

        self._schema_meta_table = NoxSchemaMetaTable(cdb)
        self._schema_table_table = NoxSchemaTableTable(cdb)
        self._schema_index_table = NoxSchemaIndexTable(cdb)
        self._is_loaded = False

    def load_schema(self):
        if self._is_loaded:
            return defer.success(self)
        d = self._load_schema()
        d.addErrback(self._load_schema_error)
        return d

    # Called when there is an error loading schema
    # remove all triggers already inserted, clears schema state,
    # and prints an error. 
    def _load_schema_error(self, failure):
        def _remove_trigger_cb(res, d, results=[]):
            results.append(res)
            if len(results) == len(self.trigger_map):
                self.trigger_map = {}
                d.errback(failure)
            return
        self.tables = {}
        lg.error("Loading schema failed: %s" %str(failure))
        if len(self.trigger_map):
            d = defer.Deferred()
            for tid in self.trigger_map.values():
                #XXX TODO: removing triggers isn't working, figure out why
                d = defer.succeed('fixme')
                #d = self.conn.remove_trigger(tid) 
                d.addCallback(_remove_trigger_cb, d)
                d.addErrback(_remove_trigger_cb, d)
            return d
        else:
            return failure

    # main state machine for intializing the DBSchema
    # The first three states insert triggers into the NOX_*_TABLES,
    # which in the future will allow us to update the UI if a tables
    # is addeded while we are already running.
    # The second three state (4-6) query each of these tables, building
    # internal data structures for each table representing its schema
    # and indices.  
    def _load_schema(self, res=None, state='add_meta_trigger'): 
        if state == 'add_meta_trigger':
            d = self.conn.put_table_trigger("NOX_SCHEMA_META", 
                    True, self._meta_tbl_trigger_cb)
            d.addCallback(self._handle_trigger_added)
            d.addCallback(self._load_schema, 'add_schema_trigger')
        elif state == 'add_schema_trigger':
            d = self.conn.put_table_trigger("NOX_SCHEMA_TABLE", 
                                    True, self._schema_tbl_trigger_cb)
            d.addCallback(self._handle_trigger_added)
            d.addCallback(self._load_schema, 'add_index_trigger')
        elif state == 'add_index_trigger': 
            d = self.conn.put_table_trigger("NOX_SCHEMA_INDEX", 
                                    True, self._index_tbl_trigger_cb)
            d.addCallback(self._handle_trigger_added)
            d.addCallback(self._load_schema, 'query_meta')
        elif state == 'query_meta':
            d = self._schema_meta_table.get_all_recs_for_query({}, 
                    conn=self.conn)
            d.addCallback(self._handle_meta_recs)
            d.addCallback(self._load_schema, 'query_table')
        elif state == 'query_table':
            d = self._schema_table_table.get_all_recs_for_query({},
                    conn=self.conn)
            d.addCallback(self._handle_table_recs)
            d.addCallback(self._load_schema, 'query_index')
        elif state == 'query_index': 
            d = self._schema_index_table.get_all_recs_for_query({},
                    conn=self.conn)
            d.addCallback(self._handle_index_recs)
            d.addCallback(self._load_schema, 'done')
        elif state == 'done':
            self._is_loaded = True
            return self
        else:
            raise Exception("Invalid state: %s" %state)
        return d

    # called when each trigger is added
    def _handle_trigger_added(self, res):
        tid = res[1]
        self.trigger_map[tid[1]] = tid  # table-name -> table trigger

    # called with all rows from NOX_SCHEMA_META table
    def _handle_meta_recs(self, recs):
        for rec in recs:
            tblname = rec.nox_table
            if rec.nox_type == self.storage_type:
                self.tables[rec.nox_table] = DBTable(tblname)

    # called with all rows from NOX_SCHEMA_TABLE table
    def _handle_table_recs(self, recs):
        for rec in recs:
            tblname = rec.nox_table
            if tblname in self.tables: 
                table = self.tables[tblname]
                table.fields[rec.nox_column] = rec.nox_type

    # called with all rows from NOX_SCHEMA_INDEX table
    def _handle_index_recs(self, recs):
        for rec in recs:
            tblname = rec.nox_table
            indexname = rec.nox_index
            column = rec.nox_column
            if tblname in self.tables: 
                table = self.tables[tblname]
                index = table.indexes.get(indexname, DBIndex())
                table.indexes[indexname] = index
                index.fields.append(column)

    def isLoaded(self):
        return self._is_loaded

    def jsonRepr(self):
        # TBD: stop prettyprinting JSON output here...
        return simplejson.dumps(self, cls=DBSchemaEncoder,
                                sort_keys=True, indent=4)

    def _meta_tbl_trigger_cb(self, id, row, reason):
        # TBD: implement handling of meta table trigger callbacks
        pass

    def _schema_tbl_trigger_cb(self, id, row, reason):
        # TBD: implement handling schema table trigger callbacks
        # TBD: what happens when a row is deleted, don't detect right now.
        pass

    def _index_tbl_trigger_cb(self, id, row, reason):
        # TBD: implement handling of index table trigger callbacks
        pass

    def __str__(self):
        if not self.isLoaded():
            return "The schema is not yet loaded."
        else:
            l = []
            l.append("=" * 78)
            for t in self.tables:
                l.append("%s" % t)
                for f in self.tables[t].fields:
                    l.append("%25s: %d" % (f, self.tables[t].fields[f]))
                l.append("-" * 78)
            return "\n".join(l)


class storage_schema_factory(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self._schemas = {}

    def getInterface(self):
        return str(storage_schema_factory)

    def install(self):
        def _get_connection_cb(res):
            result, conn = res
            if result[0] != Storage.SUCCESS:
                return Failure("Failed to connect to transactional "\
                        "storage: %s (%s)" %(result[0], result[1]))
            self.conn = conn
        def _get_connection_eb(err):
            lg.error("Error initializing storage_schema_factory: %s" %str(err))
            return err
        self.cdb = self.resolve(TransactionalStorage)
        d = defer.Deferred()
#       toggle the two lines below to enable-disable the mem-leak 
#        d.callback(((Storage.SUCCESS,""),None))
        d = self.cdb.get_connection()
        d.addCallback(_get_connection_cb)
        d.addErrback(_get_connection_eb)
        return d

    def get_schema(self, dbname, storage_type):
        """Returns deferred returning DBSchema instance
        """
        def _load_schema_cb(res, schemakey):
            if res is not None:
                self._schemas[schemakey] = res
            return res
        
        schemakey = "%s;%s" %(dbname, str(storage_type))
        if schemakey in self._schemas:
            return defer.succeed(self._schemas[schemakey])
        schema = DBSchema(storage_type, dbname, self.cdb, self.conn)
        d = schema.load_schema()
        d.addCallback(_load_schema_cb, schemakey)
        return d


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return storage_schema_factory(ctxt)

    return Factory()
