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

from nox.ext.apps.sepl.sepl_directory import register_switch, register_location, \
    register_host, register_user, register_host_group, register_user_group

addedAll = False
num_register = 0

def check(d):
    global num_register

    num_register = num_register + 1
    d.addCallback(register_success)
    d.addErrback(register_failed)
    return d

def register_success(res):
    global num_register

    num_register = num_register - 1
    if num_register == 0 and addedAll:
        print 'Registration complete'
    return res

def register_failed(res):
    print 'Registration failed'

# REGISTER SWITCHES AND LOCATIONS

def register_switch_ports(switch_info, n_ports, start_port=0, name=None):
    for i in xrange(n_ports):
        port  = i + start_port
        if name == None:
            locname = switch_info.name+str(port)
        else:
            locname = name
        check(register_location(locname, switch_info.name, port))
    return switch_info

d = check(register_switch("marbles", 622687516026))
d.addCallback(register_switch_ports, 4)

d = check(register_switch("of3k", 94259811924))
d.addCallback(register_switch_ports, 4)

d = check(register_switch("of6k", 110887703091))
d.addCallback(register_switch_ports, 5)
d.addCallback(register_switch_ports, 2, 6)
d.addCallback(register_switch_ports, 1, 5, 'wireless')

# REGISTER HOSTS/USERS
check(register_host('grasshopper', dladdr=0x0090fb1858ac))
check(register_host('ladybug',     dladdr=0x0090fb18590c))

check(register_host('miwok',     dladdr=0x001aa08f9a95))
check(register_host('hardrock',  dladdr=0x0002e30f80a4))
check(register_host('badwater',  dladdr=0x00a0cc28a994))
check(register_host('leadville', dladdr=0x001a9240ac05))
check(register_host('javelina',  dladdr=0x0014c1325fd6))
check(register_host('gobi',      dladdr=0x001e906a7dfe))
check(register_host('emerson',   dladdr=0x001d09708d2e))
check(register_host('salsa',     dladdr=0x0015f26b68c6))
check(register_host('wahoos',    dladdr=0x001bb9a57fbc))
check(register_host('nox-ucb',   dladdr=0x001fc610c596))

check(register_host('nicira-bw',    dladdr=0x001a4b122ff8))
check(register_host('nicira-color', dladdr=0x001635571374))
check(register_host('netgear',      dladdr=0x000c4141ed0c))
check(register_host('gateway',      dladdr=0x000fb5acbf42))
check(register_host('airport',      dladdr=0x001b63f1d48b))

check(register_host('straits',  dladdr=0x000c42024fbb))
check(register_host('ramonas',  dladdr=0x001bb9bee9c5))
check(register_host('tandoori', dladdr=0x001e9067c7de))
check(register_host('nf2_name', dladdr=0x001a92b8dc4c))

check(register_host('little-pete', dladdr=0x00301bad504b))
check(register_host('kirks',       dladdr=0x0013205ee646))
check(register_host('leanhorse',   dladdr=0x001e902221eb))

check(register_host('combos',    dladdr=0x000db912eb1c))
check(register_host('combos2',   dladdr=0x000db912eb1d))
check(register_host('combos3',   dladdr=0x000db912eb1e))
check(register_host('combos-of', dladdr=0x4a2771ae64c1, is_gateway=True))
check(register_host('funyuns',   dladdr=0x000db912ec8c))
check(register_host('bugles',    dladdr=0x000db912ed38))

check(register_host('gunmetal', dladdr=0x0019dbce0d28))

check(register_host('vpn', dladdr=0x4e62a7f6c891))

check(register_host('dk-laptop-wifi',  dladdr=0x0016cbb6fbf6)) 
check(register_host('jl-laptop-wifi',  dladdr=0x001b63c27c91)) 
check(register_host('bp-laptop-wifi',  dladdr=0x000e35210056)) 
check(register_host('bp-laptop-wired', dladdr=0x000ae4256bb0)) 
check(register_host('ng-laptop-wifi',  dladdr=0x001ec2c2565d)) 
check(register_host('ss-laptop-wifi',  dladdr=0x001b63c68c4f)) 
check(register_host('ss-laptop-wired', dladdr=0x001b63938b95)) 
check(register_host('ka-laptop-wifi',  dladdr=0x001cbfc95543)) 
check(register_host('ka-laptop-wired', dladdr=0x001d09c85b51))
check(register_host('tk-laptop-wifi',  dladdr=0x001e5271b4db)) 
check(register_host('mc-laptop-wifi',  dladdr=0x001ec2baaf55)) 
check(register_host('mc-laptop-wired', dladdr=0x001ec21c3865))
check(register_host('jp-laptop-wifi',  dladdr=0x001b63c15fd2))
check(register_host('jp-laptop-wired', dladdr=0x001b6391f375))
check(register_host('pb-laptop-wifi',  dladdr=0x001f3b0132b1))
check(register_host('pb-laptop-wired', dladdr=0x001ec902c0a1))
check(register_host('mm-laptop-wifi',  dladdr=0x0013ce0f7b25))
check(register_host('mm-laptop-wired', dladdr=0x00123fe3d331))

check(register_user('natasha'))
check(register_user('ben'))
check(register_user('martin'))
check(register_user('dan'))
check(register_user('keith'))
check(register_user('reid'))
check(register_user('pete'))

# GROUP DEFINITIONS

check(register_host_group('testing', 'test machines', ['straits','little-pete','leanhorse','kirks','tandoori','ramonas',"salsa","nox-ucb","gunmetal","nf2_name"], []))
check(register_host_group('laptops', 'laptops', ['dk-laptop-wifi',
                                                 'jl-laptop-wifi',
                                                 'bp-laptop-wifi',
                                                 'bp-laptop-wired',
                                                 'mc-laptop-wifi',
                                                 'mc-laptop-wired',
                                                 'tk-laptop-wifi',
                                                 'ng-laptop-wifi',
                                                 'ss-laptop-wifi',
                                                 'pb-laptop-wifi',
                                                 'pb-laptop-wired',
                                                 'ss-laptop-wired',
                                                 'ka-laptop-wifi',
                                                 'ka-laptop-wired',
                                                 'mm-laptop-wifi',
                                                 'mm-laptop-wired',
                                                 'jp-laptop-wifi'], []))
check(register_host_group('servers', 'servers', ['leadville','wahoos'], []))
check(register_host_group('ofbox', '', ['bugles', 'funyuns', 'combos', 'combos2', 'combos3', 'combos-of'], []))
check(register_host_group('workstations', 'workstations', ['miwok', 'hardrock', 'badwater', 'javelina','gobi','emerson'], []))
check(register_host_group('computers', 'all computers', ['netgear','gateway','airport'], ['workstations', 'servers', 'laptops', 'testing']))
check(register_host_group('mobile', 'mobile devices', [], []))
check(register_host_group('printers', 'printers', ['nicira-bw', 'nicira-color'], []))
check(register_host_group('all', 'all hosts', [], ['printers', 'mobile','ofbox','computers']))

addedAll = True
if num_register == 0:
    print 'Registration complete'
