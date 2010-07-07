#!/usr/bin/python

import time
import MySQLdb

###############################################################################
# NOX defaults for database connectivity.
###############################################################################
DB_DB='nox_dwh'
DB_HOST='localhost'
DB_USER='nox_dwh'
DB_PASSWD='nox_dwh'

###############################################################################
# Table definitions
#
# Please keep these in sync with the table definitions in the
# applications and the DWH schema.
#
###############################################################################
tables = {}
tables['FLOW'] = {'columns': ['ID', 'CREATED_DT', 'DELETED_DT', 'DP_ID',
                              'PORT_ID', 'ETH_VLAN', 'ETH_TYPE', 
                              'SOURCE_MAC', 'DESTINATION_MAC', 
                              'SOURCE_IP', 'SOURCE_IP_MASK',
                              'DESTINATION_IP', 'DESTINATION_IP_MASK',
                              'PROTOCOL_ID', 'SOURCE_PORT', 'DESTINATION_PORT',
                              'DURATION', 'PACKET_COUNT', 'BYTE_COUNT'],
                  'keys': ['DP_ID', 'PORT_ID', 'ETH_VLAN', 'ETH_TYPE', 
                           'SOURCE_MAC', 'DESTINATION_MAC',
                           'SOURCE_IP', 'DESTINATION_IP', 'PROTOCOL_ID',
                           'SOURCE_PORT', 'DESTINATION_PORT']}
tables['FLOW_SETUP'] = {'columns' : ['ID', 'CREATED_DT' 'DELETED_DT', 'DP_ID',
                                     'PORT_ID', 'REASON', 'BUFFER', 
                                     'TOTAL_LEN'],
                        'keys' : ['DP_ID', 'PORT_ID', 'REASON', 'BUFFER']}
tables['LLDP_LINKS'] = {'columns': ['ID', 'CREATED_DT', 'DELETED_DT', 
                                    'DP1', 'PORT1', 'DP2', 'PORT2'],
                        'keys': ['DP1', 'PORT1', 'DP2', 'PORT2']}
tables['LEARNING'] = {'columns': ['ID', 'CREATED_DT', 'DELETED_DT',
                                  'SWITCH_ID', 'MAC', 'PORT_ID'],
                  'keys': ['SWITCH_ID', 'MAC', 'PORT_ID']}
tables['PF'] = {'columns': ['ID', 'CREATED_DT', 'DELETED_DT',
                            'MAC', 'IP', 'P0F_OS',
                            'P0F_DESCR', 'P0F_WSS_MISS',
                            'P0F_DF_MISS', 'P0F_ACC',
                            'PF_OS'],
                'keys': ['MAC', 'IP']}

def nonmissing_min(a, b):
    if a == None:
        return b
    elif b == None:
        return a
    else:
        return min(a,b)

def nonmissing_max(a, b):
    if a == None:
        return b
    elif b == None:
        return a
    else:
        return max(a,b)

class DWHConnection:
    """
    A connection object to NOX data warehouse database.
    """
    def __init__(self, host, user, passwd, db):
        self.conn = MySQLdb.connect(host, user, passwd, db)
        self.conn.autocommit(True)
        
    def get_prev_snapshot_id(self, table, date):
        return "SELECT MAX(ID) FROM SNAPSHOT WHERE CREATED_DT <= %s " \
            "AND TABLE_ID = (%s)" % (date, self.get_table_id(table))

    def get_prev_snapshot_ts(self, table, date):
        return "SELECT CREATED_DT FROM SNAPSHOT WHERE ID = (%s)" \
            % self.get_prev_snapshot_id(table, date)
            
    def get_table_id(self, table):
        return "SELECT ID FROM LOAD_TABLE WHERE NAME = '%s'" % table

    def query_snapshot(self, table, date):
        """
        Retrieves the latest snapshot for the given table before or at
        given date.
        """
        fmt = {'columns' : ", ".join(map(lambda x: "query_snapshotf." + x, 
                                         tables[table]['columns'])),
               'prev_snapshot_ts' : self.get_prev_snapshot_ts(table, date),
               'table_id' : self.get_table_id(table),
               'date' : date,
               'table' : table}
        return "SELECT %(columns)s FROM %(table)s_SNAPSHOT query_snapshots, "\
            "%(table)s query_snapshotf WHERE query_snapshots.SNAPSHOT_ID ="\
            "(SELECT MAX(ID) FROM SNAPSHOT WHERE TABLE_ID = (%(table_id)s) AND "\
            "CREATED_DT <= (%(prev_snapshot_ts)s)) AND "\
            "query_snapshots.%(table)s_ID = query_snapshotf.ID AND "\
            "query_snapshotf.DELETED_DT > %(date)s" % fmt;

    def query_latest(self, table, date):
        """
        Retrieves the latest state before given date, but past
        snapshot given date.
        """
        fmt = {'columns' : ", ".join(map(lambda x: "query_latest." + x, 
                                        tables[table]['columns'])),
               'prev_snapshot_ts' : self.get_prev_snapshot_ts(table, date),
               'date' : date,
               'table' : table}
        return "SELECT %(columns)s FROM %(table)s query_latest WHERE "\
            "query_latest.CREATED_DT > (%(prev_snapshot_ts)s) AND "\
            "query_latest.CREATED_DT <= %(date)s AND "\
            "query_latest.DELETED_DT > %(date)s" % fmt

    def query(self, table, date):
        return "(" + self.query_snapshot(table, date) + ") UNION (" +\
            self.query_latest(table, date) + ")"

    def execute(self, q):
        print q
        cursor = self.conn.cursor()
        cursor.execute(q)
        return cursor

    def convert_time(self, t):
        return long(t * 1000000)

    # Executes a query for the contents of 'table' at 'date' and
    # returns the results in a form similar to that returned by the
    # NDB; that is, a list of rows, in which each row is a dictionary
    # mapping from column name to value.
    def fetchLikeNDB(self, table, date):
        columns = tables[table]['columns']
        cursor = self.execute(self.query(table, date) + " ORDER BY CREATED_DT")
        results = []
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            dict = {}
            for i in range(len(columns)):
                dict[columns[i]] = row[i]
            results.append(dict)
        cursor.close()
        return results

    # Returns the earliest date of any change in any of the 'tables',
    # or None if all of the 'tables' are empty.
    def get_earliest(self, tables):
        earliest = None
        for table in tables:
            earliest = nonmissing_min(earliest, self.execute_singleton(
                    "SELECT MIN(CREATED_DT) FROM %s" % table))
        return earliest

    # Returns the latest date of any change in any of the 'tables', or
    # None if all of the 'tables' are empty.
    def get_latest(self, tables):
        latest = None
        for table in tables:
            latest = nonmissing_max(latest, self.execute_singleton(
                    "SELECT MAX(CREATED_DT) FROM %s" % table))
            latest = nonmissing_max(latest, self.execute_singleton(
                    "SELECT MAX(DELETED_DT) FROM %s "
                    "WHERE DELETED_DT != 9223372036854775807" % table))
        return latest

    # Runs 'query', which should return a single row with a single column.
    # Returns the value, if successful, None otherwise.
    def execute_singleton(self, query):
        cursor = self.execute(query)
        row = cursor.fetchone()
        cursor.close()
        if row != None and row[0] != None:
            return row[0]
        else:
            return None

    # Returns the latest date before 'date' on which any of 'tables' changes,
    # or None if none of the 'tables' ever changes before 'date'.
    def prev_change(self, tables, date):
        prev = None
        for table in tables:
            prev = nonmissing_max(prev, self.execute_singleton(
                    "SELECT MAX(CREATED_DT) FROM %s WHERE CREATED_DT < %d"
                    % (table, date)))
            prev = nonmissing_max(prev, self.execute_singleton(
                    "SELECT MAX(DELETED_DT) FROM %s WHERE DELETED_DT < %d"
                    % (table, date)))
        return prev

    # Returns the earliest date after 'date' on which any of 'tables' changes,
    # or None if none of the 'tables' ever changes afterward.
    def next_change(self, tables, date):
        next = None
        for table in tables:
            next = nonmissing_min(next, self.execute_singleton(
                    "SELECT MIN(CREATED_DT) FROM %s WHERE CREATED_DT > %d"
                    % (table, date)))
            next = nonmissing_min(next, self.execute_singleton(
                    "SELECT MIN(DELETED_DT) FROM %s WHERE DELETED_DT > %d "
                    "AND DELETED_DT != 9223372036854775807"
                    % (table, date)))
        return next
                       
# An example how to 
if __name__ == "__main__":
    conn = DWHConnection(host = DB_HOST, user = DB_USER, passwd = DB_PASSWD, 
                         db = DB_DB)
    timestamp = conn.convert_time(time.time())
    cursor = conn.execute(conn.query('FLOW', timestamp) + " ORDER BY CREATED_DT")

    # ... access the cursor and retrieve the state of other tables as
    # needed while browing the cursor by running another execute.
