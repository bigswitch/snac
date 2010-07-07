
from nox.apps.ndb     import API, GetOp, PutOp 
from twisted.python import log

# functions to simplify access to the NDB from python
# feel free to add your own code here

# drops and then adds a table
# calls 'final_callback' when complete
def ndb_setup(ndb, table_name, table_dict, app_name, final_callback):    

        def cb_drop(res):
            d = ndb.create_table(table_name, table_dict , [])
            if(final_callback != None): 
              d.addCallback(final_callback)
            d.addErrback(lambda x: on_error("create table", table_name, app_name, x))

        d = ndb.drop_table(table_name)
        d.addCallback(cb_drop)
        d.addErrback(lambda x: on_error("drop table", table_name, app_name, x))
        return d

# adds a single entry to the NDB, calling 'final_callback' when it completes
def ndb_add(ndb, table_name, entry_dict, final_callback, app_name = ""): 
  add_put = PutOp(table_name, entry_dict) 
  d = do_op_list(ndb, table_name, [ add_put ] , final_callback, app_name, "add") 
  return d

# removes a single entry to the NDB, calling 'final_callback' when it completes
def ndb_remove(ndb, table_name, entry_dict, final_callback, app_name = ""): 
  remove_put = PutOp(table_name, None, entry_dict) 
  d = do_op_list(ndb, table_name, [ remove_put ] , final_callback, app_name, "remove") 
  return d
 
def ndb_issue_query(ndb, table_name, match_dict, final_callback, app_name = ""): 
   get_op = GetOp(table_name, match_dict)
   d = do_op_list(ndb, table_name, [ get_op ] , final_callback, app_name, "query") 
   return d

# sets trigger to callback when a column in 'columns' changes
def ndb_set_trigger(ndb, table_name, trigger_callback, columns = [], app_name = ""):
  dict = {}
  for e in columns:
    dict[e] = ""
  get_op = GetOp(table_name, dict, trigger_callback)
  d = do_op_list(ndb, table_name, [ get_op ] , None, app_name, "set trigger")  
  return d

# generic helper to execute a list of actions
def do_op_list(ndb, table_name, op_list, final_callback, app_name, op_desc) : 
  d = ndb.execute( op_list ) 
  if final_callback != None:
    d.addCallback(final_callback) 
  d.addErrback(lambda x: on_error(op_desc, table_name, app_name,x))
  return d

# generic helper for Errback calls
def on_error(action, table_name, app_name, res):
      import traceback
      print "Error in ndb_util call for '" + action + "'" 
      traceback.print_exc()
      return res # must return this result if you want other errbacks to be called
