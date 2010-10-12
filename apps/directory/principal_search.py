

from nox.apps.directory.dir_utils import glob_to_regex, filter_list
from nox.apps.coreui.web_arg_utils import *
from nox.apps.directory.dir_utils import *
from nox.apps.directory.directorymanager import *
    
    
# depending on the value of 'is_active', the arguments
# passed to query directories and bindings vary.
# this method handles those cases
def split_search_args(flat_args,is_active): 
  bs_keys = [ "dpid","port","dladdr","nwaddr" ] 
  bs_query = {}
  dir_query = copy.deepcopy(flat_args)
  if is_active is None: 
    # query both.  copy all valid bs_keys to a new query
    for k in bs_keys:
      if k in flat_args: 
        bs_query[k] = flat_args[k] 
  elif is_active == True: 
    for k in bs_keys:
      if k in flat_args: 
        bs_query[k] = flat_args[k]
        del dir_query[k] 
  else: # is_active = False
    pass 
  
  return (dir_query,bs_query) 


# if 'dirname' is None, search all directories
def do_principal_search(request, ptype_str, dirname, dm, bd): 
   is_active = grab_boolean_arg(request,"active", None)
   is_active_external = grab_boolean_arg(request, "active_ext", None)

   filter_arr = get_default_filter_arr()
   filter_dict = parse_mandatory_args(request, filter_arr)

   to_remove = map(lambda t : t[0], filter_arr)
   flat_args = flatten_args(request.args, to_remove)
   flat_args = dict([(k, unicode(v, 'utf-8')) for (k,v) in flat_args.items()])

   if is_active is not None:
       del flat_args["active"]
   if is_active_external is not None:
       del flat_args["active_ext"]
   dir_query, bs_query = split_search_args(flat_args, is_active)
   dir_set = set()
   bs_set = set() 

   # bindings_directory only queries based on network identifiers,
   # so we need to filter results based on a couple of other things
   def query_dir_cb(res):
       dir_set.update(res)
       if is_active is None:
            ret = dir_set.union(bs_set)
       elif is_active == True:
            ret = dir_set.intersection(bs_set)
       else: # is_active == False
            ret = dir_set.difference(bs_set)
       ret_list = list(ret)
       if ptype_str == "location":
         def no_openflow_devs(name): 
           # NOTE: this wont' work if the user can even rename
           # of0 locations.  Assuming such locations are not shown in the
           # UI however, this should be good enough, as long
           # as colons are not allowed in normal location names
           return demangle_name(name)[1].find(":of") == -1
         ret_list = filter(no_openflow_devs,ret_list)
       return ret_list # all done

   def query_bs_cb(res, dirname):
      # the binding storage query was not over names, so we have
      # to filter them manually
      if "name" in flat_args:
        name = flat_args["name"]
        filter_list(res,lambda n: demangle_name(n)[1] != name)
      if "name_glob" in flat_args:
        regex_str = glob_to_regex(flat_args['name_glob'])
        regex = re.compile(regex_str)
        filter_list(res, lambda n : not regex.search(demangle_name(n)[1]) )

      if dirname is not None:
        filter_list(res, lambda n: demangle_name(n)[0] != dirname)
       
      bs_set.update(res)

   def query_dir_prep(ignore, dirname): 
       if ptype_str == "location":
           q = LocationQuery(dir_query)
       elif ptype_str == "user":
           q = UserQuery(dir_query)
       elif ptype_str == "host":
           q = HostQuery(dir_query)
       elif ptype_str == "switch":
           q = SwitchQuery(dir_query)

       ptype = name_to_type_map[ptype_str]
       if dirname is None and is_active_external:
           # XXX Hack until pagination is ready - we only search the
           # Built-in directory and binding storage so we don't
           # overwhelm the UI with thousands of names
           dirname = 'Built-in'
       return dm.search_principals(ptype, q.get_query_dict(),dirname)

   name_type = get_nametype_from_string(ptype_str)
   n = HostQuery(bs_query)
   d = bd.search_names_by_netinfo(n.get_query_dict(),
                                                   name_type)
   d.addCallback(query_bs_cb,dirname)
   d.addCallback(query_dir_prep,dirname) 
   d.addCallback(query_dir_cb)
   return d

