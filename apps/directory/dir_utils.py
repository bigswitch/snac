
from nox.lib.directory_factory import Directory_Factory


# convert a string that is intended to be a glob and 
# make it so we can safely use it to create a python regex.
# this is based a method in dojo:
# dojo-release-1.1.1/dojo/data/util/filter.js
def glob_to_regex(glob_str, ignore_case=True): 
  rxp = ""
  if ignore_case:
    rxp += "(?i)"
  rxp += "^"
  i = 0 
  while i < len(glob_str): 
    c = glob_str[i]
    if c == '\\':
        rxp += c
        i += 1
        rxp += glob_str[i]
    elif c == '*':
        rxp += ".*" 
    elif c ==  '?':
        rxp += "." 
    elif c == '$' or \
      c == '^' or \
      c == '/' or \
      c == '+' or \
      c == '.' or \
      c == '|' or \
      c == '(' or \
      c == ')' or \
      c == '{' or \
      c == '}' or \
      c == '[' or \
      c == ']' : 
        rxp += "\\"
        rxp += c
    else :
        rxp += c
    i += 1

  rxp += "$"
  return rxp 

def filter_list(tofilter, nomatch_fn):
        i = 0
        while i < len(tofilter):
          if nomatch_fn(tofilter[i]):
              tofilter.pop(i)
          else:
              i += 1

name_to_type_map = { "location" : Directory_Factory.LOCATION_PRINCIPAL, 
                     "switch" : Directory_Factory.SWITCH_PRINCIPAL, 
                     "user" : Directory_Factory.USER_PRINCIPAL,
                     "host" : Directory_Factory.HOST_PRINCIPAL
                   } 

def convert_map_name_to_type(map): 
  new_map = {} 
  for key,value in map.iteritems(): 
    if key in name_to_type_map: 
      new_map[name_to_type_map[key]] = value
  return new_map

