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
from socket import ntohs
from time import time

from nox.lib.core import Component

from twisted.internet import defer
from twisted.python.failure import Failure
from nox.netapps.authenticator.pyauth import PyAuth
from nox.webapps.webservice.webservice import *
from nox.netapps.directory.directorymanager import directorymanager, mangle_name
from nox.netapps.directory.directorymanagerws import WSPathExistingDirName
from nox.ext.apps import sepl
from nox.ext.apps.miscws.policyws import WSPathExistingPolicyId, \
        WSPathExistingRuleId
from nox.ext.apps.visibility.pyflow_cache import pyflow_cache

lg = logging.getLogger('visibility_ws')

class visibility_ws(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self._dm = None
        self._fc = None
        self._policy = None
        self._wsv1 = None
        self._auth = None

    def install(self):
        self._auth = self.resolve(PyAuth)
        self._dm = self.resolve(directorymanager)
        self._fc = self.resolve(pyflow_cache)
        self._wsv1 = self.resolve(webservice).get_version("1")
        self._policy = self.resolve(sepl.policy.PyPolicyComponent)

        # GET /ws.v1/host/<dir name>/<principal name>/flow
        host_flow_path = (WSPathStaticString("host"),
                WSPathExistingDirName(self._dm, "<dir name>"),
                WSPathArbitraryString("<principal name>"),
                WSPathStaticString("flow"))
        self._wsv1.register_request(self.get_host_flows, "GET",
                host_flow_path, "Get flow history for host")
                                     
        # GET /ws.v1/policy/<policy id>/rule/<rule id>/flow
        policy_flow_path = (WSPathStaticString("policy"),
                WSPathExistingPolicyId(self._policy),
                WSPathStaticString("rule"),
                WSPathExistingRuleId(self._policy),
                WSPathStaticString("flow"))
        self._wsv1.register_request(self.get_policy_flows, "GET",
                policy_flow_path, "Get flow history for policy")

        # GET /ws.v1/nox/flow
        nox_flow_path = (WSPathStaticString("nox"), WSPathStaticString("flow"))
        self._wsv1.register_request(self.get_flows, "GET",
                nox_flow_path, "Get recent flow history")

    def getInterface(self):
        return str(visibility_ws)

    def get_name(self, principal_id):
        #currently, we get the names from authenticator, which may result in
        #not having a name if authenticator has timed it out
        #TODO: persist names?
        name = unicode(self._auth.get_name(principal_id), 'utf-8')
        if name == self._auth.get_unknown_name():
            name = "discovered;unknown name (%d)"%principal_id
        return name

    def flow_infos_to_json(self,fis): 
        return simplejson.dumps(self.flow_infos_to_dict(fis))

    def flow_infos_to_dict(self, fis):
        def flow_to_str_dict(flow):
            ret = {}
            for var in ('dl_src', 'dl_dst'):
                ret[var] = str(getattr(flow, var))
            for var in ('in_port', 'dl_vlan', 'tp_src', 'tp_dst'):
                ret[var] = str(ntohs(getattr(flow, var)))
            if ret['dl_vlan'] == "65535":
                ret['dl_vlan'] = ""
            ret['dl_type'] = "0x%04X"%ntohs(getattr(flow, 'dl_type'))
            ret['nw_src'] = str(create_ipaddr(c_ntohl(getattr(flow, 'nw_src')))
                    or '')
            ret['nw_dst'] = str(create_ipaddr(c_ntohl(getattr(flow, 'nw_dst')))
                    or '')
            ret['nw_proto'] = "0x%02X"%getattr(flow, 'nw_proto')
            return ret
        ret = []
        for fi in fis:
            sfi = {}
            sfi['flow_id'] = str(fi['id'])
            sfi['received_ts'] = str(fi['received_ts'])
            sfi.update(flow_to_str_dict(fi.pop('flow')))
            sfi['dpid'] = str(fi['dpid'])

            sfi['src_users'] = [self.get_name(user) for user in fi['src_users']]
            sfi['src_host'] = self.get_name(fi['src_host'])
            sfi['src_user_groups'] = [self.get_name(ug)
                    for ug in fi['src_user_groups']]
            sfi['src_host_groups'] = [self.get_name(sg)
                    for sg in fi['src_host_groups']]
            sfi['src_location_groups'] = [self.get_name(sg)
                    for sg in fi['src_location_groups']]
            sfi['src_switch_groups'] = [self.get_name(sg)
                    for sg in fi['src_switch_groups']]
            sfi['src_dladdr_groups'] = [self.get_name(sg)
                    for sg in fi['src_dladdr_groups']]
            sfi['src_nwaddr_groups'] = [self.get_name(sg)
                    for sg in fi['src_nwaddr_groups']]

            sfi['dst_users'] = [self.get_name(user) for user in fi['dst_users']]
            sfi['dst_host'] = self.get_name(fi['dst_host'])
            sfi['dst_user_groups'] = [self.get_name(ug)
                    for ug in fi['dst_user_groups']]
            sfi['dst_host_groups'] = [self.get_name(sg)
                    for sg in fi['dst_host_groups']]
            sfi['dst_location_groups'] = [self.get_name(sg)
                    for sg in fi['dst_location_groups']]
            sfi['dst_switch_groups'] = [self.get_name(sg)
                    for sg in fi['dst_switch_groups']]
            sfi['dst_dladdr_groups'] = [self.get_name(sg)
                    for sg in fi['dst_dladdr_groups']]
            sfi['dst_nwaddr_groups'] = [self.get_name(sg)
                    for sg in fi['dst_nwaddr_groups']]

            sfi['policy_id'] = str(fi['policy_id'])
            sfi['policy_rules'] = [str(r) for r in fi['policy_rules']]
            action_list = []
            for r in fi['policy_rules']:
                rule = self._policy.rules.get(r)
                if rule is not None:
                    action_list.append(rule.action_ustr().encode('utf-8'))
                else:
                    action_list.append("unknown")
            sfi['policy_actions'] = action_list

            sfi['routing_action_taken'] = fi['routing_action']
            ret.append(sfi)
        return ret
        
    def get_host_flows(self, request, arg):
        try:
            hostname = arg["<principal name>"]
            dirname = arg["<dir name>"]
            mangled_name = mangle_name(dirname, hostname).encode('utf-8')
            flows = self._fc.get_host_flows(mangled_name)
            return self.flow_infos_to_json(flows)
        except Exception, e:
            msg = str(e) or "Unknown Error"
            return internalError(request, "Failed to retrieve flows: %s"%msg)

    def get_policy_flows(self, request, arg):
        try:
            policyid = arg["<policy id>"]
            ruleid = arg["<rule id>"]

            if policyid != self._policy.policy_id:
                #we only cache flows for the current policy
                return simplejson.dumps("[]")

            flows = self._fc.get_policy_flows(policyid, ruleid)
            return self.flow_infos_to_json(flows)
        except Exception, e:
            msg = str(e) or "Unknown Error"
            return internalError(request, "Failed to retrieve flows: %s"%msg)

    def get_flows(self, request, arg):
        try:
            if request.args.get('allowed', ['false'])[0].lower() == 'true':
                flows = self._fc.get_allowed_flows()
            elif request.args.get('denied', ['false'])[0].lower() == 'true':
                flows = self._fc.get_denied_flows()
            else:
                flows = self._fc.get_all_flows()
            return self.flow_infos_to_json(flows)
        except Exception, e:
            msg = str(e) or "Unknown Error"
            return internalError(request, "Failed to retrieve flows: %s"%msg)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return visibility_ws(ctxt)
    return Factory()
