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
import sets

from twisted.internet import defer
from nox.apps.coreui      import webservice
from nox.apps.coreui.webservice import *
from nox.apps.coreui.web_arg_utils import get_principal_type_from_args
from nox.apps.directory.directorymanagerws import *
from nox.apps.bindings_storage.bindings_directory import *
from nox.apps.directory.directorymanager import mangle_name
from nox.apps.bindings_storage.pybindings_storage import Name
from twisted.python.failure import Failure
from nox.lib.directory import Directory, DirectoryException
import time

lg = logging.getLogger('dm_ws_bindings')

# see below for desciption
USER_COUNT_INTERVAL_SEC = (60 * 15) 

class dm_ws_bindings:
    """Exposes active network binding state that does not correspond
    directly to a call in the standard directory interface"""
   
    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        return webservice.internalError(request, msg)

    def handle_get_entity_counts(self,request,arg):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "handle_get_entity_counts",
                            "Could not retrieve entity counts.")
        try:
            results = { "active" : {}, "total" : {}, "unregistered" : {} }
            principals = [ "switches", "hosts","users","locations"]
            ntypes = [Name.SWITCH,Name.HOST,Name.USER, Name.LOCATION]
            ptypes = [Directory.SWITCH_PRINCIPAL, Directory.HOST_PRINCIPAL, \
                          Directory.USER_PRINCIPAL, Directory.LOCATION_PRINCIPAL ] 

            # send request only if we're total done
            def test_finished(): 
                for t in results.keys(): 
                    if len(results[t]) != len(principals):
                        return 
                    
                request.write(simplejson.dumps(results))
                request.finish()
                

            def ok(res, count_type, principal_type):
                if len(errCalled) > 0:
                    return
                try:
                    if count_type == "active": 
                        res = sets.Set(res)
                    results[count_type][principal_type] = len(res)
                    if count_type == "total" and principal_type == "users":
                      self.cached_total_user_count = len(res)   
                    test_finished()
                except Exception, e:
                    err_specific(Failure())

            for i in range(0,len(principals)): 
                cb = (lambda w,x: lambda y: ok(y,w,x))("active",principals[i])
                self.bindings_dir.get_bstore().get_all_names(ntypes[i],cb)

            time_diff = time.time() - self.last_total_user_count_search
            for i in range(0,len(principals)):
                # HACK: until we can cache LDAP locally, we limit how often
                # we actually query the total number of users from LDAP
                cb = (lambda w,x: lambda y: ok(y,w,x))("total",principals[i])
                if principals[i] == "users" and time_diff < USER_COUNT_INTERVAL_SEC: 
                    results["total"]["users"] = self.cached_total_user_count
                    test_finished()
                else:  
                    d =  self.dm.search_principals(ptypes[i],{})
                    if principals[i] == "users": 
                      self.last_total_user_count_search = time.time()
                    d.addCallback(cb)
                    d.addErrback(err_specific)
      
            for i in range(0,len(principals)): 
                d =  self.dm.search_principals(ptypes[i],{}, "discovered")
                cb = (lambda w, x: lambda y: ok(y,w,x))("unregistered",principals[i])
                d.addCallback(cb)
                d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
        
    def get_all_links(self,request,arg):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "get_all_links",
                            "Could not retrieve links.")
        try:
            def cb(res):
                if len(errCalled) > 0:
                    return
                try:
                    results = []
                    for link in res:
                        l = { "dpid1" : link[0],
                              "port1" : link[1],
                              "dpid2" : link[2],
                              "port2" : link[3]
                              } 
                        results.append(l)
                    request.write(simplejson.dumps(results))
                    request.finish()
                except Exception, e:
                    return err_specific(Failure())
            self.bindings_dir.get_bstore().get_all_links(cb)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
            
    def handle_is_active(self, request, arg, principal_type_str):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "handle_is_active",
                            "Could not retrieve active status.")
        try:
            name = arg['<principal name>']
            dirname = arg['<dir name>']
            mangled_name = mangle_name(dirname,name)
        
            def cb(res):
                if len(errCalled) > 0:
                    return
                try:
                    is_non_empty = len(res) > 0
                    ret = simplejson.dumps(is_non_empty) 
                    if not is_non_empty: 
                        self.write_result_or_404(request, arg, ret,principal_type_str) 
                    else: 
                        request.write(ret)
                        request.finish()
                except Exception, e:
                    return err_specific(Failure())

            principal_type = get_nametype_from_string(principal_type_str)
            bstore = self.bindings_dir.get_bstore()
            if principal_type == Name.USER or principal_type == Name.HOST: 
                bstore.get_entities_by_name(mangled_name,principal_type, cb)
            else : 
                bstore.get_location_by_name(mangled_name,principal_type, cb)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
    
    def _get_name_for_iface(self, iface_dict): 
      return iface_dict['switch_name'] + ':' + \
                    iface_dict['port_name'] + ':' + \
                    iface_dict['dladdr'] + ':' + \
                    iface_dict['nwaddr']


    # this handles both:
    # 1) requests for all interface names for a host
    # 2) details for a specific host interface
    def handle_interface_request(self, request, arg):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "handle_interface_request",
                            "Could not retrieve interface information.")
        try:
            mangled_name = mangle_name(arg['<dir name>'], 
                                       arg['<principal name>'])

            def single_interface_cb(res, name):
                if len(errCalled) > 0:
                    return
                for i in res:
                    n = self._get_name_for_iface(i) 
                    if name == n:
                        request.write(simplejson.dumps(i))
                        request.finish() 
                        return

                msg = "Host '%s' has no interface '%s'." % (mangled_name, name)
                lg.error(msg) 
                webservice.notFound(request, msg)
        
            def all_interfaces_cb(res): 
                if len(errCalled) > 0:
                    return
                name_list = [ self._get_name_for_iface(i) for i in res]
                ret = simplejson.dumps(name_list)
                if len(name_list) == 0: 
                    self.write_result_or_404(request, arg, ret,"host") 
                else: 
                    request.write(simplejson.dumps(name_list))
                    request.finish() 

            d = self.bindings_dir.get_interfaces_for_host(mangled_name)
            if '<interface name>' in arg: 
                d.addCallback(single_interface_cb, arg['<interface name>'])
            else: 
                d.addCallback(all_interfaces_cb)
            d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())

    def handle_name_for_name(self, request, arg, 
                            input_type_str, output_type_str):
        errCalled = []
        def err_specific(res):
            if len(errCalled) > 0:
                return
            errCalled.append("y")
            return self.err(res, request, "handle_name_for_name",
                        "Could not find associated " + output_type_str + "s.")

        try: 
            def cb(res):
                if len(errCalled) > 0:
                    return
                try:
                    request.write(simplejson.dumps(res))
                    request.finish()
                except Exception, e:
                    return err_specific(Failure())

            input_type = get_nametype_from_string(input_type_str)
            output_type = get_nametype_from_string(output_type_str)
            name = arg['<principal name>']
            dirname = arg['<dir name>']
            mangled_name = mangle_name(dirname,name)
            self.bindings_dir.get_name_for_name(mangled_name,
                                                input_type,output_type,cb)

            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())

    # if the result from bindings storage is "empty", then we want to
    # check if it is the case that the name does not even exist in the directory.
    # If no name exists, we return a 404, otherwise, we return the result. 
    # 'ret' should be a JSON formatted string
    def write_result_or_404(self, request, arg, ret, type_str):
        try:
            name = arg['<principal name>']
            dirname = arg['<dir name>']
            def ok(res):
                if res is None:
                    webservice.notFound(request,
                                        "%s '%s' does not exist." % (type_str.capitalize(),
                                                                    mangle_name(dirname,name)))
                else:
                    request.write(ret)
                    request.finish()

            ptype = name_to_type_map[type_str]
            d =  self.dm.get_principal(ptype,name,dirname)
            d.addCallback(ok)
            d.addErrback(self.err, request, "write_result_or_404",
                         "Could not perform request.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "write_result_or_404",
                            "Could not perform request.")

    def __init__(self, dm, bindings_dir, reg):
        self.bindings_dir = bindings_dir 
        self.dm = dm

        #HACK: b/c the number of ldap can be huge, we 
        # don't query the total number of users each time
        # the webservice is called.  Instead we do it at most every
        # USER_COUNT_INTERVAL_SEC seconds.  As a point of reference, 
        # if LDAP is 25K users, my dev machine spikes to 50% CPU usage
        # each time it pulls all names from LDAP
        self.last_total_user_count_search = 0
        self.cached_total_user_count = 0

        entity_count_path = ( webservice.WSPathStaticString("bindings"), 
                        webservice.WSPathStaticString("entity_counts"),)
        desc = "Get the number of currently active hosts, users, " \
              "locations, and switches"
        reg(self.handle_get_entity_counts,"GET",entity_count_path,desc)
        
        link_path = ( webservice.WSPathStaticString("link"),)
        desc = "See all active network links (uni-directional)"
        reg(self.get_all_links,"GET",link_path,desc)

        principals = [ "host", "user", "location" ] 
        for p1 in principals:
          activepath = ( webservice.WSPathStaticString(p1), ) + \
                         (WSPathExistingDirName(dm, "<dir name>") ,) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("active"),)
          desc = "Determine if %s name is currently active" % (p1)
          fn = (lambda p: lambda x,y: self.handle_is_active(x,y,p))(p1)
          reg(fn, "GET", activepath, desc)
          for p2 in principals:
            if p1 != p2: 

              path = activepath + (webservice.WSPathStaticString(p2),)
              desc = "Find all %ss associated with the named %s" % (p2,p1)
              fn = (lambda u,v: \
                lambda x,y: self.handle_name_for_name(x,y,u,v))(p1,p2)
              reg(fn, "GET", path, desc)

        path = ( webservice.WSPathStaticString("host"), ) + \
                         (WSPathExistingDirName(dm, "<dir name>") ,) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("active"),) + \
                         (webservice.WSPathStaticString("interface"),)
        desc = "List active network interfaces associated with the named host"
        reg(self.handle_interface_request, "GET", path, desc)

        path = ( webservice.WSPathStaticString("host"), ) + \
                         (WSPathExistingDirName(dm, "<dir name>"),) + \
                         (WSPathArbitraryString("<principal name>"),) + \
                         (webservice.WSPathStaticString("interface"),) + \
                         (WSPathArbitraryString("<interface name>"),)
        desc = "Get information for a named host interface"
        reg(self.handle_interface_request, "GET", path, desc)



