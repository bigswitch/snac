# Copyright 2008 (C) Nicira, Inc.

"""
DHCP configuration class to enable convenient access and storing of
subnet groups to the properties.  Not used by the UI as it accesses
the configuration using the simple config web service.
"""

from nox.lib.netinet.netinet import create_ipaddr

class DHCPConfig:
    def __init__(self, cfg):
        self.globals = {}
        self.subnets = {}
        self.fixedaddresses = {}
        self.cfg = cfg

    def load(self, p):
        """
        Parse the configuration from the database
        """
        for key in p.keys():
            if not key.find('subnet-') == 0 and \
                    not key.find('fixed_address-') == 0:
                self.globals[key] = p[key]
            elif key.find('subnet-') == 0:
                value = p[key]
                key = key[len('subnet-'):]
                subnet_id = key[:key.find('-')]
                key = key[key.find('-') + 1:]
                if not self.subnets.has_key(subnet_id):
                    self.subnets[subnet_id] = {}
                self.subnets[subnet_id][key] = value
            else:
                value = p[key]
                key = key[len('fixed_address-'):]
                hostname = key[:key.rfind('-')]
                key = key[key.rfind('-') + 1:]
                if not self.fixedaddresses.has_key(hostname):
                    self.fixedaddresses[hostname] = {}
                self.fixedaddresses[hostname][key] = value

    def store(self, properties):
        """
        Update the changes to the database
        """
        for key in properties.keys():
            del properties[key]
        
        for key in self.globals.keys():
            p[key] = self.globals[key]

        for subnet_id in self.subnets.keys():
            subnet = self.subnets[subnet_id]

            for key in subnet.keys():
                p['subnet-%s-%s' % (subnet_id, key)] = subnet[key]

        for hostname in self.fixedaddresses.keys():
            fixedaddress = self.fixedaddresses[hostname]

            for key in fixedaddress.keys():
                p['fixed_address-%s-%s' % (hostname, key)] = fixedaddress[key]

    def emit(self):
        """
        Return an ISC DHCP daemon compliant main configuration file.
        """
        conf = "## Generated automatically from NOX database.\n" + \
            "## Use NOX to regenerate.\n\n"

        def conv(key, values):
            values = list(values)
            values = map(lambda v: v.value, values)

            if key.find('option_') == 0:
                # only 'options' require quotes around their string
                # parameters
                def quote(s):
                    #if isinstance(s, basestring): s = '"' + s + '"'
                    return s

                values = map(quote, values)

            values = map(lambda s: str(s), values)
            return ', '.join(values)

        for key in self.globals.keys():
            if key == 'option_domain-name':
                conf += '%s "%s";\n' % (key.replace('option_', 'option '),
                                        conv(key, self.globals[key]))
            else:
                conf += '%s %s;\n' % (key.replace('option_', 'option '),
                                      conv(key, self.globals[key]))

        conf += '\n'
            
        conf += "# Configured subnets:\n"
        subnets_configured = {}
        for subnet_id in self.subnets.keys():
            subnet = self.subnets[subnet_id]
            
            options = ''
            for key in subnet.keys():
                if key == 'subnet' or key == 'netmask' or \
                        key == 'range-start': continue

                if key == 'range-end':
                    # Range gets a special treatment
                    options += '  range %s %s;\n' % \
                        (conv('range', subnet['range-start']), 
                         conv('range', subnet['range-end']))
                elif key == 'option_domain-name':
                    options += '  %s "%s";\n' % \
                        (key.replace('option_', 'option '),
                         conv(key, subnet[key]))
                else:
                    options += '  %s %s;\n' % \
                        (key.replace('option_', 'option '),
                         conv(key, subnet[key]))

            ip = create_ipaddr(str(subnet['subnet'][0]))
            netmask = create_ipaddr(str(subnet['netmask'][0]))
            subnets_configured[ip & netmask] = True;

            conf += ("subnet %s netmask %s {\n" + options + \
                         "}\n") % (ip & netmask, netmask)

        conf += "# Stub entries for local network interfaces not above:\n"
        for interface in self.cfg.get_interfaces():
            ip = create_ipaddr(interface.ip4addr)
            netmask = create_ipaddr(interface.ip4mask)
            
            if not subnets_configured.has_key(ip & netmask) and \
                    not (ip & netmask) == create_ipaddr('127.0.0.0') and \
                    not (ip & netmask) == create_ipaddr('0.0.0.0'):
                conf += "subnet %s netmask %s { }\n" % (ip & netmask, netmask)
            
        conf += '\n'
            
        i = 0
        for hostname in self.fixedaddresses.keys():
            fixedaddress = self.fixedaddresses[hostname]

            addresses = map(lambda v: v.value, fixedaddress['ip4addr'])

            conf += ("# host '%s_%s'\nhost %s {\n  hardware ethernet %s;\n  fixed-address %s;\n}\n") % \
                (fixedaddress['directory'][0], 
                 fixedaddress['hostname'][0], 
                 'host_%d' % i,
                 fixedaddress['hwaddr'][0],
                 ', '.join(addresses))
            i += 1

        return conf
