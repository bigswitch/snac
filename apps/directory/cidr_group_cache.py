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

from twisted.python import log

from nox.lib.netinet.netinet import create_ipaddr, ipaddr, cidr_ipaddr
from nox.ext.thirdparty.py_radix import radix

class cidr_group_cache:
    """Allow quick lookup of groups for an IP based on CIDR membership
    """

    def __init__(self):
        self.trie = radix.Radix()

    def get_groups(self, ip):
        ret = set()
        node = self.trie.search_best(str(ip))
        while node is not None:
            ret = ret.union(node.data['groups'])
            node = self.trie.search_containing(node.prefix)
        return ret

    def add_cidr(self, group, cidr):
        cidrstr = str(cidr)
        best = self.trie.search_best(cidrstr)
        if best is not None and best.prefix == cidrstr:
            best.data['groups'].add(group)
        else:
            node = self.trie.add(cidrstr)
            node.data['groups'] = set([group])

    def del_cidr(self, group, cidr):
        cidrstr = str(cidr)
        node = self.trie.search_exact(cidrstr)
        if node is None:
            return
        node.data['groups'].discard(group)
        if len(node.data['groups']) == 0:
            self.trie.delete(cidrstr)

    def ren_group(self, oldgroupname, newgroupname):
        for node in self.trie:
            groups = node.data['groups']
            if oldgroupname in groups:
                groups.discard(oldgroupname)
                groups.add(newgroupname)

