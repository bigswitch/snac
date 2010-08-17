# Copyright 2008 (C) Nicira, Inc.
from nox.ext.apps.sepl.sepl_directory import register_location, register_host,\
    register_user, register_switch_group, register_location_group,  \
    register_host_group, register_user_group, register_dladdr_group, \
    register_nwaddr_group, register_switch

addedAll = False
num_register = 0

def check(d):
    global num_register

    num_register = num_register + 1
    d.addCallback(register_success)
    d.addErrback(register_failed)

def register_success(res):
    global num_register

    num_register = num_register - 1
    if num_register == 0 and addedAll:
        print 'Registration complete'

def register_failed(res):
    print 'Registration failed'

check(register_switch('switch1', 0x505400000003))
check(register_switch('switch2', 0x505400000006))
check(register_location('loc1', 0x505400000003, 0, 'eth0'))
check(register_location('loc2', 0x505400000006, 0, 'eth0'))
check(register_host('host1', dladdr=0x505400000001))
check(register_host('host2', dladdr=0x505400000002))
check(register_user('user1'))
check(register_user('user2'))

check(register_switch_group('s1group', 'my switch group', ['switch1'], []))
check(register_switch_group('s2group', 'my 2nd switch group', ['switch2'], []))
check(register_location_group('l1group', 'my loc group', ['loc1'], []))
check(register_location_group('l2group', 'my 2nd loc group', ['loc2'], []))
check(register_location_group('l3group', 'roup', [], []))
check(register_host_group('h1group', 'my host group', ['host1'], []))
check(register_host_group('h2group', 'my 2nd host group', ['host2'], []))
check(register_user_group('u1group', 'my user group', ['user1'], []))
check(register_user_group('u2group', 'my 2nd user group', ['user2'], []))

check(register_location_group('all', 'my all loc group', [], ['l1group', 'l2group']))
check(register_host_group('all', 'my all host group', [], ['h1group', 'h2group']))
check(register_user_group('all', 'my all user group', [], ['u1group', 'u2group']))

check(register_dladdr_group('registered-macs', 'mac group',
                            [ 0x505400000001, 0x505400000002], []))
check(register_nwaddr_group('registered-ips', 'ip group',
                            [ '192.168.1.1', '192.168.1.2'], []))

addedAll = True
if num_register == 0:
    print 'Registration complete'
