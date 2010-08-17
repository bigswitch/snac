from twisted.python import log
from vigil import capps
from vigil import * 
from pyapi import *

from twisted.internet import reactor

active_switches = {}

def dp_join(dp, stats): 
    global active_switches 
    active_switches[dp] = True

def dp_leave(dp): 
    global active_switches 
    del active_switches[dp]

def timer_loop():

    s   = capps.stats_snapshot()
    s5  = capps.stats_snapshot()
    smin  = capps.stats_snapshot()
    lf = capps.listf()
    lf5 = capps.listf()
    lfmin = capps.listf()
    for dp in active_switches:
        dp,capps.get_packet_in_s(dp,s)
        dp,capps.get_packet_in_s_history(dp,lf)
        print s.last_s
        print '\t',
        for item in lf:
            print item,

        print ''    
        dp,capps.get_packet_in_s5(dp,s5)
        dp,capps.get_packet_in_s5_history(dp,lf5)
        print s5.last_s
        print '\t',
        for item in lf5:
            print item,
        print ''    

        dp,capps.get_packet_in_min(dp,smin)
        dp,capps.get_packet_in_min_history(dp,lfmin)
        print smin.last_s
        print '\t',
        for item in lfmin:
            print item,
        print ''    

    reactor.callLater(1, timer_loop)

register_for_datapath_join(dp_join)
register_for_datapath_leave(dp_leave)
reactor.callLater(1, timer_loop)
