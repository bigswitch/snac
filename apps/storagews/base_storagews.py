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
from nox.ext.apps.coreui.authui import UISection, UIResource
from nox.webapps.webserver.webauth import Capabilities
from nox.ext.apps.storagews.storage_schema import storage_schema_factory
from nox.netapps.storage.storage import Storage, StorageException

lg = logging.getLogger('base_storagews')

class BaseStorageDbOp:
    """Manager for callbacks from DB."""

    def __init__(self, db, schema, request):
        self.db = db
        self.schema = schema
        self.request = request
        self.op = "unspecified"
        self.table_name = None
        self._query = None
        self._guid = None
        self._row = None
        self._numResults = 0
        self._sent_header = False
        self._remove_failed = False
        self._modify_failed = False
        self._context = None

    def doGet(self, table_name, query=None):
        raise NotImplementedError("doGet must be iimplemented in subclass")

    def _write_query_header(self):
        if self._sent_header == False:
            self.request.write("{ 'table_name' : '" + self.table_name + "'")
            self.request.write(", 'identifier' : 'GUID', 'items' : [")
            self._sent_header = True

    def _handle_err(self, failure):
        if isinstance(failure.value, StorageException):
            if failure.value.code == Storage.NONEXISTING_TABLE:
                notFound(self.request, "Table '%s' does not exist." 
                        %self.table_name)
                return
            else:
                webservice.internalError(self.request,
                        "Database %s operation failed: %s" %(self.op, 
                        str(failure.value)))
                return
        failure.raiseException()

    # put methods are identical between transactional and
    # non-transactional storage
    def doPut(self, table_name, row):
        self.op = "put"
        self.table_name = table_name
        self._row = row
        self._d = self.schema.db.put(table_name, row)
        self._d.addCallback(self._handle_put)
        self._d.addErrback(self._handle_err)

    def _handle_put(self, res):
        result, guid = res
        if (result[0] != Storage.SUCCESS):
            msg = "Unexpected return code (%d) from Storage API put call."\
                    % result[0]
            webservice.internalError(request, msg)
            return
        ui_guid = guid[1].encode("hex")
        self._row["GUID"] = ui_guid
        self._row["GUID.link"] = u"/ws.v1/storage/" + self.schema.dbname
        self._row["GUID.link"] += u"/table/" + self.table_name + u"/" + ui_guid
        self.request.setResponseCode(201, "Created")
        #self.request.setHeader("Location", self._row["GUID.link"])
        self._write_query_header()
        self.request.write(simplejson.dumps(self._row))
        self.request.write("]}")
        self.request.finish()

    def doRemoveRow(self, table_name, guid):
        raise NotImplementedError("doRemoveRow must be iimplemented in "\
                "subclass")

    def doModifyRow(self, table_name, row):
        raise NotImplementedError("doModifyRow must be iimplemented in "\
                "subclass")

class WSPathSchemaDBName(webservice.WSPathComponent):
    def __init__(self, schema):
        webservice.WSPathComponent.__init__(self)
        self._schema = schema 

    def __str__(self):
        return self._schema.dbname

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI")
        if pc == self._schema.dbname:
            return webservice.WSPathExtractResult(value=self._schema)
        return webservice.WSPathExtractResult(error="'%s' != '%s'"
                %(pc, self._schema.dbname))

class WSPathNonexistentDBTable(webservice.WSPathComponent):
    def __init__(self, schema):
        webservice.WSPathComponent.__init__(self)
        self._schema = schema 

    def __str__(self):
        return "<non-existent db table name>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI")
        schema = data[self._schema.dbname]
        if schema.tables.has_key(pc):
            e = "Database table '%s' already exists." % pc
            return webservice.WSPathExtractResult(error=e)
        if pc == "":
            e = "The database table name '%s' is not valid." % pc
            return webservice.WSPathExtractResult(error=e)
        # TBD: further verify db name is valid according to Storage
        return webservice.WSPathExtractResult(value=pc)


class WSPathExistingDBTable(webservice.WSPathComponent):
    def __init__(self, schema):
        webservice.WSPathComponent.__init__(self)
        self._schema = schema 

    def __str__(self):
        return "<db table name>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI")
        schema = data[self._schema.dbname]
        if schema.tables.has_key(pc):
            return webservice.WSPathExtractResult(value=pc)
        e = "Database table '%s' does not exist." % pc
        return webservice.WSPathExtractResult(error=e)

class WSPathValidDBGUID(webservice.WSPathComponent):
    def __init__(self):
        webservice.WSPathComponent.__init__(self)

    def __str__(self):
        return "<db row guid>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI")
        e = "Invalid db row GUID value."
        if len(pc) != 40:
            return webservice.WSPathExtractResult(error=e)
        try:
            guid = pc.decode("hex")
        except TypeError:
            return webservice.WSPathExtractResult(error=e)
        return webservice.WSPathExtractResult(value=("GUID", guid))


class base_storagews():

    def __init__(self):
        pass

    def register_web_services(self, web_service, db, dbschema, storage_op_cls):
        self.db = db
        self.dbschema = dbschema
        self.op_cls = storage_op_cls
        v1 = web_service.get_version("1")
        reg = v1.register_request

        basepath = ( webservice.WSPathStaticString("storage"),
                     WSPathSchemaDBName(self.dbschema) )

        path = basepath + ( webservice.WSPathStaticString("schema"), )
        reg(self._get_schema,"GET", path,
            """Get the schema for the given database instance.""")

        basepath += ( webservice.WSPathStaticString("table"), )

        path = basepath + ( WSPathNonexistentDBTable(self.dbschema), )
        reg(self._add_table,"PUT", path,
            """Create a new table for the given database.""")

        basepath += ( WSPathExistingDBTable(self.dbschema), )
        reg(self._modify_table, "PUT", basepath,
            """Modify an existing table in the given database.""")
        reg(self._delete_table, "DELETE", basepath,
            """Delete an existing table in the given database.""")
        reg(self._get_all_table_rows, "GET", basepath,
            """Get all rows of an existing table in the given database.""")
        reg(self._add_table_row, "POST", basepath,
            """Add a new row to the given table and database.""")

        path = basepath + ( webservice.WSPathStaticString("search"), )
        reg(self._search_table,"GET", path,
            """Search for matching rows of an existing table in the
            given database.""")

        basepath += ( WSPathValidDBGUID(), )
        reg(self._get_table_row, "GET", basepath,
            """Get a specific row in the given table and database.""""")
        reg(self._update_table_row, "PUT", basepath,
            """Change an existing row in the given table and database.""")
        reg(self._delete_table_row, "DELETE", basepath,
            """Delete an existing row in the given table and database.""")


    @staticmethod
    def _strip_unicode_in_dict(d):
        for k in d.keys():
            if type(k) == types.UnicodeType:
                v = d[k]
                del(d[k])
                k = k.encode('utf-8')
                d[k] = v
            if type(d[k]) == types.UnicodeType:
                d[k] = d[k].encode('utf-8')
        return d

    @staticmethod
    def _errors_in_row(schema, table_name, row, noGUID=False):
        errors = []
        for f in schema.tables[table_name].fields:
            if noGUID and f == "GUID":
                if f in row:
                    errors.append("Contains the 'GUID' field which is "\
                            "server-assigned.")
            else:
                if f not in row:
                    errors.append("Is missing the '%s' field." % f)
                else:
                    fld_type = schema.tables[table_name].fields[f]
                    if fld_type == 0:    # INT
                        try:
                            row[f] = long(row[f])
                        except ValueError:
                            errors.append("Field '%s' has invalid type. It "\
                                    "should be of type INT." % f)
                    elif fld_type == 1:  # TEXT
                        try:
                            row[f] = str(row[f])
                        except ValueError:
                            errors.append("Field '%s' has invalid type. It "\
                                    "should be of type TEXT." % f)
                    elif fld_type == 2:  # DOUBLE
                        try:
                            row[f] = float(row[f])
                        except ValueError:
                            errors.append("Field '%s' has invalid type. It "\
                                    "should be of type DOUBLE." % f)
                    elif fld_type == 3:  # GUID
                        try:
                            row[f] = ( "GUID", row[f].decode("hex") )
                        except (ValueError, AttributeError):
                            errors.append("Field '%s' has invalid type. It "\
                                    "should be of type GUID." % f)
                    else:
                        lg.error("Unknown field type.")
        return errors

    def _get_schema(self, request, arg):
        schema = arg[self.dbschema.dbname]
        if not schema.isLoaded():
            return webservice.internalError(request, "Schema has not been "\
                    "loaded yet.")
        return schema.jsonRepr()

    def _add_table(self, request, arg):
        e = "The handler for this request has not been implemented yet."
        return webservice.internalError(request, e)

    def _modify_table(self, request, arg):
        e = "The handler for this request has not been implemented yet."
        return webservice.internalError(request, e)

    def _delete_table(self, request, arg):
        e = "The handler for this request has not been implemented yet."
        return webservice.internalError(request, e)

    def _get_all_table_rows(self, request, arg):
        schema = arg[self.dbschema.dbname]
        table_name = arg["<db table name>"]
        q = self.op_cls(self.db, schema, request)
        q.doGet(table_name)
        return webservice.NOT_DONE_YET

    def _search_table(self, request, arg):
        e = "The handler for this request has not been implemented yet."
        return webservice.internalError(request, e)

    def _get_table_row(self, request, arg):
        schema = arg[self.dbschema.dbname]
        table_name = arg["<db table name>"]
        qd = { "GUID" : arg["<db row guid>"] }
        q = self.op_cls(self.db, schema, request)
        q.doGet(table_name, qd)
        return webservice.NOT_DONE_YET

    def _add_table_row(self, request, arg):
        schema = arg[self.dbschema.dbname]
        table_name = arg["<db table name>"]
        row = webservice.json_parse_message_body(request)
        if row == None:
            return webservice.NOT_DONE_YET
        e = base_storagews._errors_in_row(schema, table_name, row, noGUID=True)
        if len(e) != 0:
            errmsg =  "Errors in message body:" + "\n    - ".join(e)
            return webservice.badRequest(request, errmsg)
        p = self.op_cls(self.db, schema, request)
        p.doPut(table_name, row)
        return webservice.NOT_DONE_YET

    def _update_table_row(self, request, arg):
        schema = arg[self.dbschema.dbname]
        table_name = arg["<db table name>"]
        guid = arg["<db row guid>"]
        row = webservice.json_parse_message_body(request)
        if row == None:
            return webservice.NOT_DONE_YET
        e = base_storagews._errors_in_row(schema, table_name, row, 
                noGUID=False)
        if guid != row["GUID"]:
            e.append("GUID in message body must match GUID in URI.")
        if len(e) != 0:
            errmsg =  "The following error(s) were found:\n\n    - "
            errmsg += "\n    - ".join(e)
            return webservice.badRequest(request, errmsg)
        # TBD: remove this hack when storage API supports python
        # TBD: unicode strings.
        base_storagews._strip_unicode_in_dict(row)
        p = self.op_cls(self.db, schema, request)
        p.doModifyRow(table_name, row)
        return webservice.NOT_DONE_YET

    def _delete_table_row(self, request, arg):
        schema = arg[self.dbschema.dbname]
        table_name = arg["<db table name>"]
        guid = arg["<db row guid>"]
        d = self.op_cls(self.db, schema, request)
        d.doRemoveRow(table_name, guid)
        return webservice.NOT_DONE_YET


