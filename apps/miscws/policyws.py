import simplejson
import protocolsws
import logging

from nox.apps.coreui import webservice, web_arg_utils
from nox.ext.apps import sepl
from nox.ext.apps.sepl import compile
from nox.ext.apps.sepl.declare import *
from nox.lib.directory import DirectoryException
from nox.lib.netinet.netinet import create_datapathid_from_host, \
    create_eaddr, create_ipaddr, c_ntohl

from nox.lib.core import Component

from twisted.internet import defer
from twisted.python.failure import Failure

lg = logging.getLogger('policyws')

class policyws(Component):
    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.cur_policy_table = 'current_policy'
        self.rule_table = 'policy_rules'
        self.policy = None
        self.v1 = None

    def install(self):
        self.policy = self.resolve(str(sepl.policy.PyPolicyComponent))
        self.v1 = self.resolve(str(webservice.webservice)).get_version("1")

        self.v1.register_request(protocolsws.get_protocols, "GET", 
                                 (webservice.WSPathStaticString('protocols'), ),
                                 "Get the set of currently defined protocol.")

        self.v1.register_request(protocolsws.get_protocol, "GET",
                                 (webservice.WSPathStaticString('protocols'),
                                  protocolsws.WSPathExistProtocolIdent()),
                                 "Get a protocol's definition.")

        self.v1.register_request(protocolsws.modify_protocol, "PUT",
                                 (webservice.WSPathStaticString('protocols'),
                                  protocolsws.WSPathProtocolIdent()),
                                 "Modify/create a protocol's definition.")

        self.v1.register_request(protocolsws.delete_protocol, "DELETE",
                                 (webservice.WSPathStaticString('protocols'),
                                  protocolsws.WSPathExistProtocolIdent()),
                                 "Delete a protocol's definition.")

        self.v1.register_request(self.get_policy_names, "GET",
                                 (webservice.WSPathStaticString('policy'),
                                  webservice.WSPathStaticString('names')),
                                 "Get name mappings.")

        self.v1.register_request(self.get_policy, "GET",
                                 (webservice.WSPathStaticString('policy'), ),
                                 "Get installed policy id.")
        
        self.v1.register_request(self.get_stats, "GET",
                                 (webservice.WSPathStaticString('policy'), 
                                  webservice.WSPathStaticString('stats'), ),
                                 "Get basic policy stats.")

        self.v1.register_request(self.reset_stats, "DELETE",
                                 (webservice.WSPathStaticString('policy'), 
                                  webservice.WSPathStaticString('stats'), ),
                                 "Reset all policy stats; returns stats "
                                 "prior to delete")

        self.v1.register_request(self.get_rule, "GET",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rule'),
                                  WSPathExistingRuleId(self.policy)),
                                 "Get rule id's defintion.")
        # disabled since we need .../rule/<rule id>/<other_stuff>
        # we may want to move this under ../<rule id>/attribute/...
        #self.v1.register_request(self.get_rule_param, "GET",
        #                         (webservice.WSPathStaticString('policy'),
        #                          WSPathExistingPolicyId(self.policy),
        #                          webservice.WSPathStaticString('rule'),
        #                          WSPathExistingRuleId(self.policy),
        #                          WSPathRuleParam()),
        #                         "Get rule id's parameter value.")
        self.v1.register_request(self.get_rules, "GET",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rules')),
                                 "Get policy id's rules.")
        self.v1.register_request(self.get_rule_stats, "GET",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rule'),
                                  WSPathExistingRuleId(self.policy),
                                  webservice.WSPathStaticString('stats')),
                                 "Get rule id's enforcement stats.")
        self.v1.register_request(self.put_rule, "PUT",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rule'),
                                  WSPathExistingRuleId(self.policy)),
                                 "Modify a rule's attributes or definition.")
        self.v1.register_request(self.put_record_rule_senders, "PUT",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rule'),
                                  WSPathExistingRuleId(self.policy),
                                  webservice.WSPathStaticString('stats')),
                                 "Configure stats collection for a rule.")
        self.v1.register_request(self.put_analysis, "PUT",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('analysis'),
                                  webservice.WSPathStaticString('rules')),
                                 "Analyze a new policy relative to another.")
        self.v1.register_request(self.delete_rule, "DELETE",
                                 (webservice.WSPathStaticString('policy'),
                                  WSPathExistingPolicyId(self.policy),
                                  webservice.WSPathStaticString('rule'),
                                  WSPathExistingRuleId(self.policy)),
                                 "Delete a rule by id.")
        self.v1.register_request(self.post_rules, "POST",
                                 (webservice.WSPathStaticString('policy'), ),
                                 "Post a new policy.")

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        if isinstance(failure.value, DirectoryException) \
                and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                or failure.value.code == DirectoryException.REMOTE_ERROR):
            msg = failure.value.message
        if isinstance(msg, str):
            msg = unicode(msg, 'utf-8')
        return webservice.internalError(request, msg)

    def badReq(self, failure, request, fn_name):
        lg.error('%s: %s' % (fn_name, str(failure)))
        msg = failure.value.message
        if isinstance(msg, str):
            msg = unicode(msg, 'utf-8')
        return webservice.badRequest(request, msg)

    def get_policy_names(self, request, data):
        try:
            content = web_arg_utils.flatten_args(request.args)
            keys = ['inport', 'dpsrc', 'dlsrc', 'dldst', 'nwsrc', 'nwdst']
            for key in keys:
                if not content.has_key(key):
                    return webservice.badRequest(request, "Must include '%s' argument." % key)
            try:
                dp = create_datapathid_from_host(long(content['dpsrc']))
                if dp == None:
                    return webservice.badRequest(request, "Invalid datapath ID.")
            except ValueError, e:
                return webservice.badRequest(request, "Invalid datapath.")
            try:
                port = int(content['inport'])
            except ValueError, e:
                return webservice.badRequest(request, "Invalid inport.")
            
            dlsrc = create_eaddr(content['dlsrc'])
            dldst = create_eaddr(content['dldst'])
            if dlsrc == None or dldst == None:
                return webservice.badRequest(request, "Invalid MAC address.")
            nwsrc = create_ipaddr(content['nwsrc'])
            nwdst = create_ipaddr(content['nwdst'])
            if nwsrc == None or nwdst == None:
                return webservice.badRequest(request, "Invalid IP address.")
            def cb(names):
                try:
                    request.write(simplejson.dumps(names))
                    request.finish()
                except Exception, e:
                    self.err(Failure(), request, "get_names",
                             "Could not retrieve name mappings.")

            self.policy.authenticator.get_names(dp, port, dlsrc, c_ntohl(nwsrc.addr), dldst,
                                                c_ntohl(nwdst.addr), cb)
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_names",
                            "Could not retrieve name mappings.")
            
    # Wrapper so doesn't return error if used as errback
    def unlock_policy(self, res):
        return self.policy.unlock_policy(res)
        
    def get_policy(self, request, data):
        try:
            d = self.policy.lock_policy()
            d.addCallback(self.__get_policy__, request)
            d.addBoth(self.unlock_policy)
            d.addErrback(self.err, request, "get_policy",
                         "Could not retrieve policy ID.")
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_policy",
                            "Could not retrieve policy ID.")

    def __get_policy__(self, ignore, request):
        request.write(simplejson.dumps({'policy_id' : self.policy.policy_id,
                                        'user' : self.policy.user,
                                        'timestamp' : self.policy.timestamp }))
        request.finish()

    def get_rule(self, request, data):
        try:
            return simplejson.dumps(to_json_rule(self.policy.rules[data['<rule id>']]))
        except Exception, e:
            return self.err(Failure(), request, "get_rule",
                            "Could not retrieve policy rule.")
            

    def get_rule_stats(self, request, data):
        try:
            stats = self.policy.get_rule_stats(data['<rule id>'])
            if stats == None:
                return webservice.badRequest(request, "Could not retrieve rule stats for ID %u." % data['<rule id>'])

            stats['sender_macs'] = [ str(eth) for eth in stats['sender_macs'] ]
            return simplejson.dumps(stats)
        except Exception, e:
            return self.err(Failure(), request, "get_rule_stats",
                            "Could not retrieve policy rule stats.")
        
    def put_record_rule_senders(self, request, data):
        try:
            content = webservice.json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            elif not self.policy.set_record_rule_senders(data['<rule id>'],
                                                         content['record_senders']):
                return webservice.badRequest(request, "Could not set record senders for rule ID %u." % data['<rule id>'])
            return "Success"
        except Exception, e:
            return self.err(Failure(), request, "put_record_rule_senders",
                            "Could not set record rule senders field.")

    def get_rule_param(self, request, data):
        try:
            rule = self.policy.rules[data['<rule id>']]
            param = data['<param>']

            if param == 'priority':
                res = { param : rule.priority }
            elif param == 'condition':
                res = to_json_cond_wrap(rule.condition)
            elif param == 'actions':
                res = [ to_json_action(a) for a in rule.actions ]
            elif param == 'text':
                res = { param : rule.ustr() }
            elif param == 'exception':
                res = { param : rule.exception }
            elif param == 'protected':
                res = { param : rule.protected }
            elif param == 'rule_type':
                res = { param : rule.rule_type }
            elif param == 'description':
                res = { param : rule.description }
            elif param == 'comment':
                res = { param : rule.comment }
            elif param == 'expiration':
                res = { param : rule.expiration }
            elif param == 'policy_id':
                res = { param : rule.policy_id }
            elif param == 'user':
                res = { param : rule.user }
            elif param == 'timestamp':
                res = { param : rule.timestamp }

            return simplejson.dumps(res)
        except Exception, e:
            return self.err(Failure(), request, "get_rule_param",
                            "Could not retrieve rule parameter.")

    def get_rules(self, request, data):
        try:
            ordered = self.policy.rules.values()
            ordered.sort(None, compile.PyRule.get_order)
            return simplejson.dumps([to_json_rule(rule) \
                                         for rule in ordered])
        except Exception, e:
            return self.err(Failure(), request, "get_rules",
                            "Could not retrieve policy rules.")

    def get_stats(self, request, data): 
        try:
            exceptions = 0 
            protected = 0;
            for rule in self.policy.rules.itervalues(): 
                if rule.exception == True: 
                    exceptions += 1
                if rule.protected == True:
                    protected += 1
            ret = { "num_rules" : len(self.policy.rules), 
                    "num_exception_rules" : exceptions,
                    "num_protected_rules" : protected,
                    "num_allows" : self.policy.get_allows(),
                    "num_drops" : self.policy.get_denies() }
            return simplejson.dumps(ret)
        except Exception, e:
            return self.err(Failure(), request, "get_stats",
                            "Could not retrieve rule stats.")

    def reset_stats(self, request, data):
        ret = self.get_stats(request, data)
        self.policy.stats.clear_stats()
        return ret

    def put_rule(self, request, data):
        try:
            content = webservice.json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            d = self.policy.lock_policy()
            d.addCallback(self.__put_rule__, request, data, content)
            d.addBoth(self.unlock_policy)
            d.addErrback(self.err, request, "put_rule",
                         "Could not modify rule.")
        except Exception, e:
            return self.err(Failure(), request, "put_rule",
                            "Could not modify rule.")

    def __put_rule__(self, tmp, request, data, content):
        rule = self.policy.rules[data['<rule id>']]

        exc = rule.exception
        pro = rule.protected
        rt = rule.rule_type
        desc = rule.description
        com = rule.comment
        exp = rule.expiration

        d = self.__put_rule2__(request, data, content, rule)
        d.addCallbacks(self.__apply_policy__, self.__mod_failed__, (request,), None,
                       (request, rule, exc, pro, rt, desc, com, exp))
        return d

    def __apply_policy__(self, tmp, request):
        d = self.policy.apply(request.getSession().user.username)
        d.addCallback(self.write_policy_id, request)
        return d

    def __mod_failed__(self, res, request, rule, exc, pro, rt, desc, com, exp):
        rule.exception = exc
        rule.protected = pro
        rule.rule_type = rt
        rule.description = desc
        rule.comment = com
        rule.expiration = exp
        res.value.message = "Cannot modify rule: %s" % res.value.message
        return self.badReq(res, request, "put_rule")
        
    def __put_rule2__(self, request, data, content, rule):
        try:
            mod = False
            d = None

            if content.has_key('exception'):
                val = content['exception']
                if not isinstance(val, bool):
                    raise Exception("Invalid exception, expects bool.")
                rule.exception = val
                mod = True

            if content.has_key('protected'):
                val = content['protected']
                if not isinstance(val, bool):
                    raise Exception("Invalid protected, expects bool.")
                rule.protected = val
                mod = True

            if content.has_key('rule_type'):
                val = content['rule_type']
                if not isinstance(val, basestring):
                    raise Exception("Invalid rule type, expects string.")
                rule.rule_type = val
                mod = True

            if content.has_key('description'):
                val = content['description']
                if not isinstance(val, basestring):
                    raise Exception("Invalid description, expects string.")
                rule.description = val
                mod = True

            if content.has_key('comment'):
                val = content['comment']
                if not isinstance(val, basestring):
                    raise Exception("Invalid comment, expects string.")
                rule.comment = val
                mod = True

            if content.has_key('expiration'):
                val = content['expiration']
                if not (isinstance(val, float) or isinstance(val, int) or isinstance(val, long)):
                    raise Exception("Invalid expiration time, expects numeric value.")
                rule.expiration = float(val)
                mod = True

            if content.has_key('text'):
                if content.has_key('actions') or content.has_key('condition'):
                    raise Exception("Cannot modify rule with text AND condition/actions set.")

                d = self.policy.change_rule_definition(rule.global_id, content['text'], globals(), locals())
                mod = True
            elif content.has_key('condition'):
                if not content.has_key('actions'):
                    raise Exception("Cannot modify rule condition without including actions.")

                s = rule_string(content)
                d = self.policy.change_rule_definition(rule.global_id, s, globals(), locals())
                mod = True
            elif content.has_key('actions'):
                raise Exception("Cannot modify rule actions without including condition.")

            if not mod:
                raise Exception("No valid rule attributes to modify.")

            if d != None:
                return d

            if not self.policy.modify_metadata(rule.global_id):
                raise Exception("Could not modify rule ID %u's metadata." % rule.global_id)
            return defer.succeed(None)
        except Exception, e:
            return defer.fail(Failure())

    def delete_rule(self, request, data):
        try:
            d = self.policy.lock_policy()
            d.addCallback(self.__delete_rule__, request, data)
            d.addBoth(self.unlock_policy)
            d.addErrback(self.err, request, "delete_rule",
                         "Could not delete rule.")
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "delete_rule",
                            "Could not delete rule.")

    def __delete_rule__(self, tmp, request, data):
        id = data['<rule id>']
        if not self.policy.remove_rule(id):
            return webservice.badRequest(request, "Could not remove rule %u." % id)

        d = self.policy.apply(request.getSession().user.username)
        d.addCallback(self.write_policy_id, request)
        return d

    def post_rules(self, request, data):
        try:
            content = webservice.json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            d = self.policy.lock_policy()
            d.addCallback(self.__post_rules__, request, data, content)
            d.addBoth(self.unlock_policy)
            d.addErrback(self.err, request, "post_rules",
                         "Could not modify policy.")
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "post_rules",
                            "Could not modify policy.")

    def __post_rules__(self, tmp, request, data, content):
        if not content.has_key('policy_id'):
            return webservice.badRequest(request, 'Request must include policy id to update.')
        elif content['policy_id'] != self.policy.policy_id:
            return webservice.conflictError(request, 'Cannot apply changes to old policy id %u.' % content['policy_id'])

        if not content.has_key('rules'):
            return webservice.badRequest(request, 'Request must include array of new policy rules.')

        d = self.__categorize_rules__(content['rules'])
        d.addCallbacks(self.__post_rules2__, self.badReq, (request,), None, (request, "post_rules"))
        return d

    def __post_rules2__(self, rule_lists, request):
        for rule in rule_lists[1]:
            if not self.policy.remove_rule(rule.global_id):
                raise Exception('Could not remove rule ID %u.' % rule.global_id)

        for id, rule in rule_lists[2].iteritems():
            self.policy.rules[id].order = rule['order']

        d = self.policy.apply(request.getSession().user.username)
        d.addCallback(self.write_policy_id, request,)
        return d

    def put_analysis(self, request, data):
        try:
            content = webservice.json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            d = self.policy.lock_policy()
            d.addCallback(self.__put_analysis__, request, data, content)
            d.addBoth(self.unlock_policy)
            d.addErrback(self.err, request, "put_analysis",
                         "Could not analyze rules.")
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "put_analysis",
                            "Could not analyze rules.")
        
    def __put_analysis__(self, tmp, request, data, content):
        if not content.has_key('rules'):
            return webservice.badRequest(request, 'Request must include array of policy rules to analyze.')

        d = self.__categorize_rules__(request, content['rules'])
        d.addCallbacks(self.__put_analysis2__, self.badReq, (request,), None, (request, "put_analysis"))
        return d

    def __put_analysis2__(self, rule_lists, request):
        added = []
        for rule in self.policy.parsed_rules:
            jrule = to_json_rule(rule)
            analysis = self.policy.analyze_rule(rule)
            jrule['overlaps'] = analysis[1]
            added.append(jrule)

        result = { 'added' : added }
        result['removed'] = [ rule.global_id for rule in rule_lists[1] ]
        request.write(simplejson.dumps(result))
        request.finish()

    def __categorize_rules__(self, rules):
        try:
            g = globals()
            l = locals()
            j = 0
            self.policy.parse_rules(None, '', g, l, True, False)
            for rule in rules:
                if not rule.has_key('rule_id'):
                    if rule.has_key('text'):
                        s = rule['text']
                    elif rule.has_key('actions') and rule.has_key('condition'):
                        s = rule_string(rule)
                    else:
                        raise Exception("%s new rule does not specifiy text or condition/actions attributes." % compile.__ith__(j))
                    try:
                        self.policy.parse_rules(rule['priority'], s, g, l, False, False)
                    except Exception, e:
                        e.message = "Error while parsing %s new rule: %s" % (compile.__ith__(j), e.message)
                        return defer.fail(Failure())
                    j = j + 1
            d = self.policy.parse_rules(None, '', g, l, False, True)
            d.addCallback(self.__categorize_rules2__, rules)
            return d
        except Exception, e:
            return defer.fail(Failure())

    def __categorize_rules2__(self, tmp, rules):
        preserved_rules = {}
        added_rules = []
        j = 0
        for i in xrange(len(rules)):
            rule = rules[i]
            rule['order'] = i
            if rule.has_key('rule_id'):
                id = rule['rule_id']
                if not self.policy.rules.has_key(id):
                    raise Exception("Rule with ID %u does not exist." % id)
                preserved_rules[id] = rule
            else:
                if j >= len(self.policy.parsed_rules):
                    raise Exception("At least one rule was not correctly formatted as a python rule.")
                prule = self.policy.parsed_rules[j]
                prule.exception = rule['exception']
                prule.protected = rule['protected']
                prule.rule_type = rule['rule_type']
                prule.description = rule['description']
                prule.comment = rule['comment']
                prule.expiration = float(rule['expiration'])
                prule.order = rule['order']
                added_rules.append(rule)
                j = j + 1
            
        removed_rules = []
        for rule in self.policy.rules.itervalues():
            if not preserved_rules.has_key(rule.global_id):
                removed_rules.append(rule)

        return (added_rules, removed_rules, preserved_rules)
    
    def write_policy_id(self, ignore, request):
        request.write(simplejson.dumps({'policy_id' : self.policy.policy_id}))
        request.finish()

    def getInterface(self):
        return str(policyws)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return policyws(ctxt)

    return Factory()

class WSPathExistingPolicyId(webservice.WSPathComponent):
    def __init__(self, policy):
        webservice.WSPathComponent.__init__(self)
        self.policy = policy

    def __str__(self):
        return "<policy id>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI.")

        try:
            id = int(pc, 10)
        except ValueError:
            return webservice.WSPathExtractResult(error="Invalid non-integer policy id %s." % pc)

        if self.policy.is_locked():
            return webservice.WSPathExtractResult(error="Policy is currently being updated.")
        if id != self.policy.policy_id:
            return webservice.WSPathExtractResult(error="Policy id %s does not exist." % pc)
        return webservice.WSPathExtractResult(value=id)

class WSPathExistingRuleId(webservice.WSPathComponent):
    def __init__(self, policy):
        webservice.WSPathComponent.__init__(self)
        self.policy = policy

    def __str__(self):
        return "<rule id>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI.")

        try:
            id = int(pc, 10)
        except ValueError:
            return webservice.WSPathExtractResult(error="Invalid non-integer rule id %s." % pc)

        if not self.policy.rules.has_key(id):
            return webservice.WSPathExtractResult(error="Rule id %s does not exist." % pc)
        return webservice.WSPathExtractResult(value=id)

__params__ = { 'priority' : 1, 'condition' : 1, 'actions' : 1, 'text' : 1,
               'expiration' : 1, 'policy_id' : 1, 'user' : 1,
               'timestamp' : 1, 'exception' : 1, 'rule_type' : 1,
               'description' : 1, 'comment' : 1 , 'protected' : 1 }

class WSPathRuleParam(webservice.WSPathComponent):
    def __init__(self):
        webservice.WSPathComponent.__init__(self)
        
    def __str__(self):
        return "<param>"

    def extract(self, pc, data):
        global __params__

        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI.")

        if __params__.has_key(pc):
            return webservice.WSPathExtractResult(value=pc)
        return webservice.WSPathExtractResult(error="Invalid rule parameter \'%s\'." % pc)

def rule_string(jrule):
    actions = jrule['actions']
    if len(actions) > 1:
        rulestr = 'compose('
    else:
        rulestr = ''
    rulestr = rulestr + ', '.join([lit_string(a['type'], a['args']) for a in actions])
    if len(actions) > 1:
        rulestr = rulestr + ') <= ' + pred_string(jrule['condition'])
    else:
        rulestr = rulestr + ' <= ' + pred_string(jrule['condition'])

    return rulestr

def pred_string(jpred):
    pred = jpred['pred']
    if pred == 'not':
        return '~(' + pred_string(jpred['args'][0]) + ')'
    if pred == 'and':
        return ' ^ '.join([ ('(' + pred_string(p) + ')') for p in jpred['args']])
    if pred == 'or':
        return ' | '.join([ ('(' + pred_string(p) + ')') for p in jpred['args']])

    return lit_string(pred, jpred['args'])

def lit_string(t, args):
    if isinstance(t, bool):
        return str(t)

    return t + '(' + ', '.join([make_string(arg) for arg in args]) + ')'

def make_string(arg):
    return '\'' + arg + '\''

def to_json_rule(rule):
    json = { 'rule_id' : rule.global_id,
             'priority' : rule.priority,
             'text' : rule.ustr(),
             'exception' : rule.exception,
             'protected' : rule.protected,
             'rule_type' : rule.rule_type,
             'description' : rule.description,
             'comment' : rule.comment,
             'expiration' : rule.expiration,
             'policy_id' : rule.policy_id,
             'user' : rule.user,
             'timestamp' : rule.timestamp,
             'condition' : to_json_cond_wrap(rule.condition),
             'actions' : [ to_json_action(a) for a in rule.actions ] }
    return json

def to_json_cond_wrap(obj, parent_op=None):
    if isinstance(obj, bool):
        json = { 'pred' : obj,
                 'args' : [] }
        if parent_op == None:
            return json
        return [ json ]
    if isinstance(obj, PyComplexPred):
        return to_json_cond(obj, parent_op)
    return to_json_lit(obj, parent_op)

def to_json_cond(cond, parent_op=None):
    if cond.orp == None:
        json = to_json_cond_wrap(cond.lit)
    else:
        json = to_json_cond_wrap(cond.left, cond.orp)
        json.extend(to_json_cond_wrap(cond.right, cond.orp))
        if parent_op != None and parent_op == cond.orp and not cond.negate:
            return json

        if cond.orp:
            opname = 'or'
        else:
            opname = 'and'
        json = { 'pred' : opname,
                 'args' : json }

    if cond.negate:
        json = { 'pred' : 'not',
                 'args' : [ json ] }

    if parent_op == None:
        return json
    return [json]

def to_json_lit(lit, parent_op=None):
    pinfo = compile.pred_info(lit.pred) 
    if lit.pred == compile.EXPGROUP or pinfo[compile.TYPE_IDX] == compile.GROUP_T:
        args = list(lit.args)
        args[1] = compile.pred_info(args[1])[compile.STR_IDX].upper()
    else:
        args = lit.args


    json = { 'pred' : pinfo[compile.STR_IDX],
             'args' : args }

    if parent_op == None:
        return json
    return [ json ]

def to_json_action(action):
    ainfo = compile.action_info(action.type)

    json =  { 'type' : ainfo[compile.STR_IDX],
              'args' : action.args }
    return json

