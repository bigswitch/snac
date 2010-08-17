# Copyright 2008 (C) Nicira, Inc.

import sys
from nox.ext.apps.sepl.sepl_directory import register_switch, register_location, \
    register_host, register_user, register_host_group, register_user_group
from nox.ext.apps.sepl.compile import register_py_func
from twisted.python import log

num_register = 0
addedAll = False

def check(d, should_pass):
    global num_register

    num_register = num_register + 1
    d.addCallback(register_success, should_pass)
    d.addErrback(register_failed, should_pass)

def check_dir_pass(d):
    check(d, True)
    return d

def check_dir_fail(d):
    check(d, False)
    return d

def register_success(res, should_pass):
    global num_register

    if should_pass == False:
        log.err('Register %s should have failed.' % str(res))

    num_register = num_register - 1
    if num_register == 0 and addedAll:
        print 'Registration test complete'

def register_failed(res, should_pass):
    global num_register

    if should_pass == True:
        log.err('Register should have passed')
    
    num_register = num_register - 1
    if num_register == 0 and addedAll:
        print 'Registration test complete'

def unwrap_reg_loc(switch_info, name, switch, port, port_name):
    check_dir_pass(register_location(name, switch, port, port_name))

d = check_dir_pass(register_switch('switch1', 0x505400000004))
d.addCallback(unwrap_reg_loc, 'loc1', 'switch1', 1, 'eth0')
check_dir_pass(register_location('loc2', 0x505400000003, 0, 'eth0'))
check_dir_pass(register_location('loc3', 0x505400000003, 1, 'eth1'))

check_dir_pass(register_host('host1', dladdr=0x505400000001, is_gateway=True))
check_dir_pass(register_host('host2', dladdr=0x505400000002))

check_dir_pass(register_user('user1'))
check_dir_pass(register_user('user2'))

check_dir_fail(register_switch('switch1', 0x505400000004)) # dup entry
check_dir_fail(register_switch('switch2', 0x505400000004)) # dup entry

check_dir_fail(register_location('loc5', 0x505400000003, 0, 'eth0'))  # dup entry
check_dir_fail(register_location('loc6', 0x505400000003, 1, 'eth1'))  # dup entry
check_dir_fail(register_location('loc1', 0x505400000004, 1, 'eth1')) # dup entry
check_dir_fail(register_location('loc1', 0x505400000004, 2, 'eth2')) # diff addr

check_dir_fail(register_host('host1', dladdr=0x505400000001))  # dup entry
check_dir_fail(register_host('host2', dladdr=0x505400000002)) # dup entry
check_dir_fail(register_host('host1', dladdr=0x505400000003)) # diff val
check_dir_fail(register_host('host2', dladdr=0x505400000004))  # diff val
check_dir_fail(register_host('ost1', dladdr=0x505400000001)) # diff id
check_dir_fail(register_host('ost2', dladdr=0x505400000002))  # diff id
check_dir_fail(register_host('host1', dladdr=0x50540000000))   # diff new id
check_dir_fail(register_host('hst1', dladdr=0x505400000001))  # new name, existing id
check_dir_fail(register_host('hst2', dladdr=0x505400000002)) # new name, existing id

check_dir_fail(register_user('user1'))  # dup entry

check_dir_pass(register_host_group('my_group', 'a host group', ['host1'], []))

def fn(flow, tmp=2, tmp1=3):
    return True
def fn2(flow=2):
    return True
def fn3(flow):
    return True

if not register_py_func(fn):
    log.err("Could not register pyfunc %s" % fn.func_name)
if not register_py_func(fn2):
    log.err("Could not register pyfunc %s" % fn.func_name)
if not register_py_func(fn3):
    log.err("Could not register pyfunc %s" % fn.func_name)


addedAll = True
if num_register == 0:
    print "Registration test complete"
