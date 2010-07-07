from nox.lib.directory import Directory

# All groups listed below will be created at startup if they don't exist
default_groups = (
    # All default groups are of the form 
    # (<group_type>, <group_name>, <group_description>)
    #
    # Valid group types:
    #   Directory.SWITCH_PRINCIPAL_GROUP
    #   Directory.LOCATION_PRINCIPAL_GROUP
    #   Directory.HOST_PRINCIPAL_GROUP
    #   Directory.USER_PRINCIPAL_GROUP
    #   Directory.DLADDR_GROUP
    #   Directory.NWADDR_GROUP
    #
    # examples:
    #  (Directory.SWITCH_PRINCIPAL_GROUP, 'sgroup1', 'Example switch group 1'),
    #  (Directory.DLADDR_GROUP, 'dlgroup1', 'Example dladdr group 1'),
    #
    (Directory.HOST_PRINCIPAL_GROUP, 'DHCP Servers',
     'Valid DHCP servers for the network.'),
    (Directory.HOST_PRINCIPAL_GROUP, 'DNS Servers',
     'Valid DNS servers for the network.'),
    (Directory.HOST_PRINCIPAL_GROUP, 'Controllers',
     'Valid Nicira controllers for the network.'),
    (Directory.HOST_PRINCIPAL_GROUP, 'LDAP Servers',
     'Valid LDAP servers for the network.'),
    (Directory.HOST_PRINCIPAL_GROUP, 'User Auth Portals',
     'Valid user authentication portals for the network.'),
    (Directory.HOST_PRINCIPAL_GROUP, 'Unrestricted Servers',
     'Hosts that should be allowed unrestricted access to the network'),
    (Directory.LOCATION_PRINCIPAL_GROUP, 'User Auth Portal Locations',
     'Locations in the network for which the user auth portal should be used to authenticate users.'),
    (Directory.SWITCH_PRINCIPAL_GROUP, 'User Auth Portal Switches',
     'Switches in the network for which the user auth portal should be used to authenticate users.'),
    (Directory.NWADDR_GROUP, 'User Auth Client Subnets', 
      'IP prefixes in the network containing clients that must perform captive portal authentication.')
    )
