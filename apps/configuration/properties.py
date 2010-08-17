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

import copy
import logging
import pickle

from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed
from twisted.python.failure import Failure

from nox.apps.storage import Storage
from nox.apps.storage import TransactionalConnection

log = logging.getLogger('properties')

# For the table definition, see configuration/configuration.cc
TABLE = 'PROPERTIES'
COL_GUID = 'GUID'
COL_SECTION = 'SECTION'
COL_KEY = 'KEY'
COL_VALUE_ORDER = 'VALUE_ORDER'
COL_VALUE_TYPE = 'VALUE_TYPE'
COL_VALUE_INT = 'VALUE_INT'
COL_VALUE_STR = 'VALUE_STR'
COL_VALUE_FLOAT = 'VALUE_FLOAT'

class Properties(dict):
    """\
    A dictionary wrapper around the configuration database PROPERTIES
    table.

    To load the values in from the database, the application must call
    load() method. If the values are to be modified, the application
    must open a transaction (with begin()) before loading and
    modifying values.  Once done, the values have to be committed (or
    rollbacked) to the database.

    Methods returning a deferred (begin(), commit(), rollback(), and
    load()) do not support concurrent access.  Application can issue
    only a single blocking operation at a time for the class.
    
    N.B. Nothing prevents application accessing the PROPERTIES table
         directly, as long as the transactional semantics are obeyed: a
         single transaction should not leave the application-level
         configuration in inconsistent state, ever.
    """

    def __init__(self, storage, section_id, defaults=None):
        """
        Parameters:
        storage    -- transactional storage instance
        section_id -- unique application id (string)
        defaults   -- default key/value pairs (if multiple values, the
                      value can be a list).
        """
        self._in_transaction = False
        self._deleted = []
        
        self._connection = None
        self.__kvp = {}
        self.__kvp_snapshot = {}
        self.__section_id = None
        self.__trigger_id = None
        if defaults:
            self.__defaults = {}
            for key in defaults.keys():
                row = defaults[key]
                try:
                    iter(row)
                except TypeError:
                    row = [ row ]

                self.__defaults[key] = \
                    PropertyList(self, key, [ None ] * len(row))

                for i in xrange(0, len(row)):
                    self.__defaults[key].\
                        __setitem__(i, Property(None, True, row[i]), True)
        else:
            self.__defaults = {}

        self.storage, self._section_id = [ storage, section_id ]

    def __table_changed(self, trigger_id, row):
        # If in the middle of a transaction, can ignore any delayed
        # trigger invocations now.
        if not self._in_transaction:
            c = self.__callbacks
            self.__callbacks = []
            for callback in c:
                try:
                    callback()
                except Exception, e:
                    log.error('Unhandled error while invoking an ' +
                              'application callback: %s' % str(e))
    
    def addCallback(self, configuration_callback):
        """
        Adds a callback to be called at most once the database
        contents have changed for the property section.  Returns a
        callback id to use when removing the callback.

        N.B. The callback is called only once; the application has to
             re-add a callback if it wishes to be informed about
             future changes.
        """
        def construct_callback(connection, application_callback):
            def callback(trigger_id, row, reason):
                application_callback()
            return (connection, callback)

        def put_trigger(result):
            connection, callback = result
            return connection.\
                put_row_trigger(TABLE, { COL_SECTION : self._section_id },
                                callback)

        def return_trigger_id(r):
            result, trigger_id = r
            return trigger_id

        return self.__get_connection().\
            addCallback(construct_callback, configuration_callback).\
            addCallback(put_trigger).\
            addCallback(return_trigger_id)

    def remove_callback(self, callback_id):
        """
        Remove a callback.  Never returns an error.
        """
        def ignore(result_or_failure):
            return None

        return connection.remove_trigger(callback_id).\
            addCallbacks(ignore, ignore)

    def __get_connection(self):
        if self._connection:
            d = Deferred()
            d.callback(self._connection)
            return d
        else:
            def cache_connection(r):
                result, self._connection = r
                return self._connection

            return self.storage.get_connection().\
                addCallback(cache_connection)

    def load(self):
        """
        Updates the properties from the database.  Returns a deferred.
        """
        return self.__refresh(None)

    def __refresh(self, ignore):
        def query(r):
            return self._connection.get(TABLE,
                                        { COL_SECTION : self._section_id } )

        def fetch(r):
            result, cursor = r

            # Mimic deep copy
            self.__kvp = pickle.loads(pickle.dumps(self.__defaults))
            for key in self.__kvp.keys():
                self.__kvp[key].properties = self

            # Note, in the following, using the reactor.callLater
            # instead of chaining deferreds together via addCallback
            # since it seems Twisted deferreds have tendency of
            # resulting in recursion which would make the recursion
            # depth a function of data set size. Sigh.

            def get_rows():
                d = Deferred()
                get_next({}, d)
                return d

            def get_next(rows, d):
                cursor.get_next().\
                    addCallback(process_row, rows, d).\
                    addErrback(lambda failure: d.errback(failure))

            def process_row(r, rows, d):
                result, row = r
                if result[0] == Storage.NO_MORE_ROWS:
                    d.callback(rows)
                    return

                key = row[COL_KEY]
                if not rows.has_key(key):
                    rows[key] = {}

                rows[key][row[COL_VALUE_ORDER]] = \
                    Property(row[COL_GUID], False, 
                             row[col_value_type_to_name(row[COL_VALUE_TYPE])])

                reactor.callLater(0, get_next, rows, d)

            def close(rows):
                for key in rows.keys():
                    row = rows[key]
                    self.__kvp[key] = \
                        PropertyList(self, key, [ None ] * len(row))

                    for i in row.keys():
                        self.__kvp[key].__setitem__(i, row[i], True)

                return cursor.close()

            def finalize(failure):
                self.__kvp = self.__kvp_snapshot
                return cursor.close().addCallback(lambda x: failure)

            return get_rows().\
                addCallback(close).\
                addErrback(finalize)

        return self.__get_connection().\
            addCallback(query).\
            addCallback(fetch).\
            addCallback(lambda x: None)
    
    def begin(self):
        """
        Prepare for modifications.  Loads the latest values from the
        database.  Returns a deferred.
        """
        if self._in_transaction:
            d = Deferred()
            d.callback(None)
            return d

        def begin_(connection):
            self._in_transaction = True
            return connection.begin(TransactionalConnection.EXCLUSIVE)

        def update_snapshot(result):
            self.__kvp_snapshot = self.__kvp

        return self.__get_connection().\
            addCallback(begin_).\
            addCallback(self.__refresh).\
            addCallback(update_snapshot)

    def commit(self):
        """
        Write the changes to the database.  Returns a deferred.
        """
        d = Deferred()

        if not self._in_transaction:
            try:
                raise Exception('call did not precede a begin() call')
            except:
                d.errback(Failure())
                return d

        d.callback(None)

        # Note, in the following, using the reactor.callLater instead
        # of chaining deferreds together via addCallback since it
        # seems Twisted deferreds have tendency of resulting in
        # recursion which would make the recursion depth a function of
        # data set size. Sigh.

        # First, execute any pending row removals
        functions = []
        for p in self._deleted:
            if not p.guid: continue

            def remove_row(p):
                row = { COL_GUID : p.guid }
                return self._connection.remove(TABLE, row)

            functions.append((remove_row, p))

        def remove_rows(ignore):
            d = Deferred()
            
            def remove_next(functions):
                f, arg = functions[0]
                functions.pop(0)
                f(arg).\
                    addCallback(cont, functions).\
                    addErrback(lambda failure: d.errback(failure))

            def cont(ignore=None, functions=None):
                if len(functions) > 0:
                    reactor.callLater(0, remove_next, functions)
                else:
                    d.callback(None)

            cont(None, functions)
            return d

        d.addCallback(remove_rows)

        # Then put/modify any new/modified rows
        functions = []
        for key in self.__kvp.keys():
            functions.append(self.__kvp[key].flush)

        def flush_rows(ignore):
            self._in_transaction = False
            self._deleted = []

            d = Deferred()
            
            def flush_next(functions):
                f = functions[0]
                functions.pop(0)
                f().\
                    addCallback(cont, functions).\
                    addErrback(lambda failure: d.errback(failure))

            def cont(ignore=None, functions=None):
                if len(functions) > 0:
                    reactor.callLater(0, flush_next, functions)
                else:
                    d.callback(None)

            cont(None, functions)
            return d

        d.addCallback(flush_rows)

        def rollback(failure):
            return self._connection.rollback().\
                addCallback(lambda x: failure)

        def commit(ignore):
            return self._connection.commit()

        return d.addCallback(commit).\
            addErrback(rollback)

    def rollback(self):
        """
        Cancel any changes done so far.
        """
        if not self._in_transaction:
            try:
                raise Exception('call did not precede a begin() call')
            except:
                d = Deferred()
                d.errback(Failure())
                return d

        self._in_transaction = False
        self._deleted = []
        self.__kvp = self.__snapshot_kvp

        return self._connection.rollback()

    def get_simple_dict(self):
        res = {} 
        for key, p_list in self.__kvp.items() :
          res[key] = [p.value for p in p_list] 
        return res

    def __getitem__(self, key):
        """
        Return the properties list
        """
        return self.__kvp[key]

    def __setitem__(self, key, value):
        """
        """
        if not self._in_transaction:
            raise Exception('call did not precede a begin() call')

        # Listify the value as needed
        try:
             value.__iter__
        except AttributeError, e:
            value = [ value ]

        # Delete the old row as necessary
        if self.__kvp.has_key(key):
            self.__delitem__(key)

        # Add the new list
        self.__kvp[key] = PropertyList(self, key, value)

    def __delitem__(self, key):
        if not self._in_transaction:
            raise Exception('call did not precede a begin() call')

        for x in self.__kvp[key]:
          if x: # FIXME: why is this getting called with None? 
            self._deleted.append(x)

        del self.__kvp[key]


    def __contains__(self, item):
        return self.__kvp.__contains__(item)

    def __iter__(self):
        return self.__kvp.__iter__()

    def __len__(self):
        return self.__kvp.__len__()

    def keys(self):
        return self.__kvp.keys()

class Property():
    def __init__(self, guid, dirty, value):
        assert(not isinstance(value, Property))

        self.guid, self.dirty, self.value = [ guid, dirty, value ]

    def __str__(self):
        return str(self.value)
        #return 'guid: ' + str(self.guid) + \
        #    '\ndirty: ' + str(self.dirty) + \
        #    '\nvalue: ' + str(self.value)

    def __cmp__(self, other):
        if isinstance(other, Property):
            return cmp(self.value, other.value)
        else:
            return cmp(self.value, other)

class PropertyList():

    def __init__(self, properties, key, values):
        self.__values__ = []
        self._dirty = False
        self.properties = properties
        self.key = key

        if isinstance(values, PropertyList):
            self.__values__ = values.__values__
            for value in self.__values__:
                value.dirty = True
        else:
            for value in values:
                self.__values__.append(Property(None, True, value))

    def flush(self, ignore=None):
        d = Deferred()

        i = -1
        for p in self.__values__:
            i = i + 1

            if not p.dirty:
                continue

            def modify_row(result, p, i, properties, key):
                row = {
                    COL_GUID : p.guid,
                    COL_KEY : key,
                    COL_VALUE_ORDER : i,
                    COL_VALUE_TYPE : col_value_type(p.value),
                    col_value_name(p.value) : p.value
                    }

                return properties._connection.modify(TABLE, row)

            def put_row(result, p, i, properties, key):
                row = {
                    COL_SECTION : properties._section_id,
                    COL_KEY : key,
                    COL_VALUE_ORDER : i,
                    COL_VALUE_TYPE : col_value_type(p.value),
                    col_value_name(p.value) : p.value
                    }

                def set_guid(r, p):
                    result, p.guid = r

                return properties._connection.put(TABLE, row).\
                    addCallback(set_guid, p)

            if not p.guid:
                d.addCallback(put_row, p, i, self.properties, self.key)
            else:
                d.addCallback(modify_row, p, i, self.properties, self.key)

        d.callback(None)
        return d

    def __setstate__(self, state):
        self.__values__, self._dirty, self.key = state

    def __getstate__(self):
        return [
            self.__values__,
            self._dirty,
            self.key 
            ]

    def __len__(self):
      return self.__values__.__len__()

    def __contains__(self, x):
        return self.__values__.__contains__(x)

    def __getitem__(self, i):
        return self.__values__[i].value

    def __setitem__(self, i, value, ignore_transaction_check=False):
        if not ignore_transaction_check and not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        if not isinstance(value, basestring) and \
                not isinstance(value, int) and \
                not isinstance(value, float) and \
                not isinstance(value, Property):
            raise TypeError('Invalid value type: ' + str(value))

        if isinstance(value, Property):
            self.__values__[i] = value
        else:
            try:
                self.__values__[i].dirty, self.__values__[i].value = \
                    [ True, value ]
            except:
                self.__values__[i] = Property(None, True, value)

    def __delitem__(self, i):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        self.properties._deleted.append(self.__values__[i])
        del self.__values__[i]


    def __iter__(self):
        return PropertyListIter(self.__values__.__iter__())

    def append(self, value):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        self.__values__.append(Property(None, True, value))

    def count(self, x):
        c = 0
        for a in self.__values__:
            if x == a.value:
                c = c + 1

        return c

    def extend(self, l):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        for value in l:
            self.append(value)

    def index(self, x):
        i = 0
        for a in self.__values__:
            if x == a.value:
                return i

            i = i + 1

        raise ValueError('x not in the list')

    def insert(self, i, x):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        self.__values__.insert(i, Property(None, True, x))

        for j in xrange(i + 1, len(self.__values__)):
            self.__values__[j].dirty = True

    def pop(self, i=-1):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        x = self.__values__[i]
        self.__delitem__(i)

        for j in xrange(i, len(self.__values__)):
            self.__values__[j].dirty = True

        return x

    def remove(self, x):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        for i in xrange(0, len(self.__values__)):
            if self.__values__[i].value == x:
                return self.pop(i)

        raise ValueError

    def reverse(self):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        for x in self.__values__:
            x.dirty = True

        self.__values__.reverse()

    def sort(self):
        if not self.properties._in_transaction:
            raise Exception('call did not precede a begin() call')

        for x in self.__values__:
            x.dirty = True

        self.__values__.sort()

class PropertyListIter():
    def __init__(self, i):
        self.i = i

    def next(self):
        return self.i.next()

    def __iter__(self):
        return self

def col_value_name(value):
    if isinstance(value, basestring):
        return COL_VALUE_STR
    elif isinstance(value, int):
        return COL_VALUE_INT
    elif isinstance(value, float):
        return COL_VALUE_FLOAT

    raise TypeError

def col_value_type(value):
    if isinstance(value, int):
        return Storage.COLUMN_INT
    elif isinstance(value, basestring):
        return Storage.COLUMN_TEXT
    elif isinstance(value, float):
        return Storage.COLUMN_DOUBLE

    raise TypeError

def col_value_type_to_name(type):
    if type == Storage.COLUMN_INT:
        return COL_VALUE_INT
    elif type == Storage.COLUMN_TEXT:
        return COL_VALUE_STR
    elif type == Storage.COLUMN_DOUBLE:
        return COL_VALUE_FLOAT

    raise TypeError

__all__ = [ 'Properties' ]
