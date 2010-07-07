import sys
from nox.apps.migration.migration import Plugin

class addrgroup_migration_plugin(Plugin):
    """
    An example plugin migrating a table 'TEST' from version 0 to 1.
    """
    def __init__(self):
        self.new_rows = set()

    def get_table(self): return self._table_name
    def get_version(self): return 0
    def get_schema(self): return \
    [
        {
            'GUID' : self.GUID,
            'NAME' : self.TEXT,
            'MEMBERADDR' : self.INTEGER,
            'PREFIXLEN' : self.INTEGER,
            'SUBGROUPNAME' : self.TEXT,
            'DESCRIPTION' : self.TEXT,
        },
        {
            self._table_name+'_name_idx' : ('NAME',),
            self._table_name+'_memberAddr_idx' : ('MEMBERADDR', 'PREFIXLEN'),
            self._table_name+'_subgroupName_idx' : ('SUBGROUPNAME',),
            self._table_name+'_groupMemberSubgroup_idx' :
                    ('NAME', 'MEMBERADDR', 'PREFIXLEN', 'SUBGROUPNAME'),
        }
    ]

    def migrate(self, row):
        """
        Set the default value to the new column.
        """
        if row['MEMBERADDR'] == -1:
            row['PREFIXLEN'] = -1
        else:
            row['PREFIXLEN'] = self._def_prefix_len
        return row

    def get_new_rows(self):
        return tuple(self.new_rows)

class nwaddr_group_migration(addrgroup_migration_plugin):
    _def_prefix_len = 32
    _table_name = 'nox_nwaddr_groups'

class dladdr_group_migration(addrgroup_migration_plugin):
    _def_prefix_len = 48
    _table_name = 'nox_dladdr_groups'

def get_plugins():
    return [ nwaddr_group_migration(), dladdr_group_migration() ]

__all__ = [ 'get_plugins' ]
