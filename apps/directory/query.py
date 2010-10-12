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

from nox.apps.directory.directorymanager import demangle_name
from nox.apps.directory.directorymanager import mangle_name

lg = logging.getLogger('query')

class query:

    def __init__(self, query = {}):
        """Accepts a dictionary of key/value pairs which it uses to
        compare against dictionaries of object attributes"""
        self._query = query
        self._dir   = ""

        # split names into directory/name
        if self._query.has_key('name'):
            self._dir, self._query['name'] =\
                demangle_name(self._query['name'])

    def matches(self, attrs):
        for field in self._query:
            if not attrs.has_key(field):
                return False
            # do more complicated matching here
            elif not attrs[field] == self._query[field]:
                return False
        return True        
