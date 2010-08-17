# Copyright 2008 (C) Nicira, Inc.

from nox.ext.apps.sepl.declare import *

def failed(tmp):
    pass

def succeeded(tmp):
    if tmp != None:
        print 'Succeeded when should have failed'

def check_fail(fn, *args):
    try:
        async = fn(*args)
        async.d.addCallback(succeeded)
        async.d.addErrback(failed)
    except SeplDeclarationError:
        pass

set_priority(0)

allow() <= locsrc('sepl_directory;loc1')
allow() <= ~locsrc('sepl_directory;loc1')
check_fail(locsrc, 'sepl_directory;host1')
check_fail(locsrc, 'sepl_directory;random')
check_fail(locsrc, 0x505400000003)
check_fail(locsrc, 14)
check_fail(locsrc, allow())

allow() <= locdst('sepl_directory;loc1')
allow() <= ~locdst('sepl_directory;loc1')
check_fail(locdst, 'sepl_directory;user1')
check_fail(locdst, 'sepl_directory;random')
check_fail(locdst, 0x505400000003)
check_fail(locdst, 14)
check_fail(locdst, allow())

allow() <= hsrc('sepl_directory;host1')
allow() <= ~hsrc('sepl_directory;host1')
check_fail(hsrc, 'sepl_directory;user1')
check_fail(hsrc, 'sepl_directory;random')
check_fail(hsrc, 0x505400000001)
check_fail(hsrc, 14)
check_fail(hsrc, allow())

allow() <= hdst('sepl_directory;host1')
allow() <= ~hdst('sepl_directory;host1')
check_fail(hdst, 'sepl_directory;loc1')
check_fail(hdst, 'sepl_directory;random')
check_fail(hdst, 0x505400000001)
check_fail(hdst, 14)
check_fail(hdst, allow())

allow() <= usrc('sepl_directory;user1')
allow() <= ~usrc('sepl_directory;user1')
check_fail(usrc, 'sepl_directory;host1')
check_fail(usrc, 'sepl_directory;random')
check_fail(usrc, 0x505400000001)
check_fail(usrc, 14)
check_fail(usrc, allow())

allow() <= udst('sepl_directory;user1')
allow() <= ~udst('sepl_directory;user1')
check_fail(udst, 'sepl_directory;host1')
check_fail(udst, 'sepl_directory;random')
check_fail(udst, 0x505400000001)
check_fail(udst, 14)
check_fail(udst, allow())

allow() <= isConnRequest()
allow() <= isConnResponse()
allow() <= conn_role(REQUEST)
allow() <= ~isConnRequest()
allow() <= ~isConnResponse()
allow() <= ~conn_role(RESPONSE)

allow() <= protocol('arp')
allow() <= protocol('http')
allow() <= protocol('tcp_http')
allow() <= protocol('ipv4_tcp_http')
allow() <= protocol(0x0800, None, 80)
allow() <= ~protocol('arp')
allow() <= ~protocol('http')
allow() <= ~protocol('tcp_http')
allow() <= ~protocol('ipv4_tcp_http')
allow() <= ~protocol(0x0800, None, 80)
check_fail(protocol, 80)
check_fail(protocol, 'noproto')
check_fail(protocol, 'a', None, None)
check_fail(protocol, 1, None, None, None)
check_fail(protocol, allow())

allow() <= subnetdst('255.255.0.0/16')
allow() <= subnetdst('1.0.1.0/24')
allow() <= subnetdst('1.0.1.0/20')
allow() <= subnetdst('1.0.1.0/0')
allow() <= subnetdst('1.0.1.0/32')
allow() <= ~subnetdst('255.255.0.0/16')
allow() <= ~subnetdst('1.0.1.0/24')
check_fail(subnetdst, '1.1.1.1/33')
check_fail(subnetdst, '1.1.1.1/a')
check_fail(subnetdst, '1.1.1.1/-1')

allow() <= dlvlan(131)
allow() <= dlvlan(long(0x0fff))
allow() <= dlvlan(0)
allow() <= ~dlvlan(0x0801)
allow() <= ~dlvlan(0x0fff)
allow() <= ~dlvlan(0)
check_fail(dlvlan, '0x1ff')
check_fail(dlvlan, 0x1000)
check_fail(dlvlan, allow())

allow() <= dlsrc('\x00\x00\x00\x89\x45\x67')
allow() <= dlsrc('ab:cd:ef:12:34:56')
allow() <= dlsrc('\xab\xcd\xef\x12\x34\x56')
allow() <= dlsrc(0xabcdef123456)
allow() <= dlsrc(0xabcdef12345612) # this gets truncated - correct behavior?
allow() <= dlsrc('ff:ff:ff:ff:ff:ff')
allow() <= ~dlsrc('\x00\x00\x00\x89\x45\x67')
allow() <= ~dlsrc('ab:cd:ef:12:34:56')
allow() <= ~dlsrc('\xab\xcd\xef\x12\x34\x56')
allow() <= ~dlsrc(0xabcdef123456)
allow() <= ~dlsrc(0xabcdef12345612) # this gets truncated - correct behavior?
allow() <= ~dlsrc('ff:ff:ff:ff:ff:ff')
check_fail(dlsrc, 'ab:cd:ef:12:34:')
check_fail(dlsrc, 'ab:cd:ef:12:34')
check_fail(dlsrc, 'ab:cd:ef:12:344')
check_fail(dlsrc, 'asdk')
check_fail(dlsrc, '\xab\xcd\xef\x12\x34')
check_fail(dlsrc, '\xab\xcd\xef\x12\x34\x12\x34')
check_fail(dlsrc, ':')
check_fail(dlsrc, allow())

allow() <= dldst('\x00\x00\x00\x89\x45\x67')
allow() <= dldst('ab:cd:ef:12:34:56')
allow() <= dldst('\xab\xcd\xef\x12\x34\x56')
allow() <= dldst(0xabcdef123456)
allow() <= dldst(0xabcdef12345612) # this gets truncated - correct behavior?
allow() <= dldst('ff:ff:ff:ff:ff:ff')
allow() <= ~dldst('\x00\x00\x00\x89\x45\x67')
allow() <= ~dldst('ab:cd:ef:12:34:56')
allow() <= ~dldst('\xab\xcd\xef\x12\x34\x56')
allow() <= ~dldst(0xabcdef123456)
allow() <= ~dldst(0xabcdef12345612) # this gets truncated - correct behavior?
allow() <= ~dldst('ff:ff:ff:ff:ff:ff')
check_fail(dldst, 'ab:cd:ef:12:34:')
check_fail(dldst, 'ab:cd:ef:12:34')
check_fail(dldst, 'ab:cd:ef:12:344')
check_fail(dldst, 'asdk')
check_fail(dldst, '\xab\xcd\xef\x12\x34')
check_fail(dldst, '\xab\xcd\xef\x12\x34\x12\x34')
check_fail(dldst, ':')
check_fail(dldst, allow())

allow() <= dltype(0x0800)
allow() <= dltype(long(0xffff))
allow() <= dltype(0)
allow() <= ~dltype(0x0800)
allow() <= ~dltype(0xffff)
allow() <= ~dltype(0)
check_fail(dltype, '0x1ff')
check_fail(dltype, 0x10000)
check_fail(dltype, allow())

allow() <= nwsrc('128.2.2.1')
allow() <= nwsrc(0)
allow() <= nwsrc(0x12345678)
allow() <= nwsrc(long(0x12345678))
allow() <= nwsrc('255.255.255.255')
allow() <= ~nwsrc('128.2.2.1')
allow() <= ~nwsrc(0x12345678)
allow() <= ~nwsrc(long(0x12345678))
allow() <= ~nwsrc('255.255.255.255')
allow() <= ~nwsrc(0)
check_fail(nwsrc, 0x100000000)
check_fail(nwsrc, '8768.1.1.1')
check_fail(nwsrc, '12.')
check_fail(nwsrc, allow())

allow() <= nwdst('128.2.2.1')
allow() <= nwdst(0)
allow() <= ~nwdst(0)
allow() <= nwdst(0x12345678)
allow() <= nwdst(long(0x12345678))
allow() <= nwdst('255.255.255.255')
allow() <= ~nwdst('128.2.2.1')
allow() <= ~nwdst(0x12345678)
allow() <= ~nwdst(long(0x12345678))
allow() <= ~nwdst('255.255.255.255')
allow() <= ~nwdst(0)
check_fail(nwdst, 0x100000000)
check_fail(nwdst, '8768.1')
check_fail(nwdst, '12.')
check_fail(nwdst, allow())

allow() <= nwproto(17)
allow() <= nwproto(long(17))
allow() <= nwproto(0xff)
allow() <= nwproto(long(0xff))
allow() <= nwproto(0)
allow() <= ~nwproto(17)
allow() <= ~nwproto(long(17))
allow() <= ~nwproto(0xff)
allow() <= ~nwproto(long(0xff))
allow() <= ~nwproto(0)
check_fail(nwproto, 0x100)
check_fail(nwproto, '17')
check_fail(nwproto, 'hello')
check_fail(nwproto, allow())

allow() <= tpsrc(80)
allow() <= tpsrc(long(80))
allow() <= tpsrc(0xffff)
allow() <= tpsrc(long(0xffff))
allow() <= tpsrc(0)
allow() <= ~tpsrc(80)
allow() <= ~tpsrc(long(80))
allow() <= ~tpsrc(0xffff)
allow() <= ~tpsrc(long(0xffff))
allow() <= ~tpsrc(0)
check_fail(tpsrc, 0x10000)
check_fail(tpsrc, 'hello')
check_fail(tpsrc, '\xff')
check_fail(tpsrc, allow())

allow() <= tpdst(80)
allow() <= tpdst(long(80))
allow() <= tpdst(0xffff)
allow() <= tpdst(long(0xffff))
allow() <= tpdst(0)
allow() <= ~tpdst(80)
allow() <= ~tpdst(long(80))
allow() <= ~tpdst(0xffff)
allow() <= ~tpdst(long(0xffff))
allow() <= ~tpdst(0)
check_fail(tpdst, 0x10000)
check_fail(tpdst, 'hello')
check_fail(tpdst, '\xff')
check_fail(tpdst, allow())

#allow() <= in_group('sepl_directory;my_group', HSRC)
check_fail(in_group, allow(), HSRC)
check_fail(in_group, [allow()], TPSRC)

ip_group = [ 0x12345678, 0x3456789a, 0x56789012]
bad_ip_group = [ 0x12345678, '1.1.1.1.1', 0x56789012, 0x78901234 ]

eth_group = ['ab:cd:ef:12:34:56', 'ff:ff:ff:01:12:33']
bad_eth_group = [ 'ff:ff:ff:ff:ff:ff', 'ab:' ]

proto_group = ['http', 'ipv4', 'tcp_http']
bad_proto_group = ['http', 'ipv4', 'arp', 'mine']

allow() <= in_group(ip_group, NWSRC)
allow() <= in_group(eth_group, DLDST)
allow() <= in_group(proto_group, PROTOCOL)
allow() <= ~in_group(ip_group, NWSRC)
allow() <= ~in_group(eth_group, DLDST)
allow() <= ~in_group(proto_group, PROTOCOL)
check_fail(in_group, eth_group, NWDST)
check_fail(in_group, bad_ip_group, NWSRC)
check_fail(in_group, bad_eth_group, DLSRC)
check_fail(in_group, proto_group, NWDST)
check_fail(in_group, bad_proto_group, PROTOCOL)

def bad_fn(flow, something, somethingelse=1):
    return True
def bad_fn2():
    return True

allow() <= func('fn')
allow() <= func('fn2')
allow() <= ~func('fn')
allow() <= ~func('fn2')
check_fail(func, bad_fn)
check_fail(func, bad_fn2)
check_fail(func, 1)
check_fail(func, 'bad_fn')
check_fail(func, allow())

incr_priority()

waypoint('sepl_directory;host2') <= True
waypoint('sepl_directory;host1', 'sepl_directory;host2') <= True
check_fail(waypoint, 0x505400000001)
check_fail(waypoint, 'fakehost')
check_fail(waypoint, 'loc1')

py_action('fn') <= True
py_action('fn2') <= True
py_action('fn3') <= True
check_fail(py_action, 1)
check_fail(py_action, bad_fn)
check_fail(py_action, bad_fn2)

def err(res):
    print res

def got_a(arule, async2):
    async2.d.addCallback(got_b, arule)
    async2.d.addErrback(err)
    return arule

def got_b(brule, arule):
    if arule.deep_cmp(brule) != 0:
        print "Don't match:"
        print arule
        print brule
        raise Exception('%u: Rules do not match' % sys._getframe(1).f_lineno)
    return brule

def check_match(async1, async2):
    async1.d.addCallback(got_a, async2)
    async1.d.addErrback(err)

#a = waypoint('sepl_directory;host1', 'sepl_directory;host2')
#b = waypoint('sepl_directory;host1', 'sepl_directory;host2')

a = allow() <= ~locsrc('sepl_directory;loc1')
b = allow() <= ~(locsrc('sepl_directory;loc1'))
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') | locsrc('sepl_directory;loc2'))
b = allow() <= ~locsrc('sepl_directory;loc1') ^ ~locsrc('sepl_directory;loc2')
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2'))
b = allow() <= ~locsrc('sepl_directory;loc1') | ~locsrc('sepl_directory;loc2')
check_match(a, b)

a = allow() <= usrc('sepl_directory;user2') ^ ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2'))
b = allow() <= (~locsrc('sepl_directory;loc1') ^ usrc('sepl_directory;user2')) | (~locsrc('sepl_directory;loc2') ^ usrc('sepl_directory;user2'))
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) ^ ~(usrc('sepl_directory;user2') | usrc('sepl_directory;user2'))
b = allow() <= (~locsrc('sepl_directory;loc1') ^ ~usrc('sepl_directory;user2') ^ ~usrc('sepl_directory;user2')) | (~locsrc('sepl_directory;loc2') ^ ~usrc('sepl_directory;user2') ^ ~usrc('sepl_directory;user2'))
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) ^ protocol('http')
b = allow() <= (~locsrc('sepl_directory;loc1') ^ tpsrc(80)) | (~locsrc('sepl_directory;loc1') ^ tpdst(80)) | (~locsrc('sepl_directory;loc2') ^ tpsrc(80)) | (~locsrc('sepl_directory;loc2') ^ tpdst(80))
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) ^ ~protocol('http')
b = allow() <= (~locsrc('sepl_directory;loc1') ^ ~tpsrc(80) ^ ~tpdst(80)) | (~locsrc('sepl_directory;loc2') ^ ~tpsrc(80) ^ ~tpdst(80)) 
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) ^ in_group(ip_group, NWDST) ^ ~(hdst('sepl_directory;host1') | hdst('sepl_directory;host2'))
b = allow() <= (~locsrc('sepl_directory;loc1') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host1') ^ ~hdst('sepl_directory;host2'))
check_match(a, b)

a = allow() <= ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) ^ in_group(ip_group, NWDST) ^ ~(hdst('sepl_directory;host1') ^ hdst('sepl_directory;host2'))
b = allow() <= (~locsrc('sepl_directory;loc1') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc1') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host1')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x56789012) ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x3456789a) ^ ~hdst('sepl_directory;host2')) \
    | (~locsrc('sepl_directory;loc2') ^ nwdst(0x12345678) ^ ~hdst('sepl_directory;host2'))
check_match(a, b)

a = allow() <= ~in_group(ip_group, NWDST) ^ ~(locsrc('sepl_directory;loc1') ^ locsrc('sepl_directory;loc2')) 
b = allow() <= (~locsrc('sepl_directory;loc1') ^ ~nwdst(0x12345678) ^ ~nwdst(0x3456789a) ^ ~nwdst(0x56789012)) \
    | (~locsrc('sepl_directory;loc2') ^ ~nwdst(0x12345678) ^ ~nwdst(0x3456789a) ^ ~nwdst(0x56789012))
check_match(a, b)
