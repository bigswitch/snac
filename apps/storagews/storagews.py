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

from nox.apps.coreui import coreui
from nox.apps.coreui import webservice
from nox.apps.coreui.authui import UISection, UIResource, Capabilities
from nox.apps.storagews.base_storagews import *
from nox.apps.storagews.storage_schema import storage_schema_factory
from nox.apps.storage.storage import Storage, StorageException

from twisted.python.failure import Failure

lg = logging.getLogger('storagews')

class StorageDbOp(BaseStorageDbOp):
    """Manager for callbacks from DB."""

    def __init__(self, db, schema, request):
        BaseStorageDbOp.__init__(self, db, schema, request)

    def doGet(self, table_name, query=None):
        self.op = "get"
        self.table_name = table_name
        if query == None:
            self._query = {}   # Get everything
        else:
            self._query = query
        self._d = self.db.get(table_name, self._query)
        self._d.addCallback(self._handle_get_row)
        self._d.addErrback(self._handle_err)

    def _write_query_header(self):
        if self._sent_header == False:
            self.request.write('{"table_name" : "' + self.table_name + '"')
            self.request.write(', "identifier" : "GUID", "items" : [')
            self._sent_header = True

    def _handle_get_row(self, res):
        result, ctxt, row = res
        if (result[0] == Storage.NO_MORE_ROWS
            or result[0] == Storage.SUCCESS and len(row) == 0):
            # TBD: Remove second clause above when storage API is fixed
            # TBD: so that it doesn't return an empty row to a get when
            # TBD: nothing matches the query.
            self._d = None
            if (self._numResults == 0
                and len(self._query) == 1
                and self._query.has_key("GUID")):
                notFound(self.request,
                        "Table %s does not have row with GUID: %s" 
                        %(self.table_name,
                        self._query["GUID"][1].encode("hex")))
            else:
                self._write_query_header()
                self.request.write("]}")
                self.request.finish()
        elif result[0] == Storage.SUCCESS:
            self._numResults += 1
            self._write_query_header()
            ui_guid = (row["GUID"][1]).encode("hex")
            row["GUID"] = ui_guid
            row["GUID.link"] = u"/ws.v1/storage/" + self.schema.dbname
            row["GUID.link"] += u"/table/" + self.table_name + u"/" + ui_guid
            self.request.write(simplejson.dumps(row))
            self.request.write(",")
            self._d = self.db.get_next(ctxt)
            self._d.addCallback(self._handle_get_row)
            self._d.addErrback(self._handle_err)
        else:
            lg.error("Unknown success result code from database ")
            webservice.internalError(self.request, "Unknown success result "\
                    "code from database")

    def doRemoveRow(self, table_name, guid):
        self.op = "remove row"
        self.table_name = table_name
        self._guid = guid
        self._query = { "GUID" : guid }
        self._d = self.db.get(table_name, self._query)
        self._d.addCallback(self._handle_remove_get_row)
        self._d.addErrback(self._handle_err)

    def _handle_remove_get_row(self, res):
        result, context, row = res
        if (result[0] == Storage.NO_MORE_ROWS
            or result[0] == Storage.SUCCESS and len(row) == 0):
            # TBD: Remove second clause above when storage API is fixed
            # TBD: so that it doesn't return an empty row to a get when
            # TBD: nothing matches the query.
            self._d = None
            if self._numResults == 0:
                notFound(self.request,
                         "Table %s does not have row with GUID: %s"
                         % (self.table_name,
                            self._query["GUID"][1].encode("hex")))
            elif self._numResults == 1:
                if self._remove_failed:
                    msg = "Remove success callback called with unexpected "\
                            "results"
                    lg.error(msg)
                    webservice.internalError(request, msg)
                else:
                    # TBD: setting response code here is causing errors deep
                    # TBD: in twisted.  Need to figure out why.
                    #self.request.setResponseCode("204")
                    self.request.finish() # No body for 204 response
            else:
                msg = "Multiple rows returned (unexpectedly) by the "\
                        "database and possibly removed."
                lg.error(msg)
                webservice.internalError(request, msg)
        elif result[0] == Storage.SUCCESS:
            if self._numResults < 1:
                # TBD: remove this check after db fix for issue with
                # TBD: removing all rows when only one is selected.
                self._numResults += 1
                d = self.db.remove(context)
                d.addCallback(self._handle_remove)
                self._d = self.db.get_next(context)
                self._d.addCallback(self._handle_remove_get_row)
                self._d.addErrback(self._handle_err)
            else:
                result = ((Storage.NO_MORE_ROWS, "Force DONE"), None, {})
                self._handle_remove_get_row(result)
        else:
            lg.errror("Unknown success result code in code from database")
            webservice.internalError(self.request, "Unknown success result "\
                    "code from database")

    def _handle_remove(self, res):
        result = res
        if (result[0] != Storage.SUCCESS):
            self._remove_failed = True

    def doModifyRow(self, table_name, row):
        self.op = "modify row"
        self.table_name = table_name
        self._row = row
        # Strip out link entries added by web service
        for k in self._row.keys():
            if k.endswith(".link"):
                del(self._row[k])
        self._query = { "GUID": self._row["GUID"] }
        self._d = self.db.get(table_name, self._query)
        self._d.addCallback(self._handle_modify_get_row)
        self._d.addErrback(self._handle_err)

    def _handle_modify_get_row(self, res):
        result, self.context, old_row = res
        if (result[0] == Storage.NO_MORE_ROWS
            or result[0] == Storage.SUCCESS and len(old_row) == 0):
            # TBD: Remove second clause above when storage API is fixed
            # TBD: so that it doesn't return an empty row to a get when
            # TBD: nothing matches the query.
            self._d = None
            if self._numResults == 0:
                notFound(self.request,
                         "Table %s does not have row with GUID: %s"
                         % (self.table_name,
                            self._query["GUID"][1].encode("hex")))
            elif self._numResults == 1:
                if self._modify_failed:
                    msg = "Modify success callback called with unexpected "\
                          "results"
                    lg.error(msg)
                    webservice.internalError(self.request, msg)
                else:
                    # TBD: setting response code here is causing errors deep
                    # TBD: in twisted.  Need to figure out why.
                    #self.request.setResponseCode("204")
                    self.request.finish() # No body for 204 response
            else:
                msg = "Multiple rows returned (unexpectedly) by the database "\
                      "and possibly modified."
                lg.error(msg)
                webservice.internalError(self.request, msg)
        elif result[0] == Storage.SUCCESS:
            self._numResults += 1
            d = self.db.modify(self.context, self._row)
            d.addCallback(self._handle_modify)
            self._d = self.db.get_next(self.context)
            self._d.addCallback(self._handle_modify_get_row)
            self._d.addErrback(self._handle_err)
        else:
            lg.error("Unknown success result code in ")
            webservice.internalError(self.request, "Unknown success result "\
                    "code from database")

    def _handle_modify(self, res):
        result, self.context = res
        if (result[0] != Storage.SUCCESS):
            self._modify_failed = True


class storagews(Component, base_storagews):
    DB_NAME = 'ndb'

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None

    def install(self):
        def _get_schema_cb(schema):
            if schema is None:
                lg.error("Failed to obtain schema for '%s'" %self.DB_NAME)
                return Failure("Failed to obtain schema for '%s'"
                        %self.DB_NAME)
            self.register_web_services(self.ws, self.storage, schema,
                    StorageDbOp)
            return None
        self.ss = self.resolve(str(storage_schema_factory))
        self.ws = self.resolve(str(webservice.webservice))
        self.storage = self.resolve(str(Storage))
        d = self.ss.get_schema(self.DB_NAME, Storage.NONPERSISTENT)
        d.addCallback(_get_schema_cb)
        return d

    def getInterface(self):
        return str(storagews)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return storagews(ctxt)

    return Factory()
