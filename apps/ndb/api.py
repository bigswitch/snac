# Network database features are:
#
# - Support for multiple tables, each consisting of arbitrary # of
#   columns. Each column can be used as a key while retrieving rows.
#
# - Supported operations are get(key1, key2, ...), and put(key1=val1,
#   key2=val, ...).
# 
# - Put() and get() operations can be grouped into transactions. In a
#   single transaction, put's and get()s can't mixed though.

__all__ = ["API", "GetOp", "PutOp", "DependencyError", "SchemaError"]

###############################################################################
# Python types supported in Get and Put ops and their mappings to
# SQLite:
#
# - None     => SQL NULL
# - int      => SQL INTEGER
# - long     => SQL INTEGER
# - float    => SQL REAL
# - str      => SQL TEXT
# - unicode  => SQL TEXT
# - buffer   => SQL BLOB
#
###############################################################################

###############################################################################
# Note: Classes should NOT have log objects inside to maintain them
#       'pickable'.
###############################################################################

class DependencyError(Exception):
    """
    Dependency checks failed exception.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class SchemaError(Exception):
    """
    Schema definition exception.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class GetOp:
    """
    Get operation to retrieve database row(s).
    """

    def __init__(self, table, columnsvalues, callback=None):
        """
        Instantiate a get(table, column1 = key1, column2 = key2, ...) 
        operation.

        Arguments:
        table         -- the table name.
        columnsvalues -- a dictionary with column names and their corresponding
                         key values.
        """
        self.table = table
        self.columnsvalues = columnsvalues
        self.results = None
        self.callback = callback

    def __str__(self):
        ret = "get(" + self.table + (", ".join(map(lambda kv: str(kv[0]) + ": " + 
                                                   str(kv[1]), self.columnsvalues.items()))) + ")"
        ret += ", results: ["
        if self.results:
            ret += ", ".join(map(lambda r: str(r), self.results))            
        ret += "]"
        return ret

class PutOp:
    """
    Put operation to insert or replace a database row.
    """
    def __init__(self, table, columnsvalues, replace_columnsvalues=None):
        """
        Constructs a put() operation to insert a single row.

        table         -- the table name.
        columnsvalues -- a dictionary with all column names and their corresponding
                         key values.
        replace       -- the row(s) to replace.
        """
        self.table = table
        self.columnsvalues = columnsvalues
        self.replace_columnsvalues = replace_columnsvalues

    def __str__(self):
        ret = "put(" + self.table + "; "
        if self.columnsvalues:
            ret += (", ".join(map(lambda kv: str(kv[0]) + ": " + 
                                  str(kv[1]), self.columnsvalues.items()))) + "; "
        else:
            ret += "[]; "
        if self.replace_columnsvalues:
            ret += (", ".join(map(lambda kv: str(kv[0]) + ": " + 
                                  str(kv[1]), self.replace_columnsvalues.items())))
        else:
            ret += "[]"

        ret += ")"
        return ret

class API:
    """
    Abstract base class API for handlers to use and for API
    implementations (cache, master) to implement.
    """

    def create_table(self, table, columns, indices=[]):
        """
        Creates a table. Raises a SchemaError if table exists or
        columns/indices are invalid. Note, no constrains are
        supported.
        
        Arguments:

        table        -- table name.
        columns      -- a dictionary, key = column name, value = any string, 
                        long/int, float or buffer object. (Value type determines
                        the column type for the database.)
        indices      -- a list of column name tuples, each defining an index.
        """
        raise NotImplementedError

    def drop_table(self, table):
        """
        Drops a table. Safe to execute even if the table wouldn't exist.
        
        Arguments:

        table        -- table name.
        """
        raise NotImplementedError

    def execute(self, ops, dependencies=[]):
        """
        Executes a transaction.

        Arguments:

        ops          -- the operations to execute as a list. 
                        It's all either PutOps or GetOps.
        dependencies -- any GetOps (with results in them) the
                        operations depend on.
        """
        raise NotImplementedError

    # Static convenience methods follow.

    @staticmethod
    def get_key(table, columnvalues):
        """
        Compute a key (to access a dictionary use) out of table and the
        query criterion.
        """
        return (table, ) + tuple(columnvalues)
