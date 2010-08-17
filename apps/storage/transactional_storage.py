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

__all__ = ['TransactionalStorage', 'TransactionalConnection']

class TransactionalStorage:
    """"Transactional multi key--value pair storage.

    Note all methods return a Twisted deferred object.  In other
    words, while method descriptions say 'Return value', the
    description actually means the value is passed to the deferred's
    callback/errback.
    """

    def get_connection(self):
        """Open a database connection.

        Returns a 2-tuple, containing a Result object 
        and a TransactionalConnection object.
        """
        pass

class TransactionalConnection:
    """
    Connection is in auto-commit mode by default.
    """

    AUTO_COMMIT, DEFERRED, EXCLUSIVE = [0, 1, 2]

    def begin(self, mode):
        """Leave the auto-commit mode.

        After the call the application is required to call the commit()
        or rollback() once done with the transaction.  Otherwise every
        other applications will remain blocked in their access to the
        database.

        The transaction may be opened in three different modes:

        - DEFERRED: no locks are acquired before the first actual
                    operation, and even then, it's first opened for
                    shared access (to support multiple concurrent
                    reads) and moved to EXCLUSIVE as necessary.
        - EXCLUSIVE: the transaction requires full exclusive access to
                     the database right from the beginning. Prefer
                     this, if the semantics of 'DEFERRED' mode are not
                     100% obvious and 'AUTO_COMMIT' is not enough.
        - AUTO_COMMIT: the operation does nothing.
        """
        pass

    def commit(self):
        """Commit all changes since the begin() and return back to the
        auto-commit mode."""
        pass

    def get_transaction_mode(self):
        """Return the mode of the connection. Guaranteed not to block."""
        pass

    def put_row_trigger(self, table, row, trigger):
        """Put a trigger.

        Return a 2-tuple consisting of Result and a trigger id (if
        trigger was succesfully created).

        table      -- table name
        row        -- row to insert the trigger to
        trigger    -- trigger callback.  expected function signature:
                      f(trigger id, row, reason).
        """
        pass

    def put_table_trigger(self, table, sticky, trigger):
        """Put a table trigger.

        Return a 2-tuple consisting of Result and a trigger id (if
        trigger was succesfully created).

        table      -- the table name.
        sticky     -- whether the trigger is sticky (True) or not (False)
        trigger    -- trigger callback.  expected function signature:
                      f(trigger id, row, reason).
        """
        pass

    def remove_trigger(self, trigger_id):
        """Remove a trigger.

        Return Result object.

        Arguments:

        trigger_id -- trigger id of the trigger to remove.
        """
        pass

    def create_table(self, table, columns, indices, version):
        """Create a table.

        Return Result object.

        Arguments:

        table      -- the case sensitive table name.
        columns    -- a dictionary: key = column name, value = a Python
                      string type, long/int type object, float type
                      object or buffer type object. Python type object
                      determines the column type.
        indices    -- a tuple of index definitions.  Each index
                      definition is a 2-tuple: a column name followed
                      by index column names as a tuple.
        version    -- table version number (0 being the initial version).
        """
        pass

    def drop_table(self, table):
        """Drop a table.

        Return Result object.

        Arguments:

        table      -- the case sensitive table name.
        """
        pass

    def get(self, table, query):
        """Open a cursor to retrieve row(s).

        Return a 2-tuple consisting of Result, TransactionalCursor
        objects.

        Arguments:

        table    -- the table name.
        query    -- a dictionary with column names and their corresponding
                    key values.  column names must match to an index.  if
                    no query columns are defined, query matches to every row.
        """
        pass

    def put(self, table, row):
        """Put a new row.

        Return 2-tuple consisting of a Result object and the GUID of
        the new row.

        Arguments:

        table    -- the table name.
        row      -- a dictionary with every column name and their
                    corresponding values.  a new random 20 byte guid
                    will be generated.
        """
        pass

    def modify(self, table, row):
        """Modify an existing row.

        Return 2-tuple consisting of a Result object and a new
        Context object.

        Arguments:

        table    -- the table name.
        row      -- a dictionary with every column name and their corresponding
                    (possibly) modified values.
        """
        pass

    def remove(self, table, row):
        """Remove an existing row.

        Return Result object.

        Arguments:

        context  -- context instance returned by an earlier get() call.
        """
        pass

class TransactionalCursor:
    """
    """
    def get_next(self, context):
        """Get next row.

        Return a 2-tuple consisting of Result, Row (represented by
        dictionaries consisting of key-value pairs) objects. Note, if
        no row can't be found, Result object contains status code of
        NO_MORE_ROWS.
        """
        pass

    def close(self):
        """Release any database resources.  This has to be called by the
        application once done with the cursor to allow other
        applications to access database."""
        pass

def getFactory():
    class Factory():
        def instance(self, context):
            from storage import Storage
            from pytransactional_storage import PyTransactional_storage
            from util import create_method

            class PyTransactionalCursorProxy:
                def __init__(self, impl):
                    self.get_next = create_method(impl.get_next)
                    self.close = create_method(impl.close)

            class PyTransactionalConnectionProxy:
                def __init__(self, impl):
                    self.create_table = create_method(impl.create_table)
                    self.drop_table = create_method(impl.drop_table)

                    def wrap_with_proxy(r):
                        result, cursor = r
                        if result[0] == Storage.SUCCESS:
                            return (result, PyTransactionalCursorProxy(cursor))
                        else:
                            return (result, None)

                    self.get = create_method(impl.get, wrap_with_proxy)
                    self.put = create_method(impl.put)
                    self.modify = create_method(impl.modify)
                    self.remove = create_method(impl.remove)
                    self.begin = create_method(impl.begin)
                    self.commit = create_method(impl.commit)
                    self.rollback = create_method(impl.rollback)
                    self.get_transaction_mode = impl.get_transaction_mode
                    self.put_row_trigger = \
                        create_method(impl.put_row_trigger)
                    self.put_table_trigger = \
                        create_method(impl.put_table_trigger)
                    self.remove_trigger = create_method(impl.remove_trigger)

            class PyTransactionalStorageProxy:
                """A proxy for the C++ based Python bindings to
                avoid instantiating Twisted Failure on the C++ side."""
                def __init__(self, ctxt):
                    self.impl = impl = PyTransactional_storage(ctxt)

                    def wrap_with_proxy(r):
                        result, conn = r
                        if result[0] == Storage.SUCCESS:
                            return (result, PyTransactionalConnectionProxy(conn))
                        else:
                            return (result, None)

                    self.get_connection = create_method(impl.get_connection,
                                                        wrap_with_proxy)

                def configure(self, configuration):
                    self.impl.configure(configuration)

                def install(self):
                    pass

                def getInterface(self):
                    return str(TransactionalStorage)

            return PyTransactionalStorageProxy(context)

    return Factory()
