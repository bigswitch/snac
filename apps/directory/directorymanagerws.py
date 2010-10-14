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
import re
from nox.lib.core    import *
from nox.ext.apps.coreui import webservice

from twisted.python.failure import Failure
from nox.netapps.authenticator.pyauth import Auth_event, Authenticator
from nox.ext.apps.directory.directorymanager import *
from nox.lib.directory_factory import Directory_Factory
from nox.netapps.switchstats.switchstats    import switchstats
from nox.ext.apps.coreui.webservice import json_parse_message_body
from nox.ext.apps.coreui.webservice import NOT_DONE_YET, WSPathArbitraryString 
from nox.ext.apps.coreui.web_arg_utils import *
from nox.ext.apps.directory.query import query
from nox.lib.netinet.netinet import *
from nox.lib.directory import *
from nox.netapps.bindings_storage.bindings_directory import *
from nox.ext.apps.directory.dir_utils import *
from nox.ext.apps.directory.principal_search import do_principal_search 

import simplejson

lg = logging.getLogger('directorymanagerws')


# this matches any valid directory name (e.g., 'NOX Directory') 
class WSPathExistingDirName(webservice.WSPathComponent):
    def __init__(self, directorymanager, id_str):
        webservice.WSPathComponent.__init__(self)
        self._dm = directorymanager
        self._id_str = id_str 
    def __str__(self):
        return self._id_str
    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI")
        pc = unicode(pc, 'utf-8')
        if self._dm.is_valid_directory_name(pc):
            return webservice.WSPathExtractResult(pc)
        err = "invalid directory name %s" % pc
        return webservice.WSPathExtractResult(error=err)
    


def reg_each_principal(reg_fn, handler,type,path_suffix,desc): 
        
        values = [ "switch","location","host","user" ]
        for v in values:
          if path_suffix: 
            path = (webservice.WSPathStaticString(v),) + path_suffix
          else: 
            path = (webservice.WSPathStaticString(v),)
         
          reg_fn(handler,type,path, desc) 


# this import has to be below the above class declaration(s)
from dm_ws_switch   import dm_ws_switch 
from dm_ws_location import dm_ws_location 
from dm_ws_user     import dm_ws_user
from dm_ws_bindings import dm_ws_bindings
from dm_ws_groups   import dm_ws_groups

class directorymanagerws(Component):
    """Web service for viewing an manipulating directory stores"""

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.error_str() + ": " + failure.value.message

        return webservice.internalError(request, msg)

    def _get_dir_types(self, request, arg):
        try:
            response = {}
            response['identifier'] = 'type_name'
            response['items'] = []
            for type, dir_factory in self._dm.get_directory_factories().items():
                item = self._convert_type_to_dict(dir_factory)
                response['items'].append(item)
            return simplejson.dumps(response)
        except Exception, e:
            return self.err(Failure(), request, "_get_dir_types",
                            "Could not retrieve directory types.")
    
    def _convert_type_to_dict(self,di): 
            item = {}
            item['type_name']         = di.get_type() 
            item['supports_global_groups'] = di.supports_global_groups()
            item['supported_auth_types'] = di.supported_auth_types()
            item['supported_principals'] = {
                'switch'   : di.principal_supported(
                        Directory_Factory.SWITCH_PRINCIPAL),
                'location' : di.principal_supported(
                        Directory_Factory.LOCATION_PRINCIPAL),
                'host'     : di.principal_supported(
                        Directory_Factory.HOST_PRINCIPAL),
                'user'     : di.principal_supported(
                        Directory_Factory.USER_PRINCIPAL),
            }
            item['supported_groups'] = {
                'location' : di.group_supported(
                        Directory_Factory.LOCATION_PRINCIPAL_GROUP),
                'host'     : di.group_supported(
                        Directory_Factory.HOST_PRINCIPAL_GROUP),
                'user'     : di.group_supported(
                        Directory_Factory.USER_PRINCIPAL_GROUP),
                'switch'   : di.group_supported(
                        Directory_Factory.SWITCH_PRINCIPAL_GROUP),
                'dladdr'   : di.group_supported(
                        Directory_Factory.DLADDR_GROUP),
                'nwaddr'   : di.group_supported(
                        Directory_Factory.NWADDR_GROUP),
            }
            item['supports_multiple_instances'] = \
                di.supports_multiple_instances()
            item['topology_properties_supported'] = \
                di.topology_properties_supported()
            item['default_config'] = di.get_default_config()
            return item

    def _convert_instance_to_dict(self,did): 
            item = {}
            item['name']         = did._name
            di = did._instance
            item['type']         = di.get_type() 
            item['enabled_auth_types'] = di.get_enabled_auth_types()
            item['status'] = { 
                'value' : di.get_status().status,
                'message' : di.get_status().message
            } 
            item['enabled_principals'] = {
                'switch'  :
                    di.principal_enabled(Directory_Factory.SWITCH_PRINCIPAL),
                'location' :
                    di.principal_enabled(Directory_Factory.LOCATION_PRINCIPAL),
                'host'     :
                    di.principal_enabled(Directory_Factory.HOST_PRINCIPAL),
                'user'     :
                    di.principal_enabled(Directory_Factory.USER_PRINCIPAL),
            }
            item['enabled_groups'] = {
                'switch'  :
                    di.group_enabled(Directory_Factory.SWITCH_PRINCIPAL_GROUP),
                'location' :
                    di.group_enabled(Directory_Factory.LOCATION_PRINCIPAL_GROUP),
                'host'     :
                    di.group_enabled(Directory_Factory.HOST_PRINCIPAL_GROUP),
                'user'     :
                    di.group_enabled(Directory_Factory.USER_PRINCIPAL_GROUP),
                'dladdr'     :
                    di.group_enabled(Directory_Factory.DLADDR_GROUP),
                'nwaddr'     :
                    di.group_enabled(Directory_Factory.NWADDR_GROUP),

            }

            item['config_params'] = di.get_config_params()
            return item

    def _get_directories(self, request, arg):
        try:
            response = {}
            response['identifier'] = 'name'
            response['items'] = []
            # directory instances are returned in search order
            for instance in self._dm.get_directory_instances():
                item = self._convert_instance_to_dict(instance) 
                response['items'].append(item)
            return simplejson.dumps(response)
        except Exception, e:
            return self.err(Failure(), request, "_get_directories",
                            "Could not retrieve directories.")

    def _change_search_order(self, request, arg): 
        def err_specific(res):
            if isinstance(res.value, DirectoryException) \
                    and res.value.code == DirectoryException.NONEXISTING_NAME:
                lg.error("Bad request: _change_search_order received nonexisting_name: %s" % str(res))
                return webservice.badRequest(request, res.value.message)
            return self.err(res, request, "_change_search_order",
                            "Could not change search order.")
    
        try:
            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request,"Unable to parse message body.")

            def ok(res):
                request.write(simplejson.dumps(res)) 
                request.finish()

            d = self._dm.set_search_order(content)
            d.addCallback(ok)
            d.addErrback(err_specific) 
            return NOT_DONE_YET
        except Exception, e:
            err_specific(Failure())

    def _get_dir(self, request, arg):
        try:
            dirname = arg['<dir name>']

            for instance in self._dm.get_directory_instances():
                if dirname == instance._name:
                    item = self._convert_instance_to_dict(instance) 
                    return simplejson.dumps(item) 

            return webservice.notFound(request, "Directory %s not found." % dirname)
        except Exception, e:
            return self.err(Failure(), request, "_get_dir",
                            "Could not retrieve directory.")

    def _delete_dir(self, request, arg):
        try:
            dirname = arg['<dir name>']

            def ok(res):
                if res == None:
                    raise Exception("Could not delete directory %s." % dirname)

                request.write(simplejson.dumps("success"))
                request.finish()

            d = self._dm.del_configured_directory(dirname)
            d.addCallback(ok)
            d.addErrback(self.err, request, "_delete_dir", "Could not delete directory.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "_delete_dir",
                            "Could not delete directory.")

    # this fn is only called via _modify_dir
    def _add_dir(self,request,dname,content):
        def ok(res):
            did = self._dm.get_directory_instance(dname)
            d = did._instance.set_config_params(content["config_params"])
            d.addCallback(_config_set, did)
            return d

        def _config_set(res, did):
            ep = convert_map_name_to_type(content["enabled_principals"])
            d = did._instance.set_enabled_principals(ep)
            d.addCallback(_enabled_principals_set, did)
            return d

        def _enabled_principals_set(res, did):
            d = did._instance.set_enabled_auth_types(content["enabled_auth_types"])
            d.addCallback(_enabled_auth_set, did)
            return d

        def _enabled_auth_set(res, did):
            ret = simplejson.dumps(self._convert_instance_to_dict(did))
            request.write(ret)
            request.finish()

        def err_specific(res):
            return handle_exception(res.value)

        def handle_exception(e):
            if isinstance(e, DirectoryException) \
                    and e.code == DirectoryException.RECORD_ALREADY_EXISTS:
                lg.error("Conflict error: _add_dir %s already_exists: %s"
                        %(dname, str(e).encode('utf-8')))
                return webservice.conflictError(request,
                        "Directory %s already exists." % dname)
            return self.err(e, request, "_add_dir",
                            "Could not add directory.")
    
        try:
            d = self._dm.add_configured_directory(content["name"],
                    content["type"])
            d.addCallback(ok)
            d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e:
            return handle_exception(e)
    
    def _modify_dir(self,request,arg): 
        try:
            def _config_set(res):
                ep = convert_map_name_to_type(content["enabled_principals"]) 
                d = di.set_enabled_principals(ep)
                d.addCallback(_enabled_principals_set)
                return d

            def _enabled_principals_set(res):
                d = di.set_enabled_auth_types(content["enabled_auth_types"])
                d.addCallback(_enabled_auth_set)
                return d

            def _enabled_auth_set(res):
                if content["name"] != dname: 
                    lg.error("TODO: implement renaming directories")
                item = self._convert_instance_to_dict(instance) 
                ret = simplejson.dumps(item) 
                request.write(ret)
                request.finish()

            dname = arg['<dir name>']
            content = json_parse_message_body(request)
            if content is None:
                return webservice.badRequest(request,
                        "Unable to parse message body.")
            if request.args.get('add', ['false'])[0].lower() == 'true':
                return self._add_dir(request, dname, content)
            instance = self._dm.get_directory_instance(dname)
            if instance is None:
                return webservice.badRequest(request,"Could not modify "
                        "directory: directory named '%s' does not exist" 
                        %dname)
            
            # otherwise, proceed with normal modify
            di = instance._instance
            d = di.set_config_params(content["config_params"])
            d.addCallback(_config_set)
            d.addErrback(self.err, request, "_modify_dir",
                         "Could not modify directory.")
            return NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "_modify_dir",
                            "Could not add/modify directory.")

    # handles search_* calls (e.g., search_locations(), search_users(),
    # search_host(), and search_switch()).  
    # web service returns a JSON-encoded list of names
    def _search_principals(self, request, arg):
        def err_specific(res):
            # special message case
            if isinstance(res.value, DirectoryException):
                msg = res.value.message
            else:
                msg = "Could not search principal data."
            return self.err(res, request, "_search_principals", msg)
    
        try:
            def write_to_json(ret_list): 
              request.write(simplejson.dumps(ret_list))
              request.finish()
            type_str = get_principal_type_from_args(arg)
            dirname = arg.get('<dir name>', None)
            d = do_principal_search(request, type_str, dirname, 
                                    self._dm, self.bindings_dir) 
            d.addCallback(write_to_json)
            d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
   
    # handles webservice requests that take a single principal name 
    # as input.  Currently these are get_principal(), delete_principal(), 
    # and get_group_memeberships() functions
    def _do_single_name_op(self, request, arg, method_name):
        def err_specific(res):
            if isinstance(res.value, DirectoryException):
                if res.value.code == DirectoryException.NONEXISTING_NAME:
                    lg.error("Not found: %s() %s %s does not exist: %s" % \
                        (method_name, type_str, mangled_name, str(res)))
                    return webservice.notFound(request, "%s %s not found." % \
                        (type_str.capitalize(), mangled_name))
                
            return self.err(res, request, method_name, "Could not %s." % \
                            method_name)

        try:
            type_str = get_principal_type_from_args(arg)
            dirname = arg.get('<dir name>', None)
            name = arg['<principal name>']
            mangled_name = mangle_name(dirname, name)
            
            def ok(res):
                if res is None:
                    return webservice.notFound(request,"%s '%s' does not exist." \
                                                   % (type_str.capitalize(), mangled_name))
                else:
                    if isinstance(res,list) or isinstance(res,tuple): 
                        # result of search_*_group() is a list 
                        ret = simplejson.dumps(res)
                    elif isinstance(res,PrincipalInfo): 
                        # result of add_*(),get_*() or del_*() is a PrincipalInfo subclass
                        ret = simplejson.dumps(res.to_str_dict())
                    else:
                        raise Exception("Unexpected result in ok() for do_single_name_op " \
                                            + "method = " + method_name + ": " + str(res))
                request.write(ret)
                request.finish()

            kwargs = {} 
            # useful only for switches
            if "include_locations" in request.args \
                    and request.args["include_locations"][0] == "true": 
                kwargs["include_locations"] = True

            ptype = name_to_type_map[type_str]
            d =  getattr(self._dm, method_name)(ptype, mangled_name, **kwargs)
            if d == None:
                raise Exception("Directory manager returned null deferred.")

            d.addCallback(ok)
            d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e: 
            return err_specific(Failure())

    # A single URL exposes add, modify, and rename at the webservice level
    def _modify_principal(self, request, arg):
        def err_specific(res):
            if isinstance(res.value, DirectoryException):
                if res.value.code == DirectoryException.RECORD_ALREADY_EXISTS:
                    lg.error("Conflict error: _modify_principal %s %s already exists: %s" \
                                 % (type_str, content['name'], str(res)))
                    return webservice.conflictError(request, "%s %s already exists." % (type_str.capitalize(),
                                                                                        content['name']))
                elif res.value.code == DirectoryException.NONEXISTING_NAME:
                    lg.error("Bad request: _modify_principal %s %s does not exist: %s" \
                                 % (type_str.capitalize(), mangled_name, str(res)))
                    return webservice.notFound(request, "%s %s does not exist." % (type_str.capitalize(), mangled_name))

            return self.err(res, request, "_modify_principal",
                            "Could not modify principal.")
        try:
            type_str = get_principal_type_from_args(arg)
            dirname  = arg['<dir name>'] # must specify a dir-name
            name = arg['<principal name>']
            mangled_name =  mangle_name(dirname, name)

            def ok(res):
                ret = simplejson.dumps(res.to_str_dict())
                request.write(ret)
                request.finish()                

            content = json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request,"Unable to parse message body.")

            info = None
            if type_str == "location": 
                info = LocationInfo.from_str_dict(content)
            elif type_str == "switch": 
                info = SwitchInfo.from_str_dict(content)
            elif type_str == "user": 
                info = UserInfo.from_str_dict(content)
            elif type_str == "host": 
                info = HostInfo.from_str_dict(content)
            else:
                raise Exception("Invalid principal type %s" % type_str)
            ptype = name_to_type_map[type_str]
            if hasattr(info, 'name') and info.name != None:
                if len(content) == 1:
                    #rename
                    newdir = demangle_name(info.name)[0]
                    d = self._dm.rename_principal(ptype, name, info.name,
                                                  dirname, newdir)
                else:
                    #modify
                    if info.name != mangled_name: 
                        # renaming and updating info simultaneously can cause
                        # duplicate key problems when moving entities between
                        # directories - for now, we simply disallow this behavior
                        # The UI should never even give the user a chance to 
                        # create this error condition, so this is really dev check

                        msg = "Cannot rename and modify '%s' at the same time." \
                            % mangled_name
                        lg.error("Bad request: %s" % msg)
                        return webservice.badRequest(request, msg)
                    d = self._dm.add_or_modify_principal(ptype, info, dirname)
            else:
                info.name = name
                d = self._dm.add_or_modify_principal(ptype, info, dirname)
        
            if d == None:
                raise Exception("Directorymanager returned a null deferred.")

            d.addCallback(ok)
            d.addErrback(err_specific)
            return NOT_DONE_YET
        except Exception, e:
            return err_specific(Failure())
      
    def _do_delete_bindings(self, request, arg):
        #TODO: it would be nice to get a response conveying what bindings were
        #      removed, but this isn't possible using the event method
        try:
            type_str = get_principal_type_from_args(arg)
            principal_name = arg["<principal name>"]
            dir_name  = arg["<dir name>"]
            principalid = mangle_name(dir_name, principal_name).encode('utf-8')
            if type_str == "user":
                ae = Auth_event(Auth_event.DEAUTHENTICATE,
                        datapathid.from_host(0), 0, create_eaddr(0), 0, False,
                        Authenticator.get_unknown_name(), principalid, 0, 0)
            elif type_str == "host":
                ae = Auth_event(Auth_event.DEAUTHENTICATE,
                        datapathid.from_host(0), 0, create_eaddr(0), 0, False,
                        principalid, Authenticator.get_unknown_name(), 0, 0)
            else:
                raise Exception("Invalid principal type %s" % type_str)
            self._dm.post(ae)
            return simplejson.dumps("success")

        except Exception, e:
            return self.err(Failure(), request, "do_delete_bindings",
                            "Could not construct deauth event.")

    def install(self):
        self._dm = self.resolve(directorymanager)

        ws  = self.resolve(str(webservice.webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request


        # we handle some bindings storage info in a separate class
        # we also use self.bindings_dir to respond to 'active=true' queries
        self.bindings_dir = self.resolve(BindingsDirectory)
        dm_ws_bindings(self._dm, self.bindings_dir, reg) 
        
        # we handle special switch stats in a separate class
        # spawn one of those right now
        switch_data = self.resolve(switchstats)
        switch_ws = dm_ws_switch(self._dm, self.bindings_dir, switch_data)
        switch_ws.register_webservices(reg) 

        # handle special location queries
        location_ws = dm_ws_location(self._dm, self.bindings_dir)
        location_ws.register_webservices(reg) 

        # handle special user queries
        dm_ws_user(self._dm, self.bindings_dir, reg)

        # this class handles the /ws.v1/group URLs
        groups = dm_ws_groups(self._dm, reg)

        # /ws.v1/directory/type
        directory_type_path = ( webservice.WSPathStaticString("directory"), 
                                webservice.WSPathStaticString("type"), )
        reg(self._get_dir_types, "GET", directory_type_path,
                """Get directory component types""")

        # PUT /ws.v1/directory/search_order
        search_order_path = ( webservice.WSPathStaticString("directory"), 
                                webservice.WSPathStaticString("search_order"), )
        reg(self._change_search_order, "PUT", search_order_path,
                """Modify search order of the directories""")
      

        # /ws.v1/directory/instance
        directory_inst_path = ( webservice.WSPathStaticString("directory"), 
                                webservice.WSPathStaticString("instance"), )
        reg(self._get_directories, "GET", directory_inst_path,
            """Get list of directories in search order.""")

        # /ws.v1/directory/instance/<dir name>/
        dirnamepath   = directory_inst_path + \
                        (WSPathArbitraryString("<dir name>") ,)
       

        # The following webservices all either search or add/modify/delete
        # principals. They can create the following HTTP error codes:
        #
        # 400 - A PUT to modify a principal did not contain any content
        # 404 - The principal does not exist in the specified directory
        # 409 - Attempting to add a principal that already exists.
        # 500 - The server experience an internal error while performing
        #       the requested operation. 

        reg(self._get_dir, "GET", dirnamepath,
            """Get directory attributes by name""")
        reg(self._delete_dir, "DELETE", dirnamepath,
            """Delete the named directory""")
        reg(self._modify_dir, "PUT", dirnamepath,
            """Add or Modify the named directory""")

        single_principal_path = \
                      (WSPathExistingDirName(self._dm,"<dir name>") ,) + \
                      (WSPathArbitraryString("<principal name>") ,)
        
        # PUT /ws.v1/<principal type>/<dir name>/<principal name>
        # ADD URL: add a new principal name to a particular directory
        # MODIFY URL: add a new principal name to a particular directory
        reg_each_principal(reg, self._modify_principal, "PUT", 
            single_principal_path, """Add or modify a principal.""")
        
        # DELETE /ws.v1/<principal type>/<dir name>/<principal name>
        def do_delete_principal(request,arg):
          return self._do_single_name_op(request,arg,"del_principal") 
        reg_each_principal(reg,do_delete_principal, "DELETE", 
            single_principal_path, """Delete an existing principal.""")

        # GET function:  Get directory data associated with a
        # particular name.  Returns JSON-encoding of a HostInfo,
        # SwitchInfo, LocationInfo, or UserInfo object.  
        #GET /ws.v1/<principal type>/<dir name>/<principal name>
        def do_get_principal(request,arg):
          return self._do_single_name_op(request,arg,"get_principal") 
        reg_each_principal(reg,do_get_principal, "GET", single_principal_path, 
            """Lookup principal data by name.""")

        # GET /ws.v1/<principal type/<dir name>/<principal name>/group
        def do_get_principal_groups(request,arg):
          dirname = arg.get('<dir name>', None)
          instance = self._dm.get_directory_instance(dirname)
          if instance is None:
            return webservice.notFound(request,"Directory '%s' does not exist."
                    %dirname)
          type_str = get_principal_type_from_args(arg)
          ptype = name_to_type_map.get(type_str)
          if ptype is None:
            return webservice.notFound(request,"Invalid principal type %s"
                    %type_str)
          if instance._instance.group_enabled(ptype) == Directory.NO_SUPPORT:
            return simplejson.dumps(())
          return self._do_single_name_op(request,arg,"get_group_membership") 
        group_path = single_principal_path + \
                          (webservice.WSPathStaticString("group"),)
        reg_each_principal(reg,do_get_principal_groups, "GET", group_path, 
              """Get all groups that contain this principal.""")
        
       
        # SEARCH functions.  Search principals in all directories
        # in in a specific directory.  Returns a list of principal names.  
        # GET /ws.v1/<principal type>
        # GET /ws.v1/<principal type>/<dir name>
        #
        # Query Params:
        # * supports standard 'start' 'count' for pagination
        # * supports 'sort_descending'
        # * if 'list' param is true, returns tuple of { 'name',
        #   'directory', and 'active' }, in which case it also 
        # supports the 'sort_attribute' param.  
        # * 'active': optional boolean param to filter results based
        # on whether the principal is currently active on the network. 
        # * Also supports a wide number of other params to filter records
        # based on the contents of bindings storage and directories.
        # See the *Query objects in nox/lib/directory.py for details. 
        reg_each_principal(reg,self._search_principals, "GET", None,
            """Search principal data in all directories""")
        
        reg_each_principal(reg,self._search_principals, "GET", 
            (WSPathExistingDirName(self._dm, "<dir name>") ,),
            """Search principal data in named directory""")
       
        # Requests deauthenticaiton of all bindings of host and user principals
        # DELETE /ws.v1/user/<dir name>/<principal name>/binding
        dirname = WSPathExistingDirName(self._dm, "<dir name>");
        principalname = WSPathArbitraryString("<principal name>")
        userpath = ( webservice.WSPathStaticString("user"), dirname,
                     principalname )
        reg(self._do_delete_bindings, "DELETE",
                userpath + (webservice.WSPathStaticString("binding"),),
                "Deauthenticate user from all active bindings.")
        # DELETE /ws.v1/host/<dir name>/<principal name>/binding
        hostpath = ( webservice.WSPathStaticString("host"), dirname,
                     principalname )
        reg(self._do_delete_bindings, "DELETE",
                hostpath + (webservice.WSPathStaticString("binding"),),
                "Deauthenticate user from all active bindings.")
        # TODO: support removing specific bindings

    def getInterface(self):
        return str(directorymanagerws)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return directorymanagerws(ctxt)
    return Factory()
