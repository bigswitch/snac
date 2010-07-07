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
# Trivial example using reactor timer method to countdown from three

import sys
import copy
import inspect
import logging

from twisted.internet import defer
from nox.lib.core import Component
from nox.lib.netinet.netinet import ethernetaddr, ipaddr, cidr_ipaddr, \
    create_eaddr, create_bin_eaddr, create_ipaddr, create_cidr_ipaddr, \
    c_htonl, c_ntohl
from nox.lib.openflow import OFP_VLAN_NONE

from nox.apps.authenticator.pyflowutil import Flow_expr, Flow_action, strlist
from nox.apps.directory.pydirmanager import Directory
from socket import htons, ntohs

lg = logging.getLogger("compile")

## Constants ##

# Composite predicates

PROTO = Flow_expr.MAX_PRED
EXPGROUP = Flow_expr.MAX_PRED + 1
SWSRC = Flow_expr.MAX_PRED + 2
SWDST = Flow_expr.MAX_PRED + 3
N_COMPOUND_PRED = 4

# SEPL argument types

LOC_T = 1
HOST_T = 2
USER_T = 3
ROLE_T = 4
GROUP_T = 5
DLVLAN_T = 6
DLADDR_T = 7
DLTYPE_T = 8
NWADDR_T = 9
NWPROTO_T = 10
TPORT_T = 11
SUBNET_T = 12
FUNC_T = 13
CFUNC_T = 14
PROTO_T = 15
TLOC_T = 16
SW_T = 17
MAX_T = 18

# String representation for Role values

ROLE_VALS = \
{
    Flow_expr.REQUEST : u'REQUEST',
    Flow_expr.RESPONSE : u'RESPONSE'
}

# SEPL predicate orientations

NONE_S = 0
SRC_S = 1
DST_S = 2

# Integer constants

U32_MAX = 4294967295
U16_MAX = 65535
U8_MAX = 255

U32_ALL = 0xffffffff

## Globals ##

__policy__ = None          # policy component that policy file rules
                           # should be added to

# SEPL Policy Compile/Declare Error Exceptions

def log_and_raise(err):
    lg.error(err)
    if isinstance(err, unicode):
        raise Exception(err.encode('utf-8'))
    else:
        raise Exception(err)

# Predicate info table
   
# Predicate info indices

STR_IDX = 0
TYPE_IDX = 1
SIDE_IDX = 2
GROUPABLE_IDX = 3
EXCLUSIVE_IDX = 4

# Possible values for various predicate attributes

GROUPABLE = True
NON_GROUPABLE = False

EXCLUSIVE = True # rule specifying more than is a static conflict
NON_EXCLUSIVE = False # rule can specify more than one value

# user should be non-exclusive??

__preds__ = range(Flow_expr.MAX_PRED + N_COMPOUND_PRED)
__preds__[Flow_expr.LOCSRC] = (u'locsrc', LOC_T, SRC_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.LOCDST] = (u'locdst', LOC_T, DST_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.HSRC] = (u'hsrc', HOST_T, SRC_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.HDST] = (u'hdst', HOST_T, DST_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.USRC] = (u'usrc', USER_T, SRC_S, GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.UDST] = (u'udst', USER_T, DST_S, GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.CONN_ROLE] = (u'conn_role', ROLE_T, NONE_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.HGROUPSRC] = (u'in_group', GROUP_T, SRC_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.HGROUPDST] = (u'in_group', GROUP_T, DST_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.UGROUPSRC] = (u'in_group', GROUP_T, SRC_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.UGROUPDST] = (u'in_group', GROUP_T, DST_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.DLVLAN] = (u'dlvlan', DLVLAN_T, NONE_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.DLSRC] = (u'dlsrc', DLADDR_T, SRC_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.DLDST] = (u'dldst', DLADDR_T, DST_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.DLTYPE] = (u'dltype', DLTYPE_T, NONE_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.NWSRC] = (u'nwsrc', NWADDR_T, SRC_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.NWDST] = (u'nwdst', NWADDR_T, DST_S, GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.NWPROTO] = (u'nwproto', NWPROTO_T, NONE_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.TPSRC] = (u'tpsrc', TPORT_T, SRC_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.TPDST] = (u'tpdst', TPORT_T, DST_S, NON_GROUPABLE, EXCLUSIVE)
__preds__[Flow_expr.SUBNETSRC] = (u'subnetsrc', SUBNET_T, SRC_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.SUBNETDST] = (u'subnetdst', SUBNET_T, DST_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.ADDRGROUPSRC] = (u'in_group', GROUP_T, SRC_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.ADDRGROUPDST] = (u'in_group', GROUP_T, DST_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[Flow_expr.FUNC] = (u'func', FUNC_T, NONE_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[PROTO] = (u'protocol', PROTO_T, NONE_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[EXPGROUP] = (u'in_group', None, NONE_S, NON_GROUPABLE, NON_EXCLUSIVE)
__preds__[SWSRC] = (u'swsrc', SW_T, SRC_S, GROUPABLE, EXCLUSIVE)
__preds__[SWDST] = (u'swdst', SW_T, DST_S, GROUPABLE, EXCLUSIVE)


# Action info table

ARG_IDX = 1

__actions__ = range(Flow_action.MAX_ACTIONS)
__actions__[Flow_action.ALLOW] = (u'allow', None)
__actions__[Flow_action.DENY] = (u'deny', None)
__actions__[Flow_action.WAYPOINT] = (u'waypoint', HOST_T)
__actions__[Flow_action.C_FUNC] = (u'c_action', CFUNC_T)
__actions__[Flow_action.PY_FUNC] = (u'py_action', FUNC_T)
__actions__[Flow_action.NAT] = (u'nat', TLOC_T)

# compiler supported function macros

__supported_fns__ = {}
__supported_fns__[u'authenticate_host'] = 1
__supported_fns__[u'allow_no_nat'] = 1
__supported_fns__[u'http_redirect'] = 1
__supported_fns__[u'http_proxy_redirect'] = 1
__supported_fns__[u'http_proxy_undo_redirect'] = 1

# Returns the info entry for a pred, action respectively

def pred_info(pred):
    if pred < 0 or pred >= len(__preds__):
        return None
    return __preds__[pred]

def action_info(act):
    if act < 0 or act >= len(__actions__):
        return None
    return __actions__[act]

# Suffix for an ith entry

def __ith__(i):
    r = i % 10
    if i == 1:
        suffix = u'st'
    elif i == 2:
        suffix = u'nd'
    elif i == 3:
        suffix = u'rd'
    else:
        suffix = u'th'
    return unicode(i) + suffix

# Predicate argument check methods

# Check for valid principal IDs, names, or values

# fail if results > 1??
def check_principal(results):
    if len(results) == 0:
        return None
    if not isinstance(results[0], unicode):
        return unicode(results[0], 'utf-8')
    return results[0]

def check_get_loc(result):
    if result is None or result.dpid is None or result.port is None:
        return None
    if not isinstance(result.name, unicode):
        name = unicode(result.name, 'utf-8')
    else:
        name = result.name
    return [ name, result.dpid.as_host() + (result.port << 48) ]

def check_principal_failed(err):
    log_and_raise("Failure %s when checking principal." % err.value.message)

def loc_check(loc, translate=False):
    global __policy__
    if translate:
        return __policy__.authenticator.get_principal_id(loc.encode('utf-8'), Directory.LOCATION_PRINCIPAL, True)
    if not isinstance(loc, basestring):
        return defer.succeed(None)
    if not isinstance(loc, unicode):
        loc = unicode(loc, 'utf-8')
    d = __policy__._dm.search_principals(Directory.LOCATION_PRINCIPAL, { 'name' : loc })
    d.addCallbacks(check_principal, check_principal_failed)
    return d

def nat_loc_check(loc, translate=False):
    global __policy__
    if translate:
        return loc[1]
    if isinstance(loc, list) and len(loc) == 2:
        loc = loc[0]

    if not isinstance(loc, basestring):
        return defer.succeed(None)
    if not isinstance(loc, unicode):
        loc = unicode(loc, 'utf-8')
    d = __policy__._dm.get_principal(Directory.LOCATION_PRINCIPAL, loc)
    d.addCallbacks(check_get_loc, check_principal_failed)
    return d

def host_check(host, translate=False):
    global __policy__
    if translate:
        return __policy__.authenticator.get_principal_id(host.encode('utf-8'), Directory.HOST_PRINCIPAL, True)
    if not isinstance(host, basestring):
        return defer.succeed(None)
    if not isinstance(host, unicode):
        host = unicode(host, 'utf-8')
    d = __policy__._dm.search_principals(Directory.HOST_PRINCIPAL, { 'name' : host })
    d.addCallbacks(check_principal, check_principal_failed)
    return d

def user_check(user, translate=False):
    global __policy__
    if translate:
        return __policy__.authenticator.get_principal_id(user.encode('utf-8'), Directory.USER_PRINCIPAL, True)
    if not isinstance(user, basestring):
        return defer.succeed(None)
    if not isinstance(user, unicode):
        user = unicode(user, 'utf-8')
    d = __policy__._dm.search_principals(Directory.USER_PRINCIPAL, { 'name' : user })
    d.addCallbacks(check_principal, check_principal_failed)
    return d

def role_check(role, translate=False):
    if isinstance(role, int) or isinstance(role, long):
        if ROLE_VALS.has_key(int(role)):
            if translate:
                return role
            return defer.succeed(role)
    return defer.succeed(None)

def dlvlan_check(vlan, translate=False):
    # should check if defined constant here

    if (isinstance(vlan, int) or isinstance(vlan, long)) \
            and ((vlan >= 0 and vlan <= 0xfff) or vlan == OFP_VLAN_NONE):
        if translate:
            return htons(int(vlan))
        return defer.succeed(int(vlan))
    return defer.succeed(None)

def dladdr_check(addr, translate=False):
    # should check if defined constant here

    if isinstance(addr, unicode):
        addr = addr.encode('utf-8')

    if isinstance(addr, str) and not (':' in addr):
        if len(addr) != ethernetaddr.LEN:
            return defer.succeed(None)
        addr = create_bin_eaddr(addr)
    elif isinstance(addr, str) or ((isinstance(addr, long) or isinstance(addr, int)) and addr >= 0):
        addr = create_eaddr(addr)
    elif not isinstance(addr, ethernetaddr):
        return defer.succeed(None)

    if addr is None:
        return defer.succeed(None)

    if translate:
        return addr.nb_long()
    return defer.succeed(unicode(str(addr)))

def dltype_check(dl, translate=False):
    # should check if defined constant here

    if (isinstance(dl, int) or isinstance(dl, long)) and dl >= 0 and dl <= U16_MAX:
        if translate:
            return htons(int(dl))
        else:
            return defer.succeed(int(dl))
    return defer.succeed(None)

def nwaddr_check(addr, translate=False):
    # should check if defined constant here

    if isinstance(addr, unicode):
        addr = addr.encode('utf-8')

    if ((isinstance(addr, int) or isinstance(addr, long)) and addr >= 0 and addr <= U32_MAX) \
            or isinstance(addr, str):
        addr = create_ipaddr(addr)
    elif not isinstance(addr, ipaddr):
        return defer.succeed(None)

    if addr is None:
        return defer.succeed(None)

    if translate:
        return addr.addr
    return defer.succeed(unicode(str(addr)))
   
def nwproto_check(proto, translate=False):
    # should check if defined constant here

    if (isinstance(proto, int) or isinstance(proto, long)) and proto >= 0 and proto <= U8_MAX:
        if translate:
            return int(proto)
        return defer.succeed(int(proto))
    return defer.succeed(None)

def tport_check(tport, translate=False):
    # should check if defined constant here

    if (isinstance(tport, int) or isinstance(tport, long)) and tport >= 0 and tport <= U16_MAX:
        if translate:
            return htons(int(tport))
        return defer.succeed(int(tport))
    return defer.succeed(None)

def subnet_check(cidr, translate=False):
    if isinstance(cidr, unicode):
        cidr = cidr.encode('utf-8')

    if isinstance(cidr, str):
        cidr = create_cidr_ipaddr(cidr)
    elif not isinstance(cidr, cidr_ipaddr):
        return defer.succeed(None)
    
    if cidr is None:
        return defer.succeed(None)

    if translate:
        return ((cidr.mask << 32) | (cidr.addr.addr))
    return defer.succeed(unicode(str(cidr)))

def group_check(group, t, translate=False):
    global __policy__
    if not isinstance(group, basestring):
        return defer.succeed(None)
    if not isinstance(group, unicode):
        group = unicode(group, 'utf-8')
    if not (isinstance(t, int) or isinstance(t, long)):
        return defer.succeed(None)
        
    if t == SW_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.SWITCH_PRINCIPAL_GROUP, True)
        d = __policy__._dm.search_groups(Directory.SWITCH_PRINCIPAL_GROUP,  { 'name' : group })
    elif t == LOC_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.LOCATION_PRINCIPAL_GROUP, True)
        d = __policy__._dm.search_groups(Directory.LOCATION_PRINCIPAL_GROUP,  { 'name' : group })
    elif t == HOST_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.HOST_PRINCIPAL_GROUP, True)
        d = __policy__._dm.search_groups(Directory.HOST_PRINCIPAL_GROUP, { 'name' : group })
    elif t == USER_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.USER_PRINCIPAL_GROUP, True)
        d = __policy__._dm.search_groups(Directory.USER_PRINCIPAL_GROUP, { 'name' : group })
    elif t == DLADDR_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.DLADDR_GROUP, True)
        d = __policy__._dm.search_groups(Directory.DLADDR_GROUP, { 'name' : group })
    elif t == NWADDR_T:
        if translate:
            return __policy__.authenticator.get_group_id(group.encode('utf-8'), Directory.NWADDR_GROUP, True)
        d = __policy__._dm.search_groups(Directory.NWADDR_GROUP, { 'name' : group })
    else:
        return defer.succeed(None)

    d.addCallbacks(check_principal, check_principal_failed)
    return d

# pyfunctions used in policy
__pyfuncs__ = {}

def register_py_func(fn):
    global __pyfuncs__

    if not callable(fn):
        return False
    if __pyfuncs__.has_key(fn.func_name):
        return False
    (a, va, vk, defs) = inspect.getargspec(fn)
    if (defs is None and len(a) != 1) or (defs is not None and len(defs) + 1 < len(a)):
        return False
    __pyfuncs__[unicode(fn.func_name)] = fn
    return True

def func_check(fn, translate=False):
    global __pyfuncs__

    if callable(fn):
        if __pyfuncs__.has_key(fn.func_name):
            if __pyfuncs__[fn.func_name] != fn:
                return defer.succeed(None)
        elif not register_py_func(fn):
            return defer.succeed(None)
        if translate:
            return fn
        return defer.succeed(unicode(fn.func_name))

    if not isinstance(fn, basestring):
        return defer.succeed(None)
    if not isinstance(fn, unicode):
        fn = unicode(fn)

    if __pyfuncs__.has_key(fn):
        if translate:
            return __pyfuncs__[fn]
        return defer.succeed(fn)
    return defer.succeed(None)

# Defined protocols

__protos__ = {}
__protos__[u'arp'] = (0x0806, None, None)
__protos__[u'ipv4'] = (0x0800, None, None)
__protos__[u'tcp'] = (None, 6, None) # makes sense if not IP?
__protos__[u'udp'] = (None, 17, None)
__protos__[u'icmp'] = (None, 1, None)
__protos__[u'ipv4_icmp'] = (0x0800, 1, None)
__protos__[u'ipv4_tcp'] = (0x0800, 6, None)
__protos__[u'ipv4_udp'] = (0x0800, 17, None)
__protos__[u'http'] = (None, None, 80) # same comment as above
__protos__[u'dhcps'] = (None, None, 67) 
__protos__[u'dhcpc'] = (None, None, 68) 
__protos__[u'dhcp6s'] = (None, None, 547) 
__protos__[u'dhcp6c'] = (None, None, 546) 
__protos__[u'tcp_http'] = (None, 6, 80)
__protos__[u'ipv4_tcp_http'] = (0x0800, 6, 80)
__protos__[u'ssh'] = (None, None, 22)
__protos__[u'dns'] = (None, 17, 53)

def proto_check(proto, translate=False):
    if isinstance(proto, basestring):
        if not isinstance(proto, unicode):
            proto = unicode(proto, 'utf-8')

        if __protos__.has_key(proto):
            if translate:
                return __protos__[proto]
            return defer.succeed(proto)
        else:
            return defer.succeed(None)

    if (isinstance(proto, list) or isinstance(proto, tuple)) and len(proto) == 3:
        if translate:
            res = [ None, None, None ]
            if proto[0] is not None:
                res[0] = dltype_check(proto[0], True)
            if proto[1] is not None:
                res[1] = nwproto_check(proto[1], True)
            if proto[2] is not None:
                res[2] = tport_check(proto[2], True)
            return tuple(res)

        res = []
        if proto[0] is not None:
            d = dltype_check(proto[0])
            d.addCallback(append_proto, res, proto)
            return d
        d = defer.Deferred()
        d.addCallback(append_proto, res, proto)
        d.callback(None)
        return d

    return defer.succeed(None)

def append_proto(check, res, proto):
    if check is None and len(res) != 0:
        return None

    res.append(check)
    if len(res) == 1:
        if proto[1] is not None:
            d = nwproto_check(proto[1])
            d.addCallback(append_proto, res, proto)
            return d
        res.append(None)
    if len(res) == 2:
        if proto[2] is not None:
            d = tport_check(proto[2])
            d.addCallback(append_proto, res, proto)
            return d
        res.append(None)
    if len(res) == 3 and res.count(None) != 3:
        return tuple(res)

    return None

def py_action_check(fn, translate=False):
    return func_check(fn, translate)

def c_action_check(fn_name, args, translate=False):
    global __policy__

    if not isinstance(fn_name, basestring):
        return defer.succeed(None)
    if not isinstance(fn_name, unicode):
        fn_name = unicode(fn_name, 'utf-8')

    slist = strlist()
    new_args = [fn_name]
    for a in args:
        if not isinstance(a, basestring):
            try:
                a = str(a)
            except:
                return defer.succeed(None)
        if isinstance(a, unicode):
            slist.push_back(a.encode('utf-8'))
            new_args.append(a)
        else:
            slist.push_back(a)
            new_args.append(unicode(a, 'utf-8'))
    if __policy__.flow_util.valid_fn_args(fn_name.encode('utf-8'), slist):
        return defer.succeed(new_args)
    return defer.succeed(None)
    
# Predicate type info table
     
# STR_IDX = 0 defined above
CHECK_IDX = 1

__pred_types__ = range(MAX_T)
__pred_types__[LOC_T] = (u'loc_t', loc_check)
__pred_types__[HOST_T] = (u'host_t', host_check)
__pred_types__[USER_T] = (u'user_t', user_check)
__pred_types__[ROLE_T] = (u'role_t', role_check)
__pred_types__[GROUP_T] = (u'group_t', group_check)
__pred_types__[DLVLAN_T] = (u'dlvlan_t', dlvlan_check)
__pred_types__[DLADDR_T] = (u'dladdr_t', dladdr_check)
__pred_types__[DLTYPE_T] = (u'dltype_t', dltype_check)
__pred_types__[NWADDR_T] = (u'nwaddr_t', nwaddr_check)
__pred_types__[NWPROTO_T] = (u'nwproto_t', nwproto_check)
__pred_types__[TPORT_T] = (u'tport_t', tport_check)
__pred_types__[SUBNET_T] = (u'subnet_t', subnet_check)
__pred_types__[FUNC_T] = (u'func_t', func_check)
__pred_types__[CFUNC_T] = (u'cfunc_t', c_action_check)
__pred_types__[PROTO_T] = (u'proto_t', proto_check)
__pred_types__[TLOC_T] = (u'tloc_t', nat_loc_check)
__pred_types__[SW_T] = (u'sw_t', None) # nothing should be calling this

def pred_type_info(t):
    if t >= len(__pred_types__) or t < 0:
        return None
    return __pred_types__[t]

def hex_dl_byte(i):
    s = hex(int(i))[2:]
    if len(s) == 1:
        return u'0' + s
    return unicode(s)
    
# SEPL Literal Expression Representation
# Holds the predicate type and arguments
# DNF converts each rule to disjunctive normal form
# as list of lists.  Each inner-list is a set of conjunctions.

class PyLiteral:
    "SEPL literal representation"

    def __init__(self, pred, args):
        self.pred = pred
        self.args = args

    def renamed(self, t, old_name, new_name, subtype):
        pinfo = pred_info(self.pred)
        
        if pinfo[TYPE_IDX] == t and self.args[0] == old_name:
            if t != GROUP_T or subtype == pred_info(self.args[1])[TYPE_IDX]:
                self.args[0] = new_name
                return True
        return False
            
    def DNF(self, negate):        
        if self.pred == EXPGROUP:
            p = self.args[1]
            a = self.args[0][0]
            exp = PyComplexPred(PyLiteral(p, [a]))
            for a in self.args[0][1:]:
                exp = exp | PyComplexPred(PyLiteral(p, [a]))
            return exp.DNF(negate)

        pinfo = pred_info(self.pred)
        t = pinfo[TYPE_IDX] 
        if t == GROUP_T:
            arg = pred_type_info(t)[CHECK_IDX](self.args[0], pred_info(self.args[1])[TYPE_IDX], True)
        elif t == PROTO_T and len(self.args) > 1:
            arg = pred_type_info(t)[CHECK_IDX](self.args, True)            
        else:
            arg = pred_type_info(t)[CHECK_IDX](self.args[0], True)

        if self.pred == Flow_expr.CONN_ROLE and negate:
            if arg == Flow_expr.REQUEST:
                return [[(self.pred, Flow_expr.RESPONSE, False)]]
            elif arg == Flow_expr.RESPONSE:
                return [[(self.pred, Flow_expr.REQUEST, False)]]

        if self.pred == PROTO:
            exp = None
            if arg[0] is not None:
                exp = PyComplexPred(PyLiteral(Flow_expr.DLTYPE, [arg[0]]))
            if arg[1] is not None:
                if exp is None:
                    exp = PyComplexPred(PyLiteral(Flow_expr.NWPROTO, [arg[1]]))
                else:
                    exp = exp ^ PyComplexPred(PyLiteral(Flow_expr.NWPROTO, [arg[1]]))
            if arg[2] is not None:
                nexp = PyComplexPred(PyLiteral(Flow_expr.TPSRC, [arg[2]])) \
                    | PyComplexPred(PyLiteral(Flow_expr.TPDST, [arg[2]]))
                if exp is None:
                    exp = nexp
                else:
                    exp = exp ^ nexp
            return exp.DNF(negate)

        return [[(self.pred, arg, negate)]]

    def ustr(self):
        pinfo = pred_info(self.pred)
        t = pinfo[TYPE_IDX]

        if self.pred == PROTO:
            if len(self.args) == 3:
                protos = [u'None', u'None', u'None']
                if self.args[0] is not None:
                    protos[0] = self.__arg_str__(self.args[0], DLTYPE_T)
                if self.args[1] is not None:
                    protos[1] = self.__arg_str__(self.args[1], NWPROTO_T)
                if self.args[2] is not None:
                    protos[2] = self.__arg_str__(self.args[2], TPORT_T)
                return unicode(pinfo[STR_IDX] + '(' + ', '.join(protos) + ')')
            else:
                return unicode(pinfo[STR_IDX] + '(' + self.__arg_str__(self.args[0], t) + ')')

        if self.pred == EXPGROUP:
            eleminfo = pred_info(self.args[1])
            t = eleminfo[TYPE_IDX]
            return unicode(pinfo[STR_IDX] + '([' + ', '.join([self.__arg_str__(a, t) for a in self.args[0]]) \
                + '], \'' + eleminfo[STR_IDX].upper() + '\')')

        if t == GROUP_T:
            return unicode(pinfo[STR_IDX] + '(\'' + self.args[0] + '\', \'' \
                + pred_info(self.args[1])[STR_IDX].upper() + '\')')

        return unicode(pinfo[STR_IDX] + '(' + self.__arg_str__(self.args[0], t) + ')')

    def __arg_str__(self, arg, t):
        if t == DLTYPE_T or t == DLVLAN_T:
            return unicode(hex(arg))
        elif t == ROLE_T:
            return unicode('\'' + ROLE_VALS[arg] + '\'')
        elif isinstance(arg, int) or isinstance(arg, long):
            return unicode(str(arg))
        elif isinstance(arg, basestring):
            return unicode('\'' + arg + '\'')
        else:
            return unicode('\'' + str(arg) + '\'')
        
# Respresentation for complex SEPL expression involving conjunctions
# (^), disjunctions (|), and negations (~)

class PyComplexPred:

    def __init__(self, lit):
        self.lit = lit
        self.orp = None
        self.left = self.right = None
        self.negate = False

    def renamed(self, t, old_name, new_name, subtype):
        ret = False
        if self.lit is not None and not isinstance(self.lit, bool):
            if self.lit.renamed(t, old_name, new_name, subtype):
                ret = True
        if self.left is not None and not isinstance(self.left, bool):
            if self.left.renamed(t, old_name, new_name, subtype):
                ret = True
        if self.right is not None and not isinstance(self.right, bool):
            if self.right.renamed(t, old_name, new_name, subtype):
                ret = True
        return ret

    def is_literal(self):
        return self.orp is None and not self.negate and not isinstance(self.lit, PyComplexPred)

    def __xor__(self, other):
        if not isinstance(other, PyComplexPred):
            raise Exception('SEPL predicate ^ operator should connect two (perhaps complex) SEPL predicates')

        if self.orp is None and not self.negate:
            self.left = self.lit
            self.lit = None
            if other.is_literal():
                self.right = other.lit
            else:
                self.right = other
            self.orp = False
            return self

        new = PyComplexPred(self)
        new = new ^ other
        return new

    def __or__(self, other):
        if not isinstance(other, PyComplexPred):
            raise Exception('SEPL predicate | operator should connect two (perhaps complex) SEPL predicates')

        if self.orp is None and not self.negate:
            self.left = self.lit
            self.lit = None
            if other.is_literal():
                self.right = other.lit
            else:
                self.right = other
            self.orp = True
            return self

        new = PyComplexPred(self)
        new = new | other
        return new

    def __invert__(self):
        if not self.negate:
            self.negate = True
            return self

        new = PyComplexPred(self)
        new = ~new
        return new

    def DNF(self, negate):
        if negate:
            negate = not self.negate
        else:
            negate = self.negate

        if self.orp is None:
            if isinstance(self.lit, bool):
                if negate:
                    return not self.lit
                return self.lit
            return self.lit.DNF(negate)

        if negate:
            orp = not self.orp
        else:
            orp = self.orp

        if isinstance(self.left, bool):
            if negate:
                ldnf = not self.left
            else:
                ldnf = self.left
            if orp:
                if ldnf:
                    return True
            elif not ldnf:
                return False
        else:
            ldnf = self.left.DNF(negate)

        if isinstance(self.right, bool):
            if negate:
                rdnf = not self.right
            else:
                rdnf = self.right
            if orp:
                if rdnf:
                    return True
            elif not rdnf:
                return False
            return ldnf
        else:
            rdnf = self.right.DNF(negate)
            if isinstance(ldnf, bool):
                return rdnf

        if orp:
            ldnf.extend(rdnf)
            return ldnf
       
        nexps = []
        imax = len(rdnf) - 1

        for exp in ldnf:
            for i in xrange(imax + 1):
                if i == imax:
                    nexp = exp
                else:
                    nexp = exp[:]
                nexp.extend(rdnf[i])
                nexps.append(nexp)

        return nexps
                  
    def ustr(self, parent_op=None):
        if self.orp is None:
            if self.negate:
                if isinstance(self.lit, PyComplexPred):
                    return unicode('~' + '(' + self.lit.ustr() + ')')
                if isinstance(self.lit, PyLiteral):
                    return unicode('~' + self.lit.ustr())
                return unicode('~' + str(self.lit))
            if isinstance(self.lit, PyComplexPred) or isinstance(self.lit, PyLiteral):
                return self.lit.ustr()
            return unicode(str(self.lit))

        if self.orp == True:
            op = '|'
        else:
            op = '^'

        if isinstance(self.left, PyComplexPred):
            lstr = self.left.ustr(self.orp)
        elif isinstance(self.left, PyLiteral):
            lstr = self.left.ustr()
        else:
            lstr = str(self.left)

        if isinstance(self.right, PyComplexPred):
            rstr = self.right.ustr(self.orp)
        elif isinstance(self.right, PyLiteral):
            rstr = self.right.ustr()
        else:
            rstr = str(self.right)

        if self.negate:
            return unicode(' '.join(('~(' + lstr, op, rstr+ ')')))
        elif parent_op is None or parent_op == self.orp:
            return unicode(' '.join((lstr, op, rstr)))
        return unicode(' '.join(('(' + lstr, op, rstr + ')')))

class AsyncPred:
    "Wrapper to support asynchronous compiling of SEPL"

    def __init__(self, pred_deferred):
        self.lhs = None
        self.d = pred_deferred
        self.d.addCallback(self.set_lhs)
        __policy__.__add_rule_deferred__(self.d)

    def set_lhs(self, lhs):
        # Should really see this error bc will have errback-ed, right?
        if not isinstance(lhs, PyComplexPred):
            log_and_raise('AsyncPred did not receive PyComplexPred in callback.')
        self.lhs = lhs
        return self.lhs

    def __xor__(self, other):
        if not isinstance(other, AsyncPred):
            log_and_raise('SEPL predicate ^ operator should connect two (perhaps complex) SEPL predicates')
        self.d.addCallback(self.wait_for_rhs, other)
        self.d.addCallback(self.set_rhs, PyComplexPred.__xor__)
        return self

    def __or__(self, other):
        if not isinstance(other, AsyncPred):
            log_and_raise('SEPL predicate | operator should connect two (perhaps complex) SEPL predicates')
        self.d.addCallback(self.wait_for_rhs, other)
        self.d.addCallback(self.set_rhs, PyComplexPred.__or__)
        return self

    def __invert__(self):
        self.d.addCallback(self.do_invert)
        return self

    def do_invert(self, tmp):
        self.lhs = ~self.lhs
        return self.lhs

    def wait_for_rhs(self, tmp, other):
        return other.d

    def set_rhs(self, rhs, op):
        self.lhs = op(self.lhs, rhs)
        return self.lhs

# Generate python function to evaluate all 'func' predicates on a flow
# at rule evaluation time

def __gen_rule_fn__(fnlits):      
    def fn(flow):
        for f in fn.fns:
            if not f(flow):
                return False
        for f in fn.neg_fns:
            if f(flow):
                return False

        return True

    fn.fns = []
    fn.neg_fns = []
    for f in fnlits:
        if f[2]:
            fn.neg_fns.append(f[1])
        else:
            fn.fns.append(f[1])

    return fn

# Detects conflicts in a conjunction list

def lit_str(lit):
    if isinstance(lit, PyLiteral):
        return lit.ustr()
    return str(lit)

def __conjunction_conflict__(expr, log_conflicts=False, i=0):
    conflict = False
    prev = None
    for lit in expr:
        if prev is not None and lit[0] == prev[0]:
            pi = pred_info(prev[0])
            if prev[1] == lit[1]:
                if prev[2] == lit[2]:
                    if log_conflicts:
                        lg.error('Literal %s in %s OR expression is useless (repeated).' % (lit_str(lit), __ith__(i)))
                else:
                    conflict = True
                    if log_conflicts:
                        lg.error('Negated literal %s in %s OR expression conflicts!' % (lit_str(lit), __ith__(i)))
            elif pos is not None and pi[EXCLUSIVE_IDX]:
                if lit[2]:
                    if log_conflicts:
                        lg.error('Literal %s in %s OR expression is useless.' % (lit_str(lit), __ith__(i)))
                else:
                    conflict = True
                    if log_conflicts:
                        lg.error('Literal %s in %s OR expression conflicts!' % (lit_str(lit), __ith__(i)))
            if not lit[2]:
                pos = lit
        elif not lit[2]:
            pos = lit
        else:
            pos = None
        prev = lit
    return conflict

# Merges two lists

def __merge_lists__(tomodify, toinsert):
    i = 0
    j = 0
    listlen = len(tomodify)

    for ins in toinsert:
        while i < listlen:
            if cmp(ins, tomodify[i]) <= 0:
                tomodify.insert(i, ins)
                listlen = listlen+1
                i = i+1
                j = j+1
                break
            i = i+1
        if i >= listlen:
            tomodify.extend(toinsert[j:])
            return

class PyAction:
    "SEPL Action Representation"

    def __init__(self, atype, args):
        self.type = atype
        self.args = args
        self.caction = None
        self.to_decrement = []

        if self.type is None:
            self.args.sort(PyAction.deep_cmp)

    def deep_cmp(self, other):
        if not isinstance(other, PyAction):
            return 1

        if self.type is None or other.type is None:
            if self.type is None:
                this = self.args
            else:
                this = [self]
            if other.type is None:
                other = other.args
            else:
                other = [other]
            for i in xrange(len(this)):
                if i > len(other):
                    return 1
                c = this[i].deep_cmp(other[i])
                if c != 0:
                    return c
            if len(other) > len(this):
                return -1

        if self.type < other.type:
            return -1
        elif self.type > other.type:
            return 1

        return cmp(self.args, other.args)

    def renamed(self, t, old_name, new_name, subtype):
        if self.type is None:
            ret = False
            for i in xrange(0,len(self.args)):
                if self.args[i].renamed(t, old_name, new_name, subtype):
                    ret = True
            return ret

        ret = False
        if len(self.args) > 0:
            argtype = action_info(self.type)[ARG_IDX]
            if argtype == t:
                for i in xrange(0,len(self.args)):
                    if self.args[i] == old_name:
                        self.args[i] = new_name
                        ret = True
            elif argtype == TLOC_T and t == LOC_T:
                for i in xrange(0,len(self.args)):
                    if self.args[i][0] == old_name:
                        self.args[i][0] = new_name
                        ret = True
                    break #NAT rule only uses TLOC and now second arg is mac, not list of loc
        return ret

    def translate(self):
        decr = False
        if self.type == Flow_action.NAT:
            self.caction = Flow_action(self.type, len(self.args))
            argtype = action_info(self.type)[ARG_IDX]
            check_fn = pred_type_info(argtype)[CHECK_IDX]
            if not self.caction.set_arg(0, check_fn(self.args[0], True)):
                raise Exception('Cannot set action argument.')
            # if dladdr given, set
            if len(self.args) > 1:
                self.caction.set_arg(1, create_eaddr(self.args[1].encode('utf-8')).hb_long())
        elif self.type == Flow_action.WAYPOINT:
            argtype = action_info(self.type)[ARG_IDX]
            check_fn = pred_type_info(argtype)[CHECK_IDX]
            self.caction = Flow_action(self.type, len(self.args))
            if self.caction is None:
                raise Exception('Out of memory.')
            args = [ check_fn(arg, True) for arg in self.args ]
            for i in xrange(len(args)):
                arg = args[i]
                self.to_decrement.append(arg)
                if not self.caction.set_arg(i, args[i]):
                    raise Exception('Cannot set action argument.')
        else:
            self.caction = Flow_action(self.type)
            if self.caction is None:
                raise Exception('Out of memory.')
            if len(self.args) > 0:
                if self.type == Flow_action.C_FUNC:
                    slist = strlist()
                    fn = self.args[0].encode('utf-8')
                    for ar in self.args[1:]:
                        slist.push_back(ar.encode('utf-8'))
                    success = __policy__.flow_util.set_action_argument(self.caction, fn, slist)
                else:
                    argtype = action_info(self.type)[ARG_IDX]
                    if argtype == LOC_T or argtype == HOST_T or argtype == USER_T or argtype == GROUP_T:
                        decr = True
                    check_fn = pred_type_info(argtype)[CHECK_IDX]
                    a = check_fn(self.args[0], True)
                    if decr:
                        self.to_decrement.append(a)
                    success = self.caction.set_arg(a)
                if not success:
                    raise Exception('Cannot set action argument.')

    def decrement_ids(self):
        global __policy__

        if self.type is None:
            for arg in self.args:
                arg.decrement_ids()
        else:
            for id in self.to_decrement:
                __policy__.authenticator.decrement_id(id)
            self.to_decrement = []

    def __le__(self, cond):
        if isinstance(cond, bool):
            cond = PyComplexPred(cond)
        elif not isinstance(cond, PyComplexPred):
            raise Exception('SEPL rule should be created with a predicate expression')

        if self.type is None:
            return PyRule(cond, self.args)
        return PyRule(cond, [self])

    def ustr(self):
        if self.type is None:
            return unicode('compose(' + ', '.join([action.ustr() for action in self.args]) + ')')

        if self.type == Flow_action.C_FUNC and __supported_fns__.has_key(self.args[0]):
            return unicode(self.args[0] + '(' + ', '.join(['\'' + a + '\'' for a in self.args[1:]])  + ')')
            
        s = __actions__[self.type][0] + '('
        if self.type == Flow_action.WAYPOINT or self.type == Flow_action.PY_FUNC or self.type == Flow_action.C_FUNC:
            argstr = ', '.join(['\'' + a + '\'' for a in self.args])
            s = s + argstr
        elif self.type == Flow_action.NAT:
            s = s + '\'' + self.args[0][0] + '\''
            if len(self.args) > 1:
                s = s + ', \'' + self.args[1] + '\''
        s = s + ')'
        return unicode(s)

class AsyncAction:
    "Wrapper to support asynchronous compiling of SEPL"

    def __init__(self, action_deferred):
        self.action = None
        self.condition = None
        self.pycond = None
        self.priority = None
        self.rule_type = None
        self.protected = None
        self.description = None
        self.comment = None
        self.d = action_deferred
        self.d.addCallback(self.set_action)
        __policy__.__add_rule_deferred__(self.d)

    def set_action(self, pyaction):
        # Should really see this error bc will have errback-ed, right?
        if not isinstance(pyaction, PyAction):
            log_and_raise('AsyncAction did not receive PyAction in callback.')
        self.action = pyaction

    def __le__(self, cond):
        global __policy__

        self.priority = __policy__.priority
        self.rule_type = __policy__.rule_type
        self.protected = __policy__.protected
        self.description = __policy__.description
        self.comment = __policy__.comment

        __policy__.set_description('')
        __policy__.set_comment('')

        self.pycond = cond
        if isinstance(cond, bool):
            self.d.addCallback(self.set_condition)
        elif isinstance(cond, AsyncPred):
            self.d.addCallback(self.wait_for_cond, cond)
            self.d.addCallback(self.set_condition)
        else:
            log_and_raise('SEPL rule should be created with a predicate expression')

        return self

    def wait_for_cond(self, tmp, cond):
        return cond.d

    def set_condition(self, tmp):
        global __policy__

        if isinstance(self.pycond, bool):
            self.condition = self.pycond
        else:
            self.condition = self.pycond.lhs

        r = self.action <= self.condition
        if self.priority is not None:
            r.priority = self.priority
        if self.rule_type is not None:
            r.rule_type = self.rule_type
        if self.protected is not None:
            r.protected  = self.protected
        r.description = self.description or r.description
        r.comment = self.comment or r.comment
        return r

# SEPL Rule Representation

class PyRule:
    "SEPL Rule Representation"

    def __init__(self, condition, actions, pri=None,
                 excep=False, protect=False, rtype='', descrip='', comment='',
                 expiration=0.0, order=None, pid=None, user=None, timestamp=None):
        global __policy__

        if pri is None:
            self.priority = __policy__.priority
        else:
            self.priority = pri

        self.rule_type = rtype
        self.exception = excep
        self.protected = protect
        self.description = descrip
        self.comment = comment
        self.expiration = expiration
        self.order = order
        self.policy_id = pid
        self.user = user
        self.timestamp = timestamp
        self.global_id = self.ids = self.cexprs = None

        self.actions = actions
        self.condition = condition
        self.dnf = condition.DNF(False)
        if not isinstance(self.dnf, bool):
            for expr in self.dnf:
                expr.sort()
            self.dnf.sort()

    def get_global_id(self):
        return self.global_id

    def get_priority(self):
        return self.priority

    def get_order(self):
        return self.order

    def change_priority(self, pri):
        if pri == self.priority:
            return True

        self.priority = pri
        if self.ids is None:
            return True

        success = True
        for id, enforcer in self.ids:
            if not enforcer.change_rule_priority(id, pri):
                success = False
        return success

    # returns True if the two rules could apply to the same flow
    # should take into account action?
    def overlaps(self, other):
        if isinstance(self.dnf, bool):
            return self.dnf
        if isinstance(other.dnf, bool):
            return other.dnf

        for a in self.dnf:
            for b in other.dnf:
                if len(a) >= len(b):
                    c = b[:]
                    __merge_lists__(c, a)
                else:
                    c = a[:]
                    __merge_lists__(c, b)
                if not __conjunction_conflict__(c):
                    return True
        return False

    # Checks that there are no conflicts within a single rule
    def verify(self):
        if isinstance(self.dnf, bool):
            return True

        valid = True
        for i in xrange(len(self.dnf)):
            if __conjunction_conflict__(self.dnf[i], True, i):
                valid = False
        return valid

    # decrements ids used in both actions and condition, assuming both
    # will be reset, or the rule will be garbage collected
    def decrement_ids(self):
        global __policy__

        done = []
        if not isinstance(self.dnf, bool):
            for orexp in self.dnf:
                for lit in orexp:
                    t = pred_info(lit[0])[TYPE_IDX]
                    if t == LOC_T or t == HOST_T or t == USER_T or t == GROUP_T:
                        if lit not in done:
                            __policy__.authenticator.decrement_id(lit[1])
                            done.append(lit)
        for action in self.actions:
            action.decrement_ids()

    def translate(self):
        self.cexprs = []

        if isinstance(self.dnf, bool) and not self.dnf:
            if isinstance(self.condition, PyComplexPred) or isinstance(self.condition, PyLiteral):
                s = self.condition.ustr()
            else:
                s = str(self.condition)
            lg.error("Rule condition %s always evaluates to False - not translating" % s)
            return

        for action in self.actions:
            action.translate()

        if isinstance(self.dnf, bool):
            cexpr = Flow_expr(0)
            if cexpr is None:
                raise Exception('Out of memory.')
            self.cexprs.append(cexpr)
            return

        for orexp in self.dnf:
            preds = []
            npreds = []
            fn_lits = []
            for lit in orexp:
                if lit[0] == Flow_expr.FUNC:
                    fn_lits.append(lit)
                elif lit[2]:
                    npreds.append(lit)
                else:
                    preds.append(lit)

            cexpr = Flow_expr(len(preds) + len(npreds))
            if cexpr is None:
                raise Exception('Out of memory.')

            i = 0
            if len(preds) > 0:
                preds.sort()
                for lit in preds:
                    if not cexpr.set_pred(i, lit[0], lit[1]):
                        raise Exception('Cannot set predicate.')
                    i = i + 1

            if len(npreds) > 0:
                npreds.sort()
                for lit in npreds:
                    if not cexpr.set_pred(i, lit[0] * -1, lit[1]):
                        raise Exception('Cannot set predicate.')
                    i = i + 1

            if len(fn_lits) > 0:
                if not cexpr.set_fn(__gen_rule_fn__(fn_lits)):
                    raise Exception('Cannot set predicate function.')

            self.cexprs.append(cexpr)

    # Installs a rule into the C++ Sepl_enforcer classifier

    def install(self, sepl_enforcer, nat_enforcer):
        # check if ids populated?

        self.ids = []
        for action in self.actions:
            for cexpr in self.cexprs:
                cexpr.global_id = self.global_id
                if action.type == Flow_action.NAT:
                    if nat_enforcer is None:
                        lg.error('Cannot add NAT rule with nat_enforcer == None')
                    else:
                        self.ids.append([nat_enforcer.add_rule(self.priority, cexpr, action.caction), nat_enforcer])
                else:
                    if sepl_enforcer is None:
                        lg.error('Cannot add SEPL rule with sepl_enforcer == None')
                    else:
                        self.ids.append([sepl_enforcer.add_rule(self.priority, cexpr, action.caction), sepl_enforcer])
            action.caction = None

        self.cexprs = None

    def remove(self, ids=None):
        if ids is None and self.ids is None:
            return True
        success = True
        clear = False
        if ids is None:
            ids = self.ids
            clear = True
        for id, enforcer in ids:
            if not enforcer.delete_rule(id):
                success = False
        if clear:
            self.ids = None
        return True

    def deep_cmp(self, other):
        if not isinstance(other, PyRule):
            return 1

        c = cmp(self.priority, other.priority)
        if c != 0:
            return c

        for i in xrange(len(self.actions)):
            if i > len(other.actions):
                return 1
            c = self.actions[i].deep_cmp(other.actions[i])
            if c != 0:
                return c
        if len(other.actions) > len(self.actions):
            return -1

        if isinstance(self.dnf, bool):
            if not isinstance(other.dnf, bool):
                return -1
        elif isinstance(other.dnf, bool):
            return 1

        return cmp(self.dnf, other.dnf)

    # expanded string form. 'string' member is the original rule string

    def action_ustr(self):
        if len(self.actions) > 1:
            return unicode('compose(' + ', '.join([action.ustr() for action in self.actions]) + ')')
        return unicode(', '.join([action.ustr() for action in self.actions]))
        
    def ustr(self, dnf=False):
        s = self.action_ustr() + ' <= '

        if not dnf:
            if isinstance(self.condition, PyComplexPred) or isinstance(self.condition, PyLiteral):
                s = s + self.condition.ustr()
            else:
                s = s + str(self.condition)
        else:
            if isinstance(self.dnf, bool):
                s = s + str(self.dnf)
            else:
                for orexp in self.dnf:
                    if len(orexp) > 1:
                        s = s + '(' + ' ^ '.join([str(andexp) for andexp in orexp]) + ') | '
                    else:
                        s = s + str(orexp[0]) + ' | '
                s = s[:-3]
        return unicode(s)
