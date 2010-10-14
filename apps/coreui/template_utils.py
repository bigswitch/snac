import urllib


def utf8quote(s): 
  if isinstance(s, unicode):
    s = s.encode('utf-8')
  return urllib.quote(s)

def utf8unquote(s):
  return urllib.unquote(s).decode('utf-8')

# 'cap_ptype' is the principal type starting with a capital letting (e.g., 'Host') 
# 'full_name' is the fully mangled name of the principal
def get_principal_path(cap_ptype, full_name):
  if cap_ptype == "Switch": 
    return "/Monitors/Switches/SwitchInfo?name=%s" % utf8quote(full_name)
  return "/Monitors/%ss/%sInfo?name=%s" % (cap_ptype,cap_ptype, utf8quote(full_name))

# 'cap_ptype' is the principal type starting with a capital letting (e.g., 'Host') for host group
# 'full_name' is the fully mangled name of the group
def get_group_path(cap_ptype, full_name):
  if cap_ptype == "IP": 
    return "/Monitors/Groups/NWAddrGroupInfo?name=%s" % (utf8quote(full_name))
  elif cap_ptype == "MAC": 
    return "/Monitors/Groups/DLAddrGroupInfo?name=%s" % (utf8quote(full_name))
  return "/Monitors/Groups/%sGroupInfo?name=%s" % (cap_ptype, utf8quote(full_name))
