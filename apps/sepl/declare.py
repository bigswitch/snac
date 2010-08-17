# Copyright 2008 (C) Nicira, Inc.

import sys
import compile
import logging
from twisted.internet import defer
from nox.netapps.authenticator.pyflowutil import Flow_expr, Flow_action
from nox.ext.apps.sepl.compile import PyAction, PyLiteral,\
    PyComplexPred, AsyncAction, AsyncPred
from twisted.python.failure import Failure

lg = logging.getLogger("declare")

# Current SEPL Variables that can be used when declaring groups

LOCSRC = Flow_expr.LOCSRC
LOCDST = Flow_expr.LOCDST
HSRC = Flow_expr.HSRC
HDST = Flow_expr.HDST
USRC = Flow_expr.USRC
UDST = Flow_expr.UDST
DLVLAN = Flow_expr.DLVLAN
DLSRC = Flow_expr.DLSRC
DLDST = Flow_expr.DLDST
DLTYPE = Flow_expr.DLTYPE
NWSRC = Flow_expr.NWSRC
NWDST = Flow_expr.NWDST
NWPROTO = Flow_expr.NWPROTO
TPSRC = Flow_expr.TPSRC
TPDST = Flow_expr.TPDST
PROTOCOL = compile.PROTO
SWSRC = compile.SWSRC
SWDST = compile.SWDST

PNAMES = \
{
    compile.pred_info(LOCSRC)[compile.STR_IDX].upper()   : LOCSRC,
    compile.pred_info(LOCDST)[compile.STR_IDX].upper()   : LOCDST,
    compile.pred_info(HSRC)[compile.STR_IDX].upper()    : HSRC,
    compile.pred_info(HDST)[compile.STR_IDX].upper()    : HDST,
    compile.pred_info(USRC)[compile.STR_IDX].upper()    : USRC,
    compile.pred_info(UDST)[compile.STR_IDX].upper()    : UDST,
    compile.pred_info(DLVLAN)[compile.STR_IDX].upper()  : DLVLAN,
    compile.pred_info(DLSRC)[compile.STR_IDX].upper()   : DLSRC,
    compile.pred_info(DLDST)[compile.STR_IDX].upper()   : DLDST,
    compile.pred_info(DLTYPE)[compile.STR_IDX].upper()  : DLTYPE,
    compile.pred_info(NWSRC)[compile.STR_IDX].upper()   : NWSRC,
    compile.pred_info(NWDST)[compile.STR_IDX].upper()   : NWDST,
    compile.pred_info(NWPROTO)[compile.STR_IDX].upper() : NWPROTO,
    compile.pred_info(TPSRC)[compile.STR_IDX].upper()   : TPSRC,
    compile.pred_info(TPDST)[compile.STR_IDX].upper()   : TPDST,
    compile.pred_info(PROTOCOL)[compile.STR_IDX].upper()   : PROTOCOL,
    compile.pred_info(SWSRC)[compile.STR_IDX].upper()   : SWSRC,
    compile.pred_info(SWDST)[compile.STR_IDX].upper()   : SWDST
}

REQUEST = compile.ROLE_VALS[Flow_expr.REQUEST]
RESPONSE = compile.ROLE_VALS[Flow_expr.RESPONSE]

ROLES = \
{
    REQUEST : Flow_expr.REQUEST,
    RESPONSE : Flow_expr.RESPONSE
}


# SEPL language supported group types

SW_T = compile.SW_T
LOC_T = compile.LOC_T
HOST_T = compile.HOST_T
USER_T = compile.USER_T

def log_and_raise(err, obj=None):
    if obj != None:
        if callable(obj):
            s = obj.func_name
        else:
            try:
                if not isinstance(obj, basestring):
                    s = unicode(str(obj), 'utf-8')
                else:
                    if isinstance(obj, str):
                        s = unicode(obj, 'utf-8')
                    else:
                        s = obj
            except Exception, e:
                s = ''
        if s != '':
            err = err + (' (%s)' % s)
        
    lg.error(err)
    if isinstance(err, unicode):
        raise Exception(err.encode('utf-8'))
    else:
        raise Exception(err)

# Sets priority level declared rules should possess

def set_priority(pri):
    if not compile.__policy__.set_priority(pri):
        log_and_raise('Priority cannot be set - invalid value.', pri)

# Increments and decrements current priority level respectively
def incr_priority():
    if not compile.__policy__.incr_priority():
        log_and_raise('Priority has reached max - cannot be incremented.')

def decr_priority():
    if not compile.__policy__.decr_priority():
        log_and_raise('Priority has reached min - cannot be decremented.')

def cascade():
    return incr_priority()

def set_rule_type(rtype):
    if not compile.__policy__.set_rule_type(rtype):
        log_and_raise('Rule type cannot be set - invalid value.', rtype)

def set_protected(prot):
    if not compile.__policy__.set_protected(prot):
        log_and_raise('Protected bool cannot be set - invalid value.', prot)

def set_description(desc):
    if not compile.__policy__.set_description(desc):
        log_and_raise('Description cannot be set - invalid value.', desc)

def set_comment(comment):
    if not compile.__policy__.set_comment(comment):
        log_and_raise('Comment cannot be set - invalid value.', comment)

# Group helper fns

def __check_list__(check_fn, group):
    if not isinstance(group, list) and not isinstance(group, tuple):
        return defer.succeed([None, group])

    ds = []
    args = []
    __add_checks__(ds, args, check_fn, group)
    d = defer.DeferredList(ds, consumeErrors=True)
    d.addCallback(__check_list2__, args)
    return d

def __check_list2__(reslist, args):
    expanded = []
    for i in xrange(len(reslist)):
        res = reslist[i]
        if res[0] == defer.FAILURE or res[1] is None:
            return [None, args[i]]
        expanded.append(res[1])
    return expanded

def __add_checks__(ds, args, check_fn, elem):
    if isinstance(elem, list) or isinstance(elem, tuple):
        for e in elem:
            __add_checks__(ds, args, check_fn, e)
    else:
        ds.append(check_fn(elem))
        args.append(elem)
    return ds

## Supported SEPL actions ##

def allow():
    async = AsyncAction(defer.Deferred())
    async.d.callback(PyAction(Flow_action.ALLOW, []))
    return async

def deny():
    async = AsyncAction(defer.Deferred())
    async.d.callback(PyAction(Flow_action.DENY, []))
    return async

def waypoint(*points):
    d = __check_list__(compile.host_check, points)
    d.addCallback(waypoint2)
    return AsyncAction(d)

def waypoint2(points):
    if len(points) == 0:
        log_and_raise('Waypoint host list should not be empty.')
    if points[0] is None:
        log_and_raise('Waypoint action expects a list of registered host principals.', points[1])
    return PyAction(Flow_action.WAYPOINT, points)

def c_action(cfn_name, *args):
    d = compile.c_action_check(cfn_name, args)
    d.addCallback(c_action2, cfn_name, args)
    return AsyncAction(d)

def c_action2(cfn_args, cfn_name, args):
    if cfn_args is None:
        log_and_raise('c_action expects a string mapping to a C++ fn and valid arguments.', cfn_name)
    return PyAction(Flow_action.C_FUNC, cfn_args)

def authenticate_host(*args):
    return c_action('authenticate_host', *args)

def allow_no_nat():
    return c_action('allow_no_nat')

def http_proxy_redirect(portal_mac, portal_ip, portal_port):
    return c_action('http_proxy_redirect', portal_mac, portal_ip, portal_port)

def http_proxy_undo_redirect(proxy_mac, proxy_ip, proxy_port):
    return c_action('http_proxy_undo_redirect', proxy_mac, proxy_ip, proxy_port)

def http_redirect(*args):
    return c_action('http_redirect', *args)

def py_action(py_fn):
    d = compile.py_action_check(py_fn)
    d.addCallback(py_action2)
    return AsyncAction(d)

def py_action2(pfn):
    if pfn is None:
        log_and_raise('py_action expects a callable function taking a single argument (the flow).')
    return PyAction(Flow_action.PY_FUNC, [pfn])

def nat(loc, dl=None):
    d = compile.nat_loc_check(loc)
    d.addCallback(nat2, dl)
    return AsyncAction(d)

def nat2(loc, dl):
    if loc is None:
        log_and_raise("NAT action expects a valid location.", loc)
    if dl is not None:
        d = compile.dladdr_check(dl)
        d.addCallback(nat3, loc, dl)
        return d
    return nat3(None, loc, None)

def nat3(dlval, loc, dlarg):
    if dlval is None and dlarg is not None:
        log_and_raise("NAT action excpects a valid MAC address.", dlarg)
    if dlval == None:
        arg = (loc,)
    else:
        arg = (loc, dlval)
    return PyAction(Flow_action.NAT, arg)

def compose(*args):
    if len(args) == 0:
        log_and_raise("compose() expects a sequence of at least one sepl action.")
    ds = []
    for arg in args:
        if not isinstance(arg, AsyncAction):
            log_and_raise("compose() expects a sequence of sepl actions.")
        else:
            ds.append(arg.d)
    d = defer.DeferredList(ds)
    d.addCallback(compose2, args)
    return AsyncAction(d)

def compose2(reslist, asyncs):
    actions = []
    for i in xrange(len(reslist)):
        res = reslist[i]
        if res[0] == defer.FAILURE:
            log_and_raise("compose() action %u is invalid." % i)
        else:
            actions.append(asyncs[i].action)

    fn = False
    deny = False
    non_deny = False
    allow = False

    i = 0
    while i < len(actions):
        action = actions[i]
        if action.type == Flow_action.DENY:
            if deny:
                lg.error("DENY action repeated - ignoring duplicate.")
                actions.pop(i)
                continue
            elif fn or non_deny:
                log_and_raise("DENY action conflicts with non-DENY actions.")
            deny = True
        elif action.type == Flow_action.C_FUNC or action.type == Flow_action.PY_FUNC:
            if fn:
                log_and_raise("Cannot have more than function action - only one executed at runtime.")
            elif deny or non_deny:
                log_and_raise("Fn action conflicts with NAC action (fn never called).")
            fn = True
        else:
            if deny:
                log_and_raise("NAC action conflicts with DENY.")
            elif fn:
                log_and_raise("NAC action conflicts with fn action (fn never called).")
            if action.type == Flow_action.ALLOW:
                if allow:
                    lg.error("ALLOW action repeated - ignoring duplicate.")
                    actions.pop(i)
                    continue
                elif non_deny:
                    lg.error("ALLOW action unnecessary with NAC action - ignoring.")
                    actions.pop(i)
                    continue
                allow = True
            non_deny = True
        i = i + 1

    return PyAction(None, actions)

## Supported SEPL predicates ##

def dlvlan(vlan):
    d = compile.dlvlan_check(vlan)
    d.addCallback(dlvlan2, vlan)
    return AsyncPred(d)

def dlvlan2(val, arg):
    if val is None:
        log_and_raise('dlvlan predicate expects a valid vlan id.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.DLVLAN, [val]))
    
def dlsrc(dladdr):
    d = compile.dladdr_check(dladdr)
    d.addCallback(dlsrc2, dladdr)
    return AsyncPred(d)

def dlsrc2(val, arg):
    if val is None:
        log_and_raise('dlsrc predicate expects a valid link layer address.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.DLSRC, [val]))

def dldst(dladdr):
    d = compile.dladdr_check(dladdr)
    d.addCallback(dldst2, dladdr)
    return AsyncPred(d)

def dldst2(val, arg):
    if val is None:
        log_and_raise('dldst predicate expects a valid link layer address.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.DLDST, [val]))

def dltype(dlt):
    d = compile.dltype_check(dlt)
    d.addCallback(dltype2, dlt)
    return AsyncPred(d)

def dltype2(val, arg):
    if val is None:
        log_and_raise('dltype predicate expects a valid dl type.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.DLTYPE, [val]))

def nwsrc(nwaddr):
    d = compile.nwaddr_check(nwaddr)
    d.addCallback(nwsrc2, nwaddr)
    return AsyncPred(d)

def nwsrc2(val, arg):
    if val is None:
        log_and_raise('nwsrc predicate expects a valid network address.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.NWSRC, [val]))

def nwdst(nwaddr):
    d = compile.nwaddr_check(nwaddr)
    d.addCallback(nwdst2, nwaddr)
    return AsyncPred(d)

def nwdst2(val, arg):
    if val is None:
        log_and_raise('nwdst predicate expects a valid network address.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.NWDST, [val]))

def nwproto(proto):
    d = compile.nwproto_check(proto)
    d.addCallback(nwproto2, proto)
    return AsyncPred(d)

def nwproto2(val, arg):
    if val is None:
        log_and_raise('nwproto predicate expects a valid network protocol.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.NWPROTO, [val]))

def tpsrc(tport):
    d = compile.tport_check(tport)
    d.addCallback(tpsrc2, tport)
    return AsyncPred(d)

def tpsrc2(val, arg):
    if val is None:
        log_and_raise('tpsrc predicate expects a valid transport protocol port.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.TPSRC, [val]))

def tpdst(tport):
    d = compile.tport_check(tport)
    d.addCallback(tpdst2, tport)
    return AsyncPred(d)

def tpdst2(val, arg):
    if val is None:
        log_and_raise('tpdst predicate expects a valid transport protocol port.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.TPDST, [val]))

def subnetsrc(subnet):
    d = compile.subnet_check(subnet)
    d.addCallback(subnetsrc2, subnet)
    return AsyncPred(d)

def subnetsrc2(val, arg):
    if val is None:
        log_and_raise('subnetsrc predicated expects a full IP address with the CIDR prefix length.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.SUBNETSRC, [val]))

def subnetdst(subnet):
    d = compile.subnet_check(subnet)
    d.addCallback(subnetdst2, subnet)
    return AsyncPred(d)

def subnetdst2(val, arg):
    if val is None:
        log_and_raise('subnetdst predicated expects a full IP address with the CIDR prefix length.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.SUBNETDST, [val]))

def locsrc(loc):
    d = compile.loc_check(loc)
    d.addCallback(locsrc2, loc)
    return AsyncPred(d)

def locsrc2(val, arg):
    if val is None:
        log_and_raise('locsrc predicate expects a registered location principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.LOCSRC, [val]))

def locdst(loc):
    d = compile.loc_check(loc)
    d.addCallback(locdst2, loc)
    return AsyncPred(d)

def locdst2(val, arg):
    if val is None:
        log_and_raise('locdst predicate expects a registered location principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.LOCDST, [val]))

def hsrc(host):
    d = compile.host_check(host)
    d.addCallback(hsrc2, host)
    return AsyncPred(d)

def hsrc2(val, arg):
    if val is None:
        log_and_raise('hsrc predicate expects a registered host principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.HSRC, [val]))

def hdst(host):
    d = compile.host_check(host)
    d.addCallback(hdst2, host)
    return AsyncPred(d)

def hdst2(val, arg):
    if val is None:
        log_and_raise('hdst predicate expects a registered host principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.HDST, [val]))

def usrc(user):
    d = compile.user_check(user)
    d.addCallback(usrc2, user)
    return AsyncPred(d)

def usrc2(val, arg):
    if val is None:
        log_and_raise('usrc predicate expects a registered user principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.USRC, [val]))

def udst(user):
    d = compile.user_check(user)
    d.addCallback(udst2, user)
    return AsyncPred(d)

def udst2(val, arg):
    if val is None:
        log_and_raise('udst predicate expects a registered user principal.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.UDST, [val]))

def conn_role(role):
    if isinstance(role, basestring):
        role = role.upper()
        if not ROLES.has_key(role):
            log_and_raise('conn_role predicate expects a role.', role)
        role = ROLES[role]

    d = compile.role_check(role)
    d.addCallback(conn_role2, role)
    return AsyncPred(d)

def conn_role2(val, arg):
    if val is None:
        log_and_raise('conn_role predicate expects a role.', arg)
    return PyComplexPred(PyLiteral(Flow_expr.CONN_ROLE, [val]))

def isConnRequest():
    async = AsyncPred(defer.Deferred())
    async.d.callback(PyComplexPred(PyLiteral(Flow_expr.CONN_ROLE, [Flow_expr.REQUEST])))
    return async

def isConnResponse():
    async = AsyncPred(defer.Deferred())
    async.d.callback(PyComplexPred(PyLiteral(Flow_expr.CONN_ROLE, [Flow_expr.RESPONSE])))
    return async

def protocol(*proto):
    if len(proto) == 1:
        proto = proto[0]
    d = compile.proto_check(proto)
    d.addCallback(protocol2, proto)
    return AsyncPred(d)

def protocol2(val, arg):
    if val is None:
        log_and_raise('protocol predicate expects a defined protocol.', arg)
    if isinstance(val, basestring):
        val = [val]
    return PyComplexPred(PyLiteral(compile.PROTO, val))

# Helper fn

def __valid_principal__(p):
    if not (isinstance(p, int) or isinstance(p, long)):
        return None
    pinfo = compile.pred_info(p)
    if pinfo is None or pinfo[compile.TYPE_IDX] is None:
        return None
    return pinfo
    
def in_group(group, ptype):
    if isinstance(ptype, basestring):
        ptype = ptype.upper()
        if not PNAMES.has_key(ptype):
            log_and_raise('in_group predicate expects a SEPL atomic type string as the second argument.', ptype)
        ptype = PNAMES[ptype]

    pinfo = __valid_principal__(ptype)
    if pinfo is None:
        log_and_raise('in_group predicate expects a SEPL atomic type as the second argument.', ptype)

    if pinfo[compile.GROUPABLE_IDX]:
        if not (isinstance(group, list) or isinstance(group, tuple)):
            d = compile.group_check(group, pinfo[compile.TYPE_IDX])
            d.addCallback(in_group2, ptype, pinfo, group)
            return AsyncPred(d)
        elif pinfo[compile.TYPE_IDX] == SW_T:
            log_and_raise('in_group cannot be declared over an unregistered switch group.')

    tinfo = compile.pred_type_info(pinfo[compile.TYPE_IDX])

    d = __check_list__(tinfo[compile.CHECK_IDX], group)
    d.addCallback(in_group_exp, ptype)
    return AsyncPred(d)

def in_group2(val, ptype, pinfo, arg):
    if val is None:
        log_and_raise('in_group predicate expects a valid registered group string name.', arg)

    if pinfo[compile.SIDE_IDX] == compile.SRC_S:
        if ptype == compile.SWSRC or ptype == Flow_expr.LOCSRC or \
                ptype == Flow_expr.HSRC:
            gtype = Flow_expr.HGROUPSRC
        elif ptype == Flow_expr.USRC:
            gtype = Flow_expr.UGROUPSRC
        elif ptype == Flow_expr.DLSRC or ptype == Flow_expr.NWSRC:
            gtype = Flow_expr.ADDRGROUPSRC
        else:
            log_and_raise('unknown ptype value')
    elif pinfo[compile.SIDE_IDX] == compile.DST_S:
        if ptype == compile.SWDST or ptype == Flow_expr.LOCDST or \
                ptype == Flow_expr.HDST:
            gtype = Flow_expr.HGROUPDST
        elif ptype == Flow_expr.UDST:
            gtype = Flow_expr.UGROUPDST
        elif ptype == Flow_expr.DLDST or ptype == Flow_expr.NWDST:
            gtype = Flow_expr.ADDRGROUPDST
        else:
            log_and_raise('unknown ptype value')
    else:
        log_and_raise('unknown SIDE value in in_group definition.')
    return PyComplexPred(PyLiteral(gtype, [val, ptype]))

def in_group_exp(val, ptype):
    if len(val) == 0:
        log_and_raise("in_group value list should not be empty.")
    if val[0] is None:
        log_and_raise("in_group expects a valid sequence of predicate values.", val[1])
    return PyComplexPred(PyLiteral(compile.EXPGROUP, [val, ptype]))

def func(fn):
    d = compile.func_check(fn)
    d.addCallback(func2, fn)
    return AsyncPred(d)

def func2(fn, arg):
    if fn is None:
        log_and_raise('func predicate expects a callable function taking a single argument (the flow).', arg)
    return PyComplexPred(PyLiteral(Flow_expr.FUNC, [fn]))
