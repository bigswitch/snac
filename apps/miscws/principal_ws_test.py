import sys,os
import httplib
import simplejson
import urllib

# without this, python can't find the NOX includes
sys.path.append(os.getcwd())
from nox.webapps.webserviceclient import PersistentLogin, NOXWSClient 

# tests if two lists of dictionaries are the
# same.  the order of dictionaries in the list
# does not matter
def dict_list_is_same(l1,l2):
  if type(l1) != type(l2): 
    return False
  if len(l1) != len(l2):
    return False

  for d1 in l1:
    match_found = False
    for d2 in l2:
      if type(d2) == type({}):
        if dict_is_same(d1,d2):
          match_found = True
          break
      elif type(d2) == type([]):
        if list_is_same(d1,d2):
          match_found = True
          break
      else:
        if d1 == d2:
          match_found = True
          break
    if not match_found:
      return False
  
  return True

def dict_is_same(d1,d2):
  if(len(d1) != len(d2)):
    return False 

  for key in d2.keys():
      if key not in d1: return False
      if type(d1[key]) == type([]): 
          if not dict_list_is_same(d1[key],d2[key]):
            return False
      else: 
          if not d1[key] == d2[key]:
            return False
  return True

def list_is_same(l1,l2):
  if len(l1) != len(l2):
    return False

  for d1 in l1:
    match_found = False
    for d2 in l2:
      if d1 == d2:
        match_found = True
        break
    if not match_found:
      return False
  
  return True


class WSTester: 

  def __init__(self): 
    loginmgr = PersistentLogin("admin","admin")
    self.wsc = NOXWSClient("127.0.0.1", 8888, False, loginmgr)
    self.print_progress = True
    self.print_requests = False

  def print_begin(self, text, width=80):
      bar = "="
      side = (width - len(text))/2
      print "\n%s %s %s" % (bar*side, text.title(), bar*side)

  def print_start(self, text, blank=False, width=59):
      if blank:    fill = " "
      else:        fill = "."
      while len(text) > width:
          for i in xrange(width+1,width/2,-1):
              if text[i-1] in (" ", "/"):
                  to_print = text[:i]
                  break
          print to_print
          text = text[len(to_print):]
      if len(text) < width:
          text += " " + fill*(width-len(text)-1)
      print "%s" % text,

  def print_end(self, text, good=True, width=21):
      if good:    cap = " [ OK ]"
      else:       cap = " [FAIL]"
      if self.print_requests:
          self.print_start("", blank=True)
      while len(text) > width - len(cap):
          to_print = text[:width]
          if len(text) > width and text[width] != " ":
              to_print = " ".join(to_print.split(" ")[:-1])
          print to_print
          text = text[len(to_print)+1:]
          self.print_start("", blank=True)
      width = width - len(cap)
      print "%-*s%s" % (width, text, cap)
   
  def response_is_valid(self,response):
      contentType = response.getContentType()
      assert response.status == httplib.OK, \
             "Request error %d (%s) : %s" % \
             (response.status, response.reason, response.getBody())
      assert contentType == "application/json", \
             "Unexpected content type: %s : %s" % \
             (contentType, response.getBody())
      return True

  def print_get(self, url):
    url = urllib.quote(url)
    response = self.wsc.get(url) 
    print "Result: %d %s\n" % (response.status, response.reason)
    body = response.getBody()
    if self.response_is_valid(response): 
      print simplejson.dumps(simplejson.loads(body), indent=2)

  
  def do_auth_event(self, type,dpid,port,mac,ip,username,hostname): 
      auth_obj = {'type' : type,
                  'dpid' : dpid,
                  'port' : port,
                  'dladdr' : mac,
                  'nwaddr' : ip,
                  'username' : username,
                  'hostname' : hostname
                 } 
      response = self.wsc.putAsJson(auth_obj,"/ws.v1/debug/event/auth") 
      self.response_is_valid(response) 
  
  def put_principal(self, principal_type, dirname, principal_name, obj_dict, \
                    notes={}):
      if self.print_progress:
          action = "Putting"
          if principal_type:
              action += " a"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              if "group" in principal_type:
                  action += " %s %s"% tuple(reversed(principal_type.split('/')))
              else:
                  action += " %s" % principal_type
          if dirname:
              action += " into"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % dirname
          if obj_dict:
              action += " with"
              if 'contents' in notes:   action += " (%s)" % notes['contents']
              action += " %s" % "/".join(obj_dict.keys())
          self.print_start(action)

      url = urllib.quote("/ws.v1/%s/%s/%s" % (principal_type,dirname,principal_name))
      if self.print_requests:
          print "\nPUT ", url
      response = self.wsc.putAsJson(obj_dict,url) 
      self.response_is_valid(response)

      if self.print_progress:
          self.print_end("Placed")
  
  def delete_principal(self, principal_type, dirname, principal_name, \
                       notes={}):
      if self.print_progress:
          action = "Deleting"
          if principal_type:
              action += " a"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              if "group" in principal_type:
                  action += " %s %s"% tuple(reversed(principal_type.split('/')))
              else:
                  action += " %s" % principal_type
          if principal_name:
              action += " named"
              if 'name' in notes:       action += " (%s)" % notes['name']
              action += " %s" % principal_name
          if dirname:
              action += " from"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % dirname
          self.print_start(action)

      url = urllib.quote("/ws.v1/%s/%s/%s" % (principal_type,dirname,principal_name))
      if self.print_requests:
          print "\nDEL ", url
      response = self.wsc.delete(url, { "content-type" : "application/json" } )
      self.response_is_valid(response)

      if self.print_progress:
          self.print_end("Removed")
 
  def add_group_member(self, principal_type, group_dir, group_name, \
                       principal_dir, principal_name, principal_class, \
                       notes={}):
      if self.print_progress:
          action = "Adding"
          if principal_type:
              action += " a"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              action += " %s" % principal_type.split("/")[1]
          if principal_name:
              action += " named"
              if 'name' in notes:  action += " (%s)" % notes['name']
              action += " %s" % principal_name
          if principal_dir:
              action += " from"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % principal_dir
          if principal_type:
              action += " into a"
              if 'group' in notes:  action += " (%s)" % notes['directory']
              action += " %s %s"% tuple(reversed(principal_type.split('/')))
          if group_name:
              action += " named"
              if 'group_name' in notes:  action += " (%s)" % notes['group_name']
              action += " %s" % group_name
          if group_dir:
              action += " in"
              if 'group_directory' in notes:  action += " (%s)" % notes['group_directory']
              action += " %s" % group_dir

          self.print_start(action)

      url = urllib.quote("/ws.v1/%s/%s/%s/%s/%s/%s" % \
                         (principal_type, group_dir, group_name, \
                          principal_class, principal_dir, principal_name))
      obj_dict = None  # Not used
      if self.print_requests:
          print "\nPUT ", url
      response = self.wsc.putAsJson(obj_dict,url) 
      self.response_is_valid(response)

      if self.print_progress:
          self.print_end("Placed")
  
  def remove_group_member(self, principal_type, group_dir, group_name, \
                          principal_dir, principal_name, principal_class, \
                          notes={}):
      if self.print_progress:
          action = "Removing"
          if principal_type:
              action += " a"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              action += " %s" % principal_class
          if principal_name:
              action += " named"
              if 'name' in notes:  action += " (%s)" % notes['name']
              action += " %s" % principal_name
          if principal_dir:
              action += " in"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % principal_dir
          if principal_type:
              action += " from a"
              if 'group' in notes:  action += " (%s)" % notes['directory']
              action += " %s %s"% tuple(reversed(principal_type.split('/')))
          if group_name:
              action += " named"
              if 'group_name' in notes:  action += " (%s)" % notes['group_name']
              action += " %s" % group_name
          if group_dir:
              action += " in"
              if 'group_directory' in notes:  action += " (%s)" % notes['group_directory']
              action += " %s" % group_dir

          self.print_start(action)

      url = urllib.quote("/ws.v1/%s/%s/%s/%s/%s/%s" % \
                          (principal_type, group_dir, group_name, \
                           principal_class, principal_dir, principal_name))
      if self.print_requests:
          print "\nDEL ", url
      response = self.wsc.delete(url, { "content-type" : "application/json" } )
      self.response_is_valid(response)

      if self.print_progress:
          self.print_end("Removed")

  # does get and makes sure that we get the expected result
  # if 'expected_obj_dict' is None, then we expect a 404
  def verify_get_group_member(self, principal_type, group_dir, group_name, \
                              principal_dir, principal_name, principal_class, \
                              expected_obj_dict, notes={}):
      if self.print_progress:
          action = "Retrieving"
          if principal_type:
              action += " a"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              action += " %s" % principal_type.split("/")[1]
          if principal_name:
              action += " named"
              if 'name' in notes:  action += " (%s)" % notes['name']
              action += " %s" % principal_name
          if principal_dir:
              action += " in"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % principal_dir
          if principal_type:
              action += " from a"
              if 'group' in notes:  action += " (%s)" % notes['directory']
              action += " %s %s"% tuple(reversed(principal_type.split('/')))
          if group_name:
              action += " named"
              if 'group_name' in notes:  action += " (%s)" % notes['group_name']
              action += " %s" % group_name
          if group_dir:
              action += " in"
              if 'group_directory' in notes:  action += " (%s)" % notes['group_directory']
              action += " %s" % group_dir
          self.print_start(action)

      url = "/ws.v1/%s/%s/%s/%s/%s/%s" %  \
             (principal_type, group_dir, group_name, \
              principal_class, principal_dir, principal_name)
      url = urllib.quote(url)
      if self.print_requests:
          print "\nGET ", url
      response = self.wsc.get(url) 
      if expected_obj_dict == None: 
        if response.status == httplib.OK:
          if self.print_progress:
              self.print_end("Found", good=False)
          print "Expected non-OK value, but got %s: %s" %  \
          (response.status,response.getBody())
        if self.print_progress:
            self.print_end("Expected error")
        return

      if self.print_progress:
          if response.status == httplib.OK:
              self.print_end("Found")
          else:
              self.print_end("Not Found", good=False)
 
  # does get and makes sure that we get the expected result
  # if 'expected_obj_dict' is None, then we expect a 404
  def verify_get_principal(self, principal_type, dirname, principal_name, \
                           expected_obj_dict, notes={}):
      if self.print_progress:
          action = "Retrieving"
          if principal_type:
              action += " a"
              if expected_obj_dict == None:  action += " non-existent"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
              if "group" in principal_type:
                  action += " %s %s"% tuple(reversed(principal_type.split('/')))
              else:
                  action += " %s" % principal_type
          if dirname:
              action += " from"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % dirname
          if expected_obj_dict:
              action += " via"
              if 'expected' in notes:      action += " (%s)" % notes['expected']
              action += " %s" % "/".join(expected_obj_dict.keys())
          self.print_start(action)

      url = "/ws.v1/%s/%s/%s" % (principal_type,dirname,principal_name)
      url = urllib.quote(url)
      if self.print_requests:
          print "\nGET ", url
      response = self.wsc.get(url) 
      if expected_obj_dict == None: 
        if response.status == httplib.OK:
          if self.print_progress:
              self.print_end("Found", good=False)
          print "Expected non-OK value, but got %s: %s" %  \
          (response.status,response.getBody())
        if self.print_progress:
            self.print_end("Expected error")
        return

      if self.response_is_valid(response):
        body = response.getBody()
        actual_obj_dict = simplejson.loads(body)
        assert dict_is_same(actual_obj_dict, expected_obj_dict), \
               "Mismatched Dictionary\nExpected: '%s'\nGot: '%s'" % \
               (expected_obj_dict, actual_obj_dict)
      if self.print_progress:
          if expected_obj_dict:
              self.print_end("Found")
          else:
              self.print_end("Expected none")
 
  # does a search_* and compares the returned list to the expected list
  # if 'dirname' is "" or None, all directories are searched
  def verify_search_principals(self, principal_type, dirname, 
                               query, expected_name_list, notes={}):
      if self.print_progress:
          action = "Searching"
          if query:  action += ""
          else:      action += " all"
          if principal_type:
              action += " %s" % principal_type
              action += " lists"
              if 'principal' in notes:  action += " (%s)" % notes['principal']
          if dirname:
              action += " in"
              if 'directory' in notes:  action += " (%s)" % notes['directory']
              action += " %s" % dirname
          if query:
              action += " by"
              if 'query' in notes:      action += " (%s)" % notes['query']
              action += " %s" % "/".join(query.keys())
          self.print_start(action)

      query_str = "?"
      query_args = []
      for key,value in query.iteritems():
        query_args.append(urllib.quote(key) + "=" + urllib.quote(value))
      query_str += "&".join(query_args)

      if dirname is None or dirname == "": 
        url = urllib.quote("/ws.v1/%s" % (principal_type))
      else :  
        url = urllib.quote("/ws.v1/%s/%s" % (principal_type,dirname))
      if self.print_requests:
          print "\nGET ", url
      response = self.wsc.get(url + query_str) 
      if expected_name_list == None: 
        if response.status == httplib.OK:
          if self.print_progress:
              self.print_end("Found", good=False)
          print "Expected NOT_FOUND, but got %s: %s" 
          (response.status,response.getBody())
        if self.print_progress:
            self.print_end("Expected error")
        return
      if self.response_is_valid(response):
        body = response.getBody()
        actual_name_list = simplejson.loads(body)
        assert list_is_same(actual_name_list, expected_name_list), \
               "Mismatched List\n\tExpected: '%s'\n\tGot: '%s'" % \
                (expected_name_list, actual_name_list)
      if self.print_progress:
          if expected_name_list:
              self.print_end("Found")
          else:
              self.print_end("Expected none")


def random_attribute_modifier(ptype, info, seed="not implemented"):
    #TODO implement a seed for reproducibility
    #TODO but first, actually finish this function
    '''
    Modifies a random attribute of the given principal's information
    Yields a query (dictionary) that would locate the new change
    Sending 'revert' restores the original value, if possible
    If nothing is provided, skips cleanly
    Example use:
        mod = random_attribute_modifier('host', info)
        query = mod.next()
        wst.verify_search_principals('hosts', '', query, info)
        mod.send('revert')
    '''
    value = {}
    old_value = {}
    if ptype == "host":
        value = {"dladdr": "00:00:00:00:00:00", "is_router" : "False",
               "is_gateway" : "False"}
        info["netinfos"].append(value.copy())
        location = info["netinfos"]
    if ptype == "location":
        value = {"dpid": "444444", "port": "65"}
        # Retrieve old values, storing only those replaced
        values = [(key, info.pop(key,None)) for key in value]
        for k,v in values:
           if v != None:  old_value[k] = v
        # Overwrite old values
        info.update(value)
        location = [info]
    if ptype == "switch":
        value = {"dpid": "2000"}
        values = [(key, info.pop(key,None)) for key in value]
        for k,v in values:
           if v != None:  old_value[k] = v
        info.update(value)
        location = [info]
    if ptype == "user":
        value = {"phone": "(124) 816-3264"}
        values = [(key, info.pop(key,None)) for key in value]
        for k,v in values:
           if v != None:  old_value[k] = v
        info.update(value)
        location = [info]

    # kludge: these may one day be searchable
    ir = value.pop('is_router',None)
    ig = value.pop('is_gateway',None)
    sent = (yield value)
    assert sent == 'revert', "Allowed sends: 'revert'.  Received: %s" % sent

    # To revert, we search all items in the list 'location' for
    # dictionary entries matching the modified values.  When found,
    # they are replaced by the original values, if they exist,
    # or deleted, if they did not previous exist.
    found = 0
    for val in value:
      for i in xrange(len(location)):
        for v in location[i]:
            # This won't work for aliases...
            if v != val:   continue
            if not old_value or val not in old_value or not old_value[val]:
                del location[i][v]
                if location[i] == {}:    del location[i]
                # kludge: these may one day be searchable
                elif location[i] == {'is_gateway':'False', 'is_router':'False'}:
                    del location[i]
            else:
                location[i][v] = old_value[v]
            found += 1
            break
    assert found == len(value), "Restored %d but %d modified: %s" % \
                                (found, len(value), value)
    if old_value:    yield old_value
    else:            yield None


def random_query_generator(ptype, info, seed="not implemented"):
    #TODO implement a seed for reproducibility
    '''
    Generator function, creates a list of all possible attribute queries,
    then randomizes the order and returns them one at a time.  Iterable.
    If no possibilities are created, is skipped cleanly.
    '''
    possible = []

    if ptype == "host":
        for k,v in info.iteritems():
            if k == 'aliases':
                possible.extend([{'name':alias} for alias in v])
            elif k == 'netinfos':
                possible.extend([netinfo.copy() for netinfo in v])
                # kludge: these may one day be searchable
                for item in possible:
                    item.pop('is_gateway',None)
                    item.pop('is_router',None)
            else:
                possible.append({k:v})
    if ptype in ("location", "switch", "user"):
        for k, v in info.iteritems():
            possible.append({k:v})

    from random import random
    randomized = []
    for item in possible:
        i = int((len(randomized)+1)*random())
        randomized.insert(i, item)

    for item in randomized:
        yield item


def run_basic_principal_tests(ptype, dir, info):
    test_indicator = "test"
    name = test_indicator + ptype
    mangled_name = dir + ";" + name
    info['name'] = name
    wst = WSTester()

    wst.print_begin("Testing %s in %s" % (ptype, dir.replace("_"," ").title()))

    if ptype == 'user':
        check = wst.wsc.get(urllib.quote("/ws.v1/%s/%s/%s" % \
                         (ptype,dir,'admin')))
        if check.status == httplib.OK:
            wst.delete_principal(ptype, dir, 'admin', 
                notes={'principal':'to simplify'})

    # Search the void
    wst.verify_search_principals(ptype, dirname="", query={},\
                                 expected_name_list=[], notes={'principal':'empty'})

    # Creation
    expected = info
    wst.put_principal(ptype, dir, name, info)
    wst.verify_get_principal(ptype, dir, name, expected, \
                             notes={'principal':'newly-created'})

    if True:
#    try:
        ## General Search
        expected = [mangled_name]
        wst.verify_search_principals(ptype, "", {}, expected, \
                                     notes={'principal':'non-empty'}) 

        expected = [mangled_name]
        wst.verify_search_principals(ptype, dir, {}, expected)

        ## Search by Attributes
        queries = random_query_generator(ptype, info)
        for query in queries:
            expected = [mangled_name]
            wst.verify_search_principals(ptype, "", query, expected)

        ## Modification
        # Change attribute, verify change
        modifier = random_attribute_modifier(ptype, info)
        new_value = modifier.next()
        expected = info
        note = {'contents':'changed %s' % '/'.join(new_value.keys())}
        wst.put_principal(ptype, dir, name, info, note)
        wst.verify_get_principal(ptype, dir, name, expected)

        # Search by new attribute
        query = new_value
        expected = [mangled_name]
        wst.verify_search_principals(ptype, dir, query, expected, \
                                     notes={'query':'new'})

        # Restore old value
        reverted_value = modifier.send('revert')
        expected = info
        note = {'contents':'reverted %s' % '/'.join(new_value.keys())}
        wst.put_principal(ptype, dir, name, info, note)
        wst.verify_get_principal(ptype, dir, name, expected)

        ## Bad searches by Attributes
        query = new_value
        expected = [ ]
        note = {'query': 'removed'}
        wst.verify_search_principals(ptype, "", query, expected, note)
        query = {'non-existent-value': 'foo'}
        expected = None
        wst.verify_search_principals(ptype, "", query, expected, \
                                     notes={'query':'non-existent'})

    if False:
#    except Exception,e:
        # To save from having to remove testing.sqlite each failure
        # Has unfortunate side effect of less-useful debugging
        wst.print_end('! Exception !', good=False)
        wst.delete_principal(ptype, dir, name)
        raise(e)

    ## Deletion
    expected = None
    wst.delete_principal(ptype, dir, name)
    wst.verify_get_principal(ptype, dir, name, expected)


def run_group_tests(dir, info):
    from copy import deepcopy

    group = "group"
    test_indicator = "test"
    name = test_indicator + group
    mangled_name = dir + ";" + name
    info['name'] = name

    principals = ['user','host','location']
    for ptype in principals:
        gtype = group +"/"+ ptype
        wst = WSTester()
        wst.print_begin("Testing %s in %s" % (gtype, dir.replace("_"," ").title()))

        # Determine what groups already exist (none for all but users)
        groups = []
        # There are several user groups that are always in NOX Directory
        if ptype == "user" :
            guserdir = "NOX Directory"
            prefix = "NOX"
            groupnames = ["No access", "Policy administrators", \
                          "Network operators", "Viewer", "Superusers", \
                          "Security operators"]
            # Groups look like 'NOX Directory;NOX_No_access'
            groups = [guserdir+";"+"_".join([prefix]+g.split()) \
                      for g in groupnames]
        expected = groups
        wst.verify_search_principals(gtype, dirname="", query={},\
                             expected_name_list=expected, notes={'principal':'empty'})

        # Check for non-existant group
        expected = None
        wst.verify_get_principal(gtype, dir, name, expected, \
                                 notes={'principal':'non-existant'})

        expected = deepcopy(info)
        unexpected = None

        # Create that group
        expected['name'] = mangled_name
        wst.put_principal(gtype, dir, name, info)
        # Check for group
        wst.verify_get_principal(gtype, dir, name, expected, \
                                 notes={'principal':'newly-added'})

        # Create/Add/Check a principal
        pdir = dir
        pclass = "principal"
        pname = test_indicator + pclass
        wst.add_group_member(gtype, dir, name, pdir, pname, pclass)
        expected['member_names'].append(pdir +";"+ pname)
        wst.verify_get_group_member(gtype, dir, name, pdir, pname, pclass, \
                                    expected, notes={'principal':'newly-added'})

        # Create/Add/Check a subgroup
        sdir = dir
        sclass = "subgroup"
        sname = test_indicator + sclass
        wst.put_principal(gtype, sdir, sname, {})
        wst.add_group_member(gtype, dir, name, sdir, sname, sclass)
        expected['subgroup_names'].append(sdir +";"+ sname)
        global empty_subgroup
        sexpected = deepcopy(empty_group)
        sexpected['name'] = sdir +";"+ sname
        wst.verify_get_principal(gtype, dir, sname, sexpected, \
                                 notes={'principal':'newly-added'})

        # Add old principal to subgroup
        wst.add_group_member(gtype, sdir, sname, pdir, pname, pclass)
        wst.verify_get_principal(gtype, dir, name, expected, \
                                 notes={'principal':'subgroup'})

        # Remove old principal from subgroup
        wst.remove_group_member(gtype, dir, name, pdir, pname, pclass, \
                                notes={'principal':'newly-added'})
        wst.verify_get_group_member(gtype, dir, name, pdir, pname, pclass, \
                             unexpected, notes={'principal':'recently-deleted'})
        # Add it again
        try:
             wst.add_group_member(gtype, sdir, sname, pdir, pname, pclass, \
                                 notes={'principal':'already-added'})
             wst.print_end("Added?!?", good=False)
             exit(1)
        except AssertionError:
            wst.print_end("Expected assertion failure")

        # Remove principal from subgroup
        wst.remove_group_member(gtype, sdir, sname, pdir, pname, pclass, \
                                notes={'principal':'doubly-added'})
        expected['member_names'].pop()

        # Check for principal in subgroup
        wst.verify_get_group_member(gtype, sdir, sname, pdir, pname, pclass, \
                             unexpected, notes={'principal':'recently-deleted'})

        # Check for principal in group
        wst.verify_get_group_member(gtype, dir, name, pdir, pname, pclass, \
                             unexpected, notes={'principal':'less-recently-deleted'})

        # Delete subgroup
        wst.remove_group_member(gtype, dir, name, sdir, sname, sclass)
        wst.delete_principal(gtype, sdir, sname)
        expected['subgroup_names'].pop()

        # Check group
        wst.verify_get_principal(gtype, dir, name, expected, \
                                 notes={'principal':'removed'})

        ## Deletion
        wst.delete_principal(gtype, dir, name)
        wst.verify_get_principal(gtype, dir, name, unexpected)



empty_location = {"name": None, "dpid": None, "port": None}
empty_host =     {"name": None, "netinfos": [], "aliases": []}
empty_netinfos = {"is_router": False, "is_gateway": False}
empty_switch =   {"name": None, "dpid": None}
empty_user =     {"name": None, "user_id": None, "user_real_name": None, \
                  "location": None, "phone": None, "user_email": None}
empty_group =    {"name": None, "description": None, "member_names": [], \
                  "subgroup_names": []}

dir = ""
if __name__ == '__main__':
    from sys import argv
    dir = ["NOX Directory","sepl_directory"]
    # Silently ignores bad input
    if len(argv) > 1 and argv[1] in dir:  dir = argv[1]
    else:                                 dir = dir[0]
    
    name = "Name not overwritten by testing!"
    # Location
    info = {"name" : name, \
            "dpid" : "1111", \
            "port" : "99" } 
    run_basic_principal_tests("location", dir, info)

    # Host
    info =  {"name"     : name,
             "netinfos" : [ { "nwaddr": "128.9.9.9", 
                              "is_router" : "False", 
                              "is_gateway" : "False"
                           }, 
                           {  "dpid": "1", 
                              "port": "99",
                              "is_router" : "False",
                              "is_gateway" : "False"
                           }
                          ],
             # "description" : "Not-yet-describable %s %s" % (test_ind, ptype),
             # "creds"    : {"not": ("implemented", "just", "yet")},
             "aliases"  : []
            }
    run_basic_principal_tests("host", dir, info)

    # Switch
    info = {"name": name, \
            # "creds": {"also": ("not", "present"), \
            "dpid": "88321707474947"} 
    run_basic_principal_tests("switch", dir, info)

    # User
    info = {"name": name, \
            "user_id": '1234', \
            "user_real_name": "Real McCoy", \
             # "description" : "Not-yet-describable %s %s" % \
             #                 (test_ind, ptype), \
            "location": "Aricin, USA 10001", \
            "phone": "(652) 123-5813", \
            # "creds": {"waiting": ("until", "activited")}
            # "password_update_epoch": 1000000000, \
            # "password_expire_epoch": 1234567890
            "user_email": "rmc@email.org"}
    #run_basic_principal_tests("user", dir, info)

    # Group
    test_ind = "test" #mini-kludge
    ptype = "group" #mini-kludge
    info = {"name": name, \
            "description": "Possibly-describable %s %s" % (test_ind, ptype), \
            "member_names": [], \
            "subgroup_names": []}
    run_group_tests(dir,info)



#################################################################  |  #########
################# L E G A C Y  *  T E S T I N G  *  C O D E ##### \|/ #########
#################################################################  '  #########


wst = WSTester()

#  This code is useful for setting up binding storage state, but is currently useless 
#  because authenticator has yet to be updated to work with the new directory interfaces
#
#wst.do_auth_event("authenticate","1",23,"0b:0f:12:00:00:00", "128.2.19.99","dan","javelina")
#for i in range(0,10): 
#  wst.do_auth_event("authenticate","1",str(i),"00:00:00:00:00:0"+str(i), 
#                        "128.2.19.9"+str(i),"user"+str(i),"host"+str(i))
#

name = "myswitch"
dirname = dir
# manually mangle name b/c we can't import directorymanager
mangled_name = dirname + ";" + name 

wst.print_begin("Legacy Testing: Switches")

# this test assumes we start from a clear directory store
# for now, it is sufficient to just delete testing.sqlite
# let's check by making sure an empty query returns no names
q = { }
wst.verify_search_principals("switch","", q, [ ])

# create switch (note: during a create, the principal name is 
# determined by the URL, not placed in the dictionary
myswitch = { "dpid" : "88321707474947" } 
wst.put_principal("switch", dirname, name, myswitch)

# verify that we can retrive the switch info by name
myswitch["name"] = name
wst.verify_get_principal("switch", dirname, name, myswitch)

# verify that search on dpid returns results when it should
q = { "dpid" : "88321707474947"}
wst.verify_search_principals("switch","", q, [ mangled_name ]) 
wst.verify_search_principals("switch",dirname, q , [ mangled_name ]) 

# empty query should match all records
q = { }
wst.verify_search_principals("switch","", q, [ mangled_name ]) 
wst.verify_search_principals("switch",dirname, q , [ mangled_name ]) 

# query for non-existent directory should return a 404
wst.verify_search_principals("switch","nonexistent directory", q , None) 

# this query should match no records, returning results
q = { "dpid" : "2000"}
wst.verify_search_principals("switch","", q, [ ]) 
wst.verify_search_principals("switch",dirname, q , [ ]) 

# modify the switch 
myswitch["dpid"] = "2000"
wst.put_principal("switch", dirname, name, myswitch)
wst.verify_get_principal("switch", dirname, name, myswitch)

# now, these queries should match a record, 
q = { "dpid" : "2000"}
wst.verify_search_principals("switch","", q, [mangled_name ]) 
wst.verify_search_principals("switch",dirname, q , [ mangled_name ]) 

# and a query for the old dpid should return no results
q = { "dpid" : "88321707474947" }
wst.verify_search_principals("switch","", q, [ ]) 
wst.verify_search_principals("switch",dirname, q , [ ]) 

# now let's delete it
wst.delete_principal("switch", dirname, name)
wst.verify_get_principal("switch", dirname, name, None)

# queries should no longer match a record, 
q = { "dpid" : "2000"}
wst.verify_search_principals("switch","", q, [ ]) 
wst.verify_search_principals("switch",dirname, q , [ ]) 

# even the query for all results should be empty 
q = {}
wst.verify_search_principals("switch","", q, [ ]) 
wst.verify_search_principals("switch",dirname, q , [  ]) 

