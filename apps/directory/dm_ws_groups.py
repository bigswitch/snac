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
#

import logging
import simplejson

from twisted.internet import defer
from twisted.python.failure import Failure
from nox.ext.apps.coreui import webservice
from nox.ext.apps.coreui.webservice import *
from nox.ext.apps.directory.directorymanagerws import *
from nox.ext.apps.directory.directorymanager import mangle_name
from nox.lib.directory import DirectoryException

from nox.lib.netinet.netinet import create_eaddr, create_ipaddr

lg = logging.getLogger('dm_ws_groups')

groupname_to_type = { 
    "switch"   : Directory_Factory.SWITCH_PRINCIPAL_GROUP,
    "location" : Directory_Factory.LOCATION_PRINCIPAL_GROUP,
    "host"     : Directory_Factory.HOST_PRINCIPAL_GROUP,
    "user"     : Directory_Factory.USER_PRINCIPAL_GROUP,
    "dladdr"   : Directory_Factory.DLADDR_GROUP,
    "nwaddr"   : Directory_Factory.NWADDR_GROUP,
}

def is_member(group_info,mangled_name, ctype_str):
      if ctype_str in ["principal", "address"]:
        if mangled_name in group_info.member_names:
          return True
        return False
      else: # 'subgroup'
        if mangled_name in group_info.subgroup_names:
          return True
        return False


class dm_ws_groups:
    """Exposes the group portion of the directory manager interface"""

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)    

    def member_op(self,request,group_info,member,ptype_str,
                  otype_str,ctype_str):
        try:
            def ok(res):
                def unicode_(s, encoding):
                      if isinstance(s, unicode): return s
                      return unicode(s, encoding)

                members = []
                for member in res[0]:
                    if not isinstance(member, basestring):
                        member = str(member)
                    members.append(unicode_(member, 'utf-8'))
                subgroups = [unicode_(subgroup, 'utf-8') for subgroup in res[1]]
                res_str =  [ members, subgroups ]
                request.write(simplejson.dumps(res_str))
                request.finish()

            if group_info is None:
                return webservice.badRequest(request,"Group does not exist.")

            exists = is_member(group_info, member, ctype_str)
            if otype_str == "add" and exists:
                return webservice.badRequest(request, "%s is already a %s in the group." \
                                                   % (member,ctype_str))
            if otype_str != "add" and not exists:
                return webservice.notFound(request, "%s %s not found in group." \
                                                 % (ctype_str.capitalize(),member))

            if otype_str == "":
                # special case, this is just a membership test
                # if the request got this far, return success
                request.finish()
                return


            ptype = groupname_to_type[ptype_str]
            method_name = otype_str + "_group_members"
            f =  getattr(self.dm, method_name)

            if ctype_str in ["principal", "address"]:
                d = f(ptype,group_info.name, (member,), () )
            else: # 'subgroup' case
                d = f(ptype,group_info.name, (), (member,))
            d.addCallback(ok)
            d.addErrback(self.err, request, "%s member_op" % method_name,
                         "Could not %s." % method_name)
            return NOT_DONE_YET
        except Exception, e: 
            return self.err(Failure(), request, "member_op",
                            "Could not perform group operation.")

    def member_op_start(self, request, arg, otype_str):
        try:
            groupname = arg['<group name>']
            groupdir = arg['<group dir>']
            mangled_group = mangle_name(groupdir,groupname)
            membername = arg['<member name>']
            memberdir = arg.get('<member dir>')
            ptype_str = get_principal_type_from_args(arg)
            ctype_str = find_value_in_args(arg,
                    ["principal","address","subgroup"])

            if memberdir == self.dm.discovered_dir.name:
                return webservice.badRequest(request, "Discovered principals "
                        "may not be added to groups; try moving principal to "
                        "a persistent directory first.")
            ptype = groupname_to_type[ptype_str]
            is_address = ctype_str == "address"
            if is_address and ptype == Directory_Factory.DLADDR_GROUP:
                  mangled_member = create_eaddr(membername.encode('utf-8'))
            elif is_address and ptype == Directory_Factory.NWADDR_GROUP:
                  mangled_member = create_cidr_ipaddr(
                        membername.encode('utf-8'))
            else:
                  mangled_member = mangle_name(memberdir, membername)
            if mangled_member is None:
                    return webservice.badRequest(request,
                        "Invalid group member parameter: '%s'" % membername)

            d = self.dm.get_group(ptype, mangled_group)
            f = lambda x: self.member_op(request,x,mangled_member,
                                         ptype_str,otype_str,ctype_str)
            d.addCallback(f)
            d.addErrback(self.err, request, "member_op_start",
                         "Could not retrieve group.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "member_op_start",
                            "Could not retrieve group.")

    def group_op(self, request, group_info, mangled_group,ptype_str, otype_str): 
        try:
            def ok(res):
                if isinstance(res, GroupInfo):
                    request.write(simplejson.dumps(res.to_str_dict()))
                else:
                    request.write(simplejson.dumps(res))
                request.finish()

            is_get_op = otype_str == "get" or otype_str == "principal" \
                or otype_str == "subgroup"
            if group_info is None and (is_get_op or otype_str == "del"): 
                return webservice.notFound(request,"Group %s does not exist." % mangled_group) 
          
            # read operations finish here.  this includes 'get','principal' 
            # and 'subgroup' otype_str 
            if is_get_op :
                str_dict = group_info.to_str_dict()
                if otype_str == "get": 
                    request.write(simplejson.dumps(str_dict))
                elif otype_str == "principal":
                    request.write(simplejson.dumps(str_dict["member_names"]))
                elif otype_str == "subgroup": 
                    request.write(simplejson.dumps(str_dict["subgroup_names"]))
                request.finish()
                return
  
            # only otype_str == 'add' or 'del' continues to this point

            ptype = groupname_to_type[ptype_str]
            if otype_str == "add":
                content = json_parse_message_body(request)
                if content == None:
                    return webservice.badRequest(request, "Unable to parse message body.")
                if group_info is None:
                    content["name"] = mangled_group
                    d = getattr(self.dm, "add_group")(ptype,
                                                      GroupInfo.from_str_dict(content))
                elif len(content) == 1 and content.has_key('name'):
                      d = getattr(self.dm, "rename_group")(ptype,
                                                           mangled_group, content['name'],'','')
                else:
                      content["name"] = mangled_group
                      d = getattr(self.dm, "modify_group")(ptype,
                                                           GroupInfo.from_str_dict(content))
            else: # delete
                d = getattr(self.dm, "del_group")(ptype, mangled_group)
            d.addCallback(ok)
            d.addErrback(self.err, request, "%s %s group_op" % (otype_str, ptype_str),
                         "Could not perform %s group operation." % ptype_str)
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "%s %s group_op" % (otype_str, ptype_str),
                            "Could not perform %s group operation." % ptype_str)

    def group_op_start(self, request, arg, otype_str):
        try:
            groupname = arg['<group name>']
            dirname = arg.get('<group dir>')
            mangled_group = mangle_name(dirname,groupname)
            ptype_str = get_principal_type_from_args(arg)
            ptype = groupname_to_type[ptype_str]
            d = self.dm.get_group(ptype, mangled_group)
            f = lambda x: self.group_op(request,x,mangled_group,
                                        ptype_str,otype_str)
            d.addCallback(f)
            d.addErrback(self.err, request, "group_op_start",
                         "Could not retrieve group.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "group_op_start",
                            "Could not retrieve group.")


    def get_all_groups(self, request, arg):
        try:
            def cb(res):
                request.write(simplejson.dumps(res))
                request.finish()

            ptype_str = get_principal_type_from_args(arg)
            ptype = groupname_to_type[ptype_str]
            d = self.dm.search_groups(ptype)

            d.addCallback(cb)
            d.addErrback(self.err, request, "get_all_groups",
                         "Could not retrieve groups.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_all_groups",
                            "Could not retrieve groups.")

    def get_group_parents(self, request, arg):
        try:
            def cb(res):
                request.write(simplejson.dumps(res))
                request.finish()

            groupname = arg['<group name>']
            dirname = arg['<group dir>']
            mangled_group = mangle_name(dirname,groupname)
            ptype_str = get_principal_type_from_args(arg)
            ptype = groupname_to_type[ptype_str]
            d = self.dm.get_group_parents(ptype, mangled_group)

            d.addCallback(cb)
            d.addErrback(self.err, request, "get_group_parents",
                         "Could not retrieve group parents.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_group_parents",
                            "Could not retrieve group parents.")

    def get_addr_groups_op(self, request, arg):
        try:
            def cb(res):
                request.write(simplejson.dumps(res))
                request.finish()

            gtype_str = get_principal_type_from_args(arg)
            gtype = groupname_to_type[gtype_str]
            if gtype == Directory.NWADDR_GROUP:
                addr = create_cidr_ipaddr(arg['<address>'].encode('utf-8'))
            elif gtype == Directory.DLADDR_GROUP:
                addr = create_eaddr(arg['<address>'].encode('utf-8'))
            else:
                return webservice.badRequest(request, "Could not retrieve "
                        "address groups: invalid address type.")
            if addr is None:
                return webservice.badRequest(request, "Could not retrieve "
                        "address groups: invalid address format.")
            d = self.dm.get_group_membership(gtype, addr)
            d.addCallback(cb)
            d.addErrback(self.err, request, "get_group_parents",
                         "Could not retrieve address groups.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_addr_groups",
                            "Could not retrieve address groups.")

    def __init__(self, dm, reg):
        self.dm = dm

        grouptypes = ["host", "user", "location", "switch"]
        addrgrouptypes = ["dladdr", "nwaddr"]
        for gt in grouptypes + addrgrouptypes:
              path = ( webservice.WSPathStaticString("group"), ) + \
                         (WSPathStaticString(gt) ,)
              desc = "List the names of all %s groups" % (gt)
              reg(self.get_all_groups, "GET", path, desc)

        for gt in grouptypes + addrgrouptypes:
          path =         ( webservice.WSPathStaticString("group"), ) + \
                         ( webservice.WSPathStaticString(gt), ) + \
                         (WSPathExistingDirName(dm,"<group dir>") ,) + \
                         (WSPathArbitraryString("<group name>"),)
          desc = "Get all members and subgroups in a %s group" % gt
          reg(lambda x,y: self.group_op_start(x,y,"get"), "GET", path, desc)
          desc = "Delete a %s group" % gt
          reg(lambda x,y: self.group_op_start(x,y,"del"), "DELETE", path, desc)
          desc = "Add a %s group" % gt
          reg(lambda x,y: self.group_op_start(x,y,"add"), "PUT", path, desc)

          parent_path = path + ( webservice.WSPathStaticString("parent"),)
          desc = "Get immediate parent groups of a %s group" % gt
          reg(self.get_group_parents, "GET",parent_path, desc)

        for gt in grouptypes:
          classes = [ "subgroup", "principal" ] 
          for c in classes: 
            path1 =         ( webservice.WSPathStaticString("group"), ) + \
                         ( webservice.WSPathStaticString(gt), ) + \
                         (WSPathExistingDirName(dm,"<group dir>") ,) + \
                         (WSPathArbitraryString("<group name>"),) + \
                         ( webservice.WSPathStaticString(c), ) 
            get_desc = "Get a list of all %ss in the named group" % c
            fn = (lambda z: lambda x,y: self.group_op_start(x,y,z))(c)
            reg(fn, "GET", path1, get_desc)

            path2 =   path1 + (WSPathExistingDirName(dm,"<member dir>") ,) + \
                         (WSPathArbitraryString("<member name>"),)
            get_desc = "Test if a %s is in the named group (no recursion)" % c
            reg(lambda x,y: self.member_op_start(x,y,""), "GET", path2,get_desc)
            put_desc = "Add a %s to the named group" % c 
            reg(lambda x,y: self.member_op_start(x,y,"add"),"PUT",path2,put_desc)
            del_desc = "Delete a %s of the named group" % c 
            reg(lambda x,y: self.member_op_start(x,y,"del"),
                                                  "DELETE",path2,del_desc)

        for gt in addrgrouptypes:
          basepath = ( webservice.WSPathStaticString("group"), ) + \
                     ( webservice.WSPathStaticString(gt), ) + \
                     (WSPathExistingDirName(dm,"<group dir>") ,) + \
                     (WSPathArbitraryString("<group name>"),)
          get_desc = "Get a list of all subgroups in the named group"
          fn = (lambda z: lambda x,y: self.group_op_start(x,y,z))("subgroup")
          reg(fn, "GET", basepath+(webservice.WSPathStaticString("subgroup"),),
                  get_desc)
          get_desc = "Get a list of all addresses in the named group"
          fn = (lambda z: lambda x,y: self.group_op_start(x,y,z))("principal")
          reg(fn, "GET", basepath+(webservice.WSPathStaticString("address"),),
                  get_desc)

          sgmpath = basepath + ( webservice.WSPathStaticString("subgroup"), ) +\
                    (WSPathExistingDirName(dm,"<member dir>") ,) +\
                    (WSPathArbitraryString("<member name>"),)
          desc = "Test if a subgroup is in the named group (no recursion)"
          reg(lambda x,y: self.member_op_start(x,y,""), "GET", sgmpath, desc)
          desc = "Add a subgroup to the named group"
          reg(lambda x,y: self.member_op_start(x,y,"add"),"PUT", sgmpath, desc)
          desc = "Delete a subgroup of the named group"
          reg(lambda x,y: self.member_op_start(x,y,"del"),"DELETE",sgmpath,desc)

          if gt == 'nwaddr':
            member_desc = "an IP address or address block"
          else:
            member_desc = "a MAC address"
          ampath = basepath + ( webservice.WSPathStaticString("address"), ) +\
                   (WSPathArbitraryString("<member name>"),)
          desc = "Test if %s is in the named group (no recursion)" %member_desc
          reg(lambda x,y: self.member_op_start(x,y,""), "GET", ampath, desc)
          desc = "Add %s to the named group" %member_desc
          reg(lambda x,y: self.member_op_start(x,y,"add"),"PUT", ampath, desc)
          desc = "Delete %s of the named group" %member_desc
          reg(lambda x,y: self.member_op_start(x,y,"del"),"DELETE",ampath,desc)

          addrpath = ( webservice.WSPathStaticString(gt), ) + \
                     (WSPathArbitraryString("<address>"),) + \
                     ( webservice.WSPathStaticString("group"), )
          desc = "Get all groups for %s" %member_desc
          reg(self.get_addr_groups_op, "GET", addrpath, desc)


