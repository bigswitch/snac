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
import simplejson
import types

from nox.lib.core import *

from nox.ext.apps.coreui import coreui
from nox.webapps.webservice import webservice
from nox.ext.apps.storage.transactional_storage import TransactionalStorage
from nox.ext.apps.coreui.authui import UISection, UIResource, Capabilities
from nox.ext.apps.storage import StorageTableUtil
from nox.netapps.storage.storage import Storage, StorageException
from nox.ext.apps.storagews.base_storagews import *
from nox.ext.apps.storagews.storage_schema import storage_schema_factory

from twisted.python.failure import Failure
from twisted.internet import defer

lg = logging.getLogger('transactionalstoragews')

class TransactionalStorageDbOp(BaseStorageDbOp):
    """Manager for callbacks from DB."""

    def __init__(self, cdb, schema, request):
        BaseStorageDbOp.__init__(self, cdb, schema, request)

    def doGet(self, table_name, query=None):
        def _process_storage_rows(rows):
            if (len(rows) == 0 and len(query) == 1
                    and query.has_key("GUID")):
                notFound(self.request,
                        "Table %s does not have row with GUID: %s" 
                        %(self.table_name,
                        self._query["GUID"][1].encode("hex")))
            else:
                self.request.write('{"table_name" : "' + table_name + '"')
                self.request.write(', "identifier" : "GUID", "items" : [')
                i = 0
                for row in rows:
                    ui_guid = (row["GUID"][1]).encode("hex")
                    row["GUID"] = ui_guid
                    row["GUID.link"] = u"/ws.v1/storage/%s/table/%s/%s" \
                            %(self.schema.dbname, table_name, ui_guid)
                    self.request.write(simplejson.dumps(row))
                    i += 1
                    if i < len(rows):
                        self.request.write(",")
                self.request.write("]}")
                self.request.finish()
            return
        query = query or {}
        d = StorageTableUtil.get_all_rows_for_query(self.db, table_name, query)
        d.addCallback(_process_storage_rows)
        return d

    def doRemoveRow(self, table_name, guid):
        def _get_guid_cb(rows):
            if len(rows) == 0:
                notFound(self.request,
                         "Table %s does not have row with GUID: %s"
                         % (self.table_name,
                            self._query["GUID"][1].encode("hex")))
            elif len(rows) > 1:
                msg = "Multiple rows returned (unexpectedly) by the "\
                        "database and possibly removed."
                lg.error(msg)
                webservice.internalError(request, msg)
            else:
                d = StorageTableUtil.get_connection_if_none(self.db)
                d.addCallback(_do_remove, rows[0])
                return d

        def _do_remove(conn, row):
            d = conn.remove(table_name, row)
            d.addCallback(_remove_cb)
            return d

        def _remove_cb(res):
            if res[0] != Storage.SUCCESS:
                msg = "Remove failed: %s (%s)" %(res[0], res[1])
                lg.error(msg)
                webservice.internalError(msg)

        query = { "GUID" : guid }
        d = StorageTableUtil.get_all_rows_for_query(self.db, table_name, query)
        d.addCallback(_get_guid_cb)
        d.addErrback(self._handle_err)
        return d

    def doModifyRow(self, table_name, row):
        def _do_modify(conn):
            d = conn.modify(table_name, row)
            d.addCallback(_modify_cb)
            return d

        def _modify_cb(res):
            if res[0] == Storage.SUCCESS:
                # TBD: setting response code here is causing errors deep
                # TBD: in twisted.  Need to figure out why.
                #self.request.setResponseCode("204")
                self.request.finish() # No body for 204 response
                return
            else:
                msg = "Modify success callback called with unexpected "\
                      "results"
                lg.error(msg)
                webservice.internalError(self.request, msg)

        # Strip out link entries added by web service
        for k in row.keys():
            if k.endswith(".link"):
                del(row[k])

        d = StorageTableUtil.get_connection_if_none(self.db)
        d.addCallback(_do_modify)
        d.addErrback(self._handle_err)
        return d


class storagews(Component, base_storagews):
    DB_NAME = 'cdb'

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None

    def install(self):
        def _get_schema_cb(schema):
            if schema is None:
                lg.error("Failed to obtain schema for '%s'" %self.DB_NAME)
                return Failure("Failed to obtain schema for '%s'"
                        %self.DB_NAME)
            self.register_web_services(self.ws, self.cdb, schema,
                    TransactionalStorageDbOp)
            return None
        self.ss = self.resolve(str(storage_schema_factory))
        self.ws = self.resolve(str(webservice.webservice))
        self.cdb = self.resolve(str(TransactionalStorage))
        d = self.ss.get_schema(self.DB_NAME, Storage.PERSISTENT)
        d.addCallback(_get_schema_cb)
        return d

    def getInterface(self):
        return str(storagews)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return storagews(ctxt)

    return Factory()
