import random
import time
import compile
import logging
import difflib

from twisted.python.failure import Failure
from twisted.internet import defer

from nox.ext.apps.sepl.pyseplstats import PySeplStats
from nox.ext.apps.sepl.policystore import PolicyStore
from nox.netapps.authenticator.pyauth import PyAuth
from nox.netapps.authenticator.pyflowutil import PyFlowUtil

from nox.netapps.directory.directorymanager import directorymanager

from nox.lib.core import Component
from nox.lib.netinet import netinet
from nox.lib.netinet.netinet import create_cidr_ipaddr
from nox.coreapps.pyrt.pycomponent import CONTINUE
from nox.netapps.directory.pydirmanager import Directory, Principal_name_event, Group_name_event
from nox.netapps.configuration.simple_config import simple_config
from nox.netapps.user_event_log.pyuser_event_log import pyuser_event_log, LogEntry

lg = logging.getLogger("policy")

class PyPolicyComponent(Component):
    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

        self.authenticator = None
        self.sepl_enforcer = None
        self.nat_enforcer = None
        self.flow_util = None
        self.stats = None
        self.policystore = None
        self._dm = None
        self.init_policy = None
        self.simple_config = None
        self.uel = None

        self.user = None
        self.timestamp = None

        self.rules = {}
        self.priority = 0
        self.policy_id = random.randint(0, compile.U32_MAX)
        self.rid_counter = random.randint(0, compile.U32_MAX)
        self.rule_type = ''
        self.protected = False
        self.description = ''
        self.comment = ''

        self.locked = False

    def configure(self, configuration):
        self.init_policy = None
        arg_len = len(configuration['arguments'])
        if arg_len == 1:
            self.init_policy = configuration['arguments'][0]
        elif arg_len > 1:
            lg.error("Policy only accepts one param - the policy module name.")
            raise Exception('Policy only accepts one param - the policy module name.')
            
        self.authenticator = self.resolve(PyAuth)
        self.flow_util = self.resolve(PyFlowUtil)
        self.stats = self.resolve(PySeplStats)
        self.policystore = self.resolve(str(PolicyStore))
        self._dm = self.resolve(directorymanager)
        self.uel = self.resolve(pyuser_event_log)

        self.register_for_bootstrap_complete(self.bootstrapped)
        self.register_handler(Principal_name_event.static_get_name(),
                              self.__renamed_principal__)
        self.register_handler(Group_name_event.static_get_name(),
                              self.__renamed_group__)

        compile.__policy__ = self
    
    def install(self): 
        self.simple_config = self.resolve(simple_config) 
        defaults = { "internal_subnets" : [""] }
        d = self.simple_config.get_config("authenticator_config", 
            self.handle_config_update, defaults)
        d.addCallback(self.handle_config_update) # initial load
        return d

    def bootstrapped(self, event):
        if self.is_component_loaded("nat"):
            from nox.netapps.routing.pynatenforcer import PyNatEnforcer
            self.nat_enforcer = self.resolve(PyNatEnforcer)

        if self.is_component_loaded("sepl"):
            from nox.ext.apps.sepl.pyseplenforcer import PySeplEnforcer
            self.sepl_enforcer = self.resolve(PySeplEnforcer)

        d = None
        if self.init_policy is not None:
            d = self.read_policy_file(None, self.init_policy)
            d.addErrback(self.__read_failed__, True, self.init_policy)

        if self.policystore is not None:
            if d is None:
                d = self.load_cdb_policy()
            else:
                d.addErrback(self.load_cdb_policy)
            d.addErrback(self.__read_failed__, False)

        cur_policy = "nox.ext.apps.sepl.current_policy"
        if d is None:
            d = self.read_policy_file(None, cur_policy)
        else:
            d.addErrback(self.read_policy_file, cur_policy)
        d.addErrback(self.__read_failed__, True, cur_policy)
        d.addErrback(self.__no_policy__)

        return CONTINUE

    # this method is called whenever there is a change
    # to the authenticator configuration in CDB, and at
    # startup. 
    def handle_config_update(self,props): 
        if "internal_subnets" not in props: 
            lg.error("no 'internal_subnets' property found")
            return
        self.authenticator.clear_internal_subnets()
        arr = props["internal_subnets"][0].split(",")
        for prefix_str in arr:
            if prefix_str == "": 
                continue 
            if isinstance(prefix_str, unicode):
                prefix_str = prefix_str.encode('utf-8')
            prefix_str = prefix_str.strip()
            cidr = create_cidr_ipaddr(prefix_str)
            if cidr == None:
                lg.error("ignoring invalid prefix entry: '%s'" % prefix_str)
            else:
                self.authenticator.add_internal_subnet(cidr)

    def getInterface(self):
        return str(PyPolicyComponent)

    # Any attempts to modify the installed policy or parse rules
    # should "lock" the component first.  Returns a Deferred that will
    # callback with this policy object once the policy has been locked.

    def lock_policy(self, res=None):
        if self.locked:
            d = defer.Deferred()
            d.addCallback(self.lock_policy)
            self.waiter.chainDeferred(d)
            return d
        self.locked = True
        self.invalid_parse = False
        self.parsed_rules = []
        self.changes = []
        self.to_remove = []
        self.modified_meta = []
        self.waiter = defer.Deferred()
        return defer.succeed(self)

    # Unlocks a previously locked policy.

    def unlock_policy(self, res=None):
        if self.locked:
            self.locked = False
            self.waiter.callback(self)
        return res

    def is_locked(self):
        return self.locked

    # Priority setters.

    # Requires locking.

    def set_priority(self, pri):
        if not self.locked:
            return False
        if (isinstance(pri, int) or isinstance(pri, long)) and pri >= 0 and pri <= compile.U32_MAX:
            self.priority = int(pri)
            return True
        return False

    # Requires locking.

    def incr_priority(self):
        if not self.locked:
            return False
        if self.priority == compile.U32_MAX:
            return False
        self.priority = self.priority + 1
        return True

    # Requires locking.

    def decr_priority(self):
        if not self.locked:
            return False
        if self.priority <= 0:
            return False
        self.priority = self.priority - 1
        return True

    # Requires locking.

    def set_rule_type(self, rtype):
        if not self.locked:
            return False
        if isinstance(rtype, basestring):
            self.rule_type = rtype
            return True
        return False

    # Requires locking.

    def set_protected(self, protected):
        if not self.locked:
            return False
        if isinstance(protected, bool):
            self.protected = protected
            return True
        return False

    # Requires locking.

    def set_description(self, desc):
        if not self.locked:
            return False
        if isinstance(desc, basestring):
            self.description = desc
            return True
        return False

    # Requires locking.

    def set_comment(self, comment):
        if not self.locked:
            return False
        if isinstance(comment, basestring):
            self.comment = comment
            return True
        return False

    # Imports nox.ext.apps.sepl.current_policy

    def read_policy_file(self, tmp, file):
        d = self.lock_policy()
        d.addCallback(self.__import_policy_file__, file)
        d.addCallback(self.__apply_policy_file__)
        d.addBoth(self.unlock_policy)
        return d

    # Loads CDB policy

    def load_cdb_policy(self, res=None):
        d = self.lock_policy()
        old_pol = self.get_policy_list()
        d.addCallback(self.policystore.get_policy)
        d.addCallback(self.__get_rules__)
        d.addBoth(self.__db_load_done__, old_pol)
        return d

    # Queue the rules in 'policy_str' for addition.  'pri' is the
    # initial priority to use before evaluating the policy string
    # (which could be None if the string itself sets the priority, or
    # the policy component has already set the priority).  declare.py
    # should have been imported into namespace.  Returns a deferred
    # that will callback if the rules were successfully parsed and
    # will be installed on the next apply(), else will errback.
    # parse_rules should not be called again until d calls/errors back.

    # Requires locking.

    def parse_rules(self, pri, policy_str, globals, locals, clear, ret_deferred):
        if not self.locked:
            raise Exception('Policy component should be locked before parse.')

        if pri is not None:
            if not self.set_priority(pri):
                raise Exception("Could not set priority.")

        if clear:
            self.parse_deferreds = []

        if (policy_str != ''):
            try:
                eval(policy_str, globals, locals)
            except Exception, e:
                self.invalid_parse = True
                lg.error('Error while evaluating rule(s): %s' % e.message)
                raise

        if ret_deferred:
            d = defer.DeferredList(self.parse_deferreds, consumeErrors=True)
            self.parse_deferreds = []
            d.addCallback(self.__parse_complete__)
            return d
        return None

    # Queue a change of rule 'id's definition to the Python rule in
    # string 's'.  All of the rule's other attributes stay the same.
    # Returns a deferred.  Will callback if the policy is locked, 'id'
    # and 's' are valid, and the change will take place in the next
    # apply(), else will errback.

    # Requires locking.

    def change_rule_definition(self, id, s, globals, locals):
        if not self.locked:
            return defer.fail(Exception('Policy component should have been locked.'))

        if not (isinstance(id, int) or isinstance(id, long)):
            return defer.fail(Exception('ID is not an int or long.'))
        if not self.rules.has_key(id):
            return defer.fail(Exception('Rule ID %u does not exist.' % id))

        rule = self.rules[id]
        d = self.parse_rules(None, s, globals, locals, True, True)
        d.addCallback(self.__change_rule_parse_complete__, rule, s)
        return d

    # Queue a change of rule 'id's priority.  All of the rule's other
    # attributes stay the same.  Returns True if the policy is locked,
    # 'id' and 'pri' are valid, and the change will take place on the
    # next apply(), else returns False.

    # Requires locking.
    
    def change_rule_priority(self, id, pri):
        if not self.locked:
            return False

        if not (isinstance(id, int) or isinstance(id, long)):
            return False
        if not self.rules.has_key(id):
            return False
        if not (isinstance(pri, int) or isinstance(pri, long)) or pri < 0 or pri > compile.U32_MAX:
            return False

        rule = self.rules[id]
        for i in xrange(len(self.changes)):
            c = self.changes[i]
            if c[0] == rule and c[1] != rule.priority:
                self.changes.pop(i)
                break
        if rule.priority == pri:
            return True
        self.changes.append((rule, pri))
        return True

    # Queue a change of rule 'id's metadata.  Metadata should have
    # been directly changed by caller.  Returns True if the policy is
    # locked, 'id' is valid, and the change will take place on the
    # next apply, else returns False.

    # Requires locking.
    
    def modify_metadata(self, id):
        if not self.locked:
            return False
        if not (isinstance(id, int) or isinstance(id, long)):
            return False
        if not self.rules.has_key(id):
            return False

        self.modified_meta.append(self.rules[id])
        return True

    # Queue removal of rule 'id' from the policy.  Returns True if the
    # policy is locked, 'id' is valid, and the rule will be removed on
    # next apply(), else returns False.

    # Requires locking.

    def remove_rule(self, id):
        if not self.locked:
            return False
        if not (isinstance(id, int) or isinstance(id, long)):
            return False
        if not self.rules.has_key(id):
            return False

        rule = self.rules[id]
        if rule not in self.to_remove:
            self.to_remove.append(rule)
        return True

    # Queue all currently installed rules for removal.  Returns True
    # is the policy is locked and the rules will be removed on the
    # next apply(), else returns False.

    # Requires locking.

    def remove_all_rules(self):
        if not self.locked:
            return False

        self.to_remove = self.rules.values()
        return True

    # Apply queued changes to the installed policy.  Returns a
    # deferred that will callback if the changes were successfully
    # applied, else errbacks.

    # Requires locking.

    def apply(self, user='anonymous'):
        if not self.locked:
            return defer.fail(Exception('Policy component should have been locked.'))
        if self.invalid_parse == True:
            return defer.fail(Exception('Cannot apply invalid parse'))

        old_pol = self.get_policy_list()
        d = self.__apply_parsed__(user)
        d.addCallbacks(self.__update_succeed__, self.__update_fail__,
                       (old_pol,), None, (old_pol,))
        return d

    # Completely clear installed policy.  Returns a deferred that will
    # callback if the policy was successfully cleared, else errbacks.

    # Requires locking.

    def clear(self, user='anonymous'):
        if not self.locked:
            return defer.fail(Exception('Policy component should have been locked.'))

        old_pol = self.get_policy_list()
        self.policy_id = self.policy_id + 1
        self.timestamp = time.time()
        self.user = user

        if self.sepl_enforcer is not None:
            self.sepl_enforcer.reset()
        if self.nat_enforcer is not None:
            self.nat_enforcer.reset()
        self.rules = {}
        self.priority = 0
        self.rid_counter = random.randint(0, compile.U32_MAX)

        if self.policystore is None:
            return defer.succeed(None)

        d = self.policystore.reset([], self.policy_id, self.user, self.timestamp)
        d.addCallbacks(self.__update_succeed__, self.__update_fail__,
                       (old_pol,), None, (old_pol,))
        return d

    # Calling analyze on a rule returns a 2-tuple.  The first element
    # is True if the rule is valid, False if its literals conflict.
    # The 2nd is a list of rule ids whose domains could overlap with
    # the analyzed rule, ignoring priority and group definitions.

    # Analyze the pyrule 'rule'
    def analyze_rule(self, rule):
        if not isinstance(rule, compile.PyRule):
            return None

        overlappings = []
        for other in self.rules.itervalues():
            if rule.overlaps(other):
                overlappings.append(other.global_id)

        return (rule.verify(), overlappings)

    # Get the stats for the rule with ID 'id'.  Returns a dictionary
    # with 'count' set to the number of hits, 'record_senders' set to
    # True with the source MACs of the flows matching the rule have
    # been recorded (else False), and 'sender_macs' set to a list of
    # the macs if the senders are recorded.

    def get_rule_stats(self, id):
        if not (isinstance(id, int) or isinstance(id, long)):
            return None
        if not self.rules.has_key(id):
            return None

        rule = self.rules[id]
        if rule.ids is None:
            return None

        sender_macs = []

        stats_entry = self.stats.get_rule_stats(id)
        if stats_entry.record_senders:
            sender = stats_entry.sender_macs.begin()
            while sender != stats_entry.sender_macs.end():
                sender_macs.append(sender.value())
                sender.incr()
        return { 'count' : stats_entry.count,
                 'record_senders' : stats_entry.record_senders,
                 'sender_macs' : sender_macs }

    # Configure source MACs of the flows matching rule with ID 'id' to
    # either be recorded ('record'=True) or not ('record'=False).

    def set_record_rule_senders(self, id, record):
        if not (isinstance(id, int) or isinstance(id, long)):
            return False
        if not self.rules.has_key(id):
            return False

        rule = self.rules[id]
        if rule.ids is None:
            return False

        self.stats.set_record_rule_senders(id, record)
        return True        

    # Get the number of flows that have been allowed

    def get_allows(self):
        return self.stats.get_allows()

    # Get the number of flows that have been dropped

    def get_denies(self):
        return self.stats.get_denies()

    # Log the current policy

    def log_policy(self, old_pol):
        if self.user is not None:
            if isinstance(self.user, unicode):
                suser = self.user.encode('utf-8')
            else:
                suser = self.user

            self.uel.log("policy", LogEntry.INFO,
                         "Policy modified by {su}.", su=suser)

        if len(self.rules) == 0:
            lg.error(" Empty policy.")
            return

        new_pol = self.get_policy_list()
        g = difflib.ndiff(old_pol, new_pol)
        ordered = self.rules.values()
        ordered.sort(None, compile.PyRule.get_order)
        oidx = 0
        ridx = 0
        for r in g:
            if r[0] == '?':
                continue
            elif r[0] == '-':
                suffix = ''
            else:
                rule = ordered[ridx]
                suffix = ' ' + str(rule.global_id)+': ' + str([id[0] for id in rule.ids]) + ' ' + str(rule.order)
                ridx = ridx + 1

            lg.error('  '+r+suffix)
            if isinstance(r, unicode):
                sr = r.encode('utf-8')
            else:
                sr = r
            self.uel.log("policy", LogEntry.INFO, sr)
            
    def get_policy_list(self):
        pol = []
        ordered = self.rules.values()
        ordered.sort(None, compile.PyRule.get_order)
        for rule in ordered:
            pol.append(rule.ustr())
        return pol
        
    def __add_rule_deferred__(self, deferred):
        self.parse_deferreds.append(deferred)

    def __apply_change__(self, r, pri):
        c = (r, r.priority)
        if r.priority != pri and c not in self.changes:
            r.change_priority(pri)
        else:
            if r.priority != pri:
                self.changes.remove(c)
                r.priority = pri
            r.decrement_ids()
            remove_ids = r.ids
            r.actions = r.new_actions
            r.condition = r.new_condition
            r.dnf = r.new_dnf
            r.translate()
            r.install(self.sepl_enforcer, self.nat_enforcer)
            if remove_ids is not None:
                r.remove(remove_ids)

        self.modified_meta.append(r)

    def __apply_policy_file__(self, tmp):
        return self.apply()

    def __apply_parsed__(self, user):
        self.policy_id = self.policy_id + 1
        self.timestamp = time.time()
        self.user = user

        pri = None
        if len(self.changes) > 0:
            self.changes.sort(None, self.__pri_change_key__)
            (r, pri) = self.changes.pop(0)

        self.parsed_rules.sort(None, compile.PyRule.get_priority)
        for rule in self.parsed_rules:
            rule.translate()
        for rule in self.parsed_rules:
            while pri is not None and pri <= rule.priority:
                self.__apply_change__(r, pri)
                if len(self.changes) > 0:
                    (r, pri) = self.changes.pop(0)
                else:
                    pri = None

            self.__assign_id__(rule)
            rule.install(self.sepl_enforcer, self.nat_enforcer)

        while pri is not None:
            self.__apply_change__(r, pri)
            if len(self.changes) > 0:
                (r, pri) = self.changes.pop(0)
            else:
                pri = None

        self.to_remove.sort(None, compile.PyRule.get_priority, True)
        for rule in self.to_remove:
            rule.remove()
            rule.decrement_ids()
            self.stats.remove_entry(rule.global_id)
            del self.rules[rule.global_id]

        for rule in self.modified_meta:
            self.__set_rule__(rule)

        for rule in self.parsed_rules:
            self.__set_rule__(rule)

        self.__set_rule_order__()

        if self.sepl_enforcer is not None:
            self.sepl_enforcer.build()
        if self.nat_enforcer is not None:
            self.nat_enforcer.build()
        if self.policystore is None:
            return defer.succeed(None)

        return self.policystore.reset(self.rules.values(), self.policy_id, self.user, self.timestamp)

    def __assign_id__(self, rule):
        loop = self.rid_counter

        while True:
            found = False
            if not self.rules.has_key(self.rid_counter):
                rule.global_id = self.rid_counter
                self.rules[rule.global_id] = rule
                found = True
            if self.rid_counter == compile.U32_MAX:
                self.rid_counter = 0
            else:
                self.rid_counter = self.rid_counter + 1
            if found:
                return
            elif loop == self.rid_counter:
                raise Exception('Rule ID space exhausted')

    def __change_rule_parse_complete__(self, tmp, rule, s):
        if self.invalid_parse:
            if isinstance(s, unicode):
                raise Exception("Invalid rule string: %s" % s.encode('utf-8'))
            else:
                raise Exception("Invalid rule string: %s" % s)
        new = self.parsed_rules.pop()
        rule.new_actions = new.actions
        rule.new_condition = new.condition
        rule.new_dnf = new.dnf
        c = (rule, rule.priority)
        if c not in self.changes:
            self.changes.append(c)

    def __db_load_done__(self, res, old_pol):
        lg.error(" CDB loaded policy:")
        self.log_policy(old_pol)
        self.unlock_policy()
        return res

    def __dbrule_parse_complete__(self, tmp, rules):
        i = 0
        for rule in rules:
            prule = self.parsed_rules[i]
            prule.global_id = rule['rule_id']
            if rule['exception']:
                prule.exception = True
            else:
                prule.exception = False
            if rule['protected']:
                prule.protected = True
            else:
                prule.protected = False
            prule.rule_type = rule['rule_type']
            prule.description = rule['description']
            prule.comment = rule['comment']
            prule.expiration = rule['expiration']
            prule.order = rule['policy_order']
            prule.policy_id = rule['policy_id']
            prule.user = rule['user']
            prule.timestamp = rule['timestamp']
            prule.translate()
            i = i + 1

        self.parsed_rules.sort(None, compile.PyRule.get_priority)
        for rule in self.parsed_rules:
            rule.install(self.sepl_enforcer, self.nat_enforcer)
            self.rules[rule.global_id] = rule
        if self.sepl_enforcer is not None:
            self.sepl_enforcer.build()
        if self.nat_enforcer is not None:
            self.nat_enforcer.build()

    def __get_rules__(self, policy_row):
        if policy_row is None:
            return defer.fail(Exception('CDB policy has not be defined.'))
        self.policy_id = policy_row['id']
        self.user = policy_row['user']
        self.timestamp = policy_row['timestamp']
        d = self.policystore.get_rules()
        d.addCallback(self.__got_rules__)
        return d

    def __got_rules__(self, rules):
        from declare import *
        g = globals()
        l = locals()
        d = defer.succeed(None)
        for i in xrange(len(rules)):
            rule = rules[i]
            try:
                d = self.parse_rules(rule['priority'], rule['text'], g, l, i == 0, i == (len(rules)-1))
            except Exception, e:
                lg.error("Error while parsing %s rule: %s." % (compile.__ith__(i), e.message))
                raise
        d.addCallback(self.__dbrule_parse_complete__, rules)
        return d

    def __import_policy_file__(self, tmp, file):
        self.parse_deferreds = []

        self.remove_all_rules()
        __import__(file)

        d = defer.DeferredList(self.parse_deferreds, consumeErrors=True)
        d.addCallback(self.__parse_complete__)
        return d

    def __no_policy__(self, res):
        lg.error("No valid policies at config time - no policy installed.")

    def __parse_complete__(self, reslist):
        idx = 0
        for res in reslist:
            if res[0] == defer.FAILURE:
                self.invalid_parse = True
                raise Exception('Error while evaluating rule %u: %s' % (idx, res[1].value.message))
            elif isinstance(res[1], compile.PyRule):
                self.parsed_rules.append(res[1])
                idx = idx + 1

    def __pri_change_key__(self, tup):
        return tup[1]

    def __read_failed__(self, res, isCurrent, file=None):
        if isCurrent:
            lg.error("Could not import policy module '%s': %s" % (file, res.value.message))
        else:
            lg.error("Failure when reading CDB policy: %s" % res.value.message)
        lg.error(res)
        return res

    def __renamed__(self, tmp, t, old_name, new_name, subtype):
        if not isinstance(old_name, unicode):
            old_name = unicode(old_name, 'utf-8')
        if not isinstance(new_name, unicode):
            new_name = unicode(new_name, 'utf-8')
        for rule in self.rules.itervalues():
            ret = False
            if rule.condition.renamed(t, old_name, new_name, subtype):
                ret = True
            for act in rule.actions:
                if act.renamed(t, old_name, new_name, subtype):
                    ret = True
            if ret:
                if new_name == "":
                    self.to_remove.append(rule)
                else:
                    self.modified_meta.append(rule)

        if len(self.to_remove) > 0 or len(self.modified_meta) > 0:
            return self.apply('name-admin')
        else:
            return defer.succeed(None)

    def __renamed_group__(self, event):
        if event.type == Directory.SWITCH_PRINCIPAL_GROUP:
            t = compile.SW_T
        elif event.type == Directory.LOCATION_PRINCIPAL_GROUP:
            t = compile.LOC_T
        elif event.type == Directory.HOST_PRINCIPAL_GROUP:
            t = compile.HOST_T
        elif event.type == Directory.USER_PRINCIPAL_GROUP:
            t = compile.USER_T
        else:
            return CONTINUE

        d = self.lock_policy()
        d.addCallback(self.__renamed__, compile.GROUP_T, event.oldname, event.newname, t)
        d.addBoth(self.unlock_policy)
        return CONTINUE

    def __renamed_principal__(self, event):
        if event.type == Directory.LOCATION_PRINCIPAL:
            t = compile.LOC_T
        elif event.type == Directory.HOST_PRINCIPAL:
            t = compile.HOST_T
        elif event.type == Directory.USER_PRINCIPAL:
            t = compile.USER_T
        else:
            return CONTINUE

        d = self.lock_policy()
        d.addCallback(self.__renamed__, t, event.oldname, event.newname, None)
        d.addBoth(self.unlock_policy)
        return CONTINUE

    def __set_rule__(self, rule):
        rule.policy_id = self.policy_id
        rule.timestamp = self.timestamp
        rule.user = self.user

    def __set_rule_order__(self):
        if len(self.rules) == 0:
            return

        order = self.rules.values()
        order.sort(None, compile.PyRule.get_order)
        popped = []

        while len(order) > 0 and order[0].order is None:
            r = order.pop(0)
            popped.append(r)
        popped.sort(None, compile.PyRule.get_priority)
        order.extend(popped)

        i = 0
        for rule in order:
            rule.order = i
            i = i + 1

    def __update_succeed__(self, res, old_pol):
        lg.error(" Updated policy:")
        self.log_policy(old_pol)
        return res

    def __update_fail__(self, res, old_pol):
        # any damage control?
        if res is not None:
            if isinstance(res, Failure):
                lg.error("Updated failed: %s" % res.value.message)
            else:
                lg.error("Updated failed: %s" % str(res))
        lg.error(" Current policy:")
        self.log_policy(old_pol)
        return res

    # Return the installed rules as a newline-separated string
    def __str__(self):
        return '\n'.join([rule.ustr() + ' ' + str(rule.global_id)+': '+\
                              str([id[0] for id in rule.ids]) for rule in self.rules.itervalues()])

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return PyPolicyComponent(ctxt)

    return Factory()
