import logging

from nox.netapps.storage import Storage
from nox.netapps.storage import TransactionalStorage

from nox.lib.core import Component

from twisted.internet import defer

lg = logging.getLogger("policystore")

class PolicyStore(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.cur_policy_table = 'current_policy'
        self.rule_table = 'policy_rules'
        self.storage = None
        self.conn = None

    def install(self):
        self.storage = self.ctxt.resolve(str(TransactionalStorage))

        def conn_err(res):
            lg.error('Could not obtain storage connection: %s.' % res.value.message)
            return res

        def create_ok(res):
            pass

        # right now fails if table already exists...which not an
        # error...but code is wrong
        def create_err(res, tbl):
            if tbl == 1:
                lg.error('Could not create \'%s\' table: %s.' % (self.cur_policy_table, res.value.message))
            else:
                lg.error('Could not create \'%s\' table: %s.' % (self.rule_table, res.value.message))
            return res

        def create1(res):
            self.conn = res[1]
            d = self.conn.create_table(self.cur_policy_table,
                                       { 'id' : int,
                                         'user' : str,
                                         'timestamp' : float },
                                       (),
                                       0)
            d.addCallback(create2)
            d.addErrback(create_err, 1)
            return d

        def create2(res):
            d = self.conn.create_table(self.rule_table,
                                       { 'rule_id' : int,
                                         'priority' : int,
                                         'text' : str,
                                         'exception' : int,
                                         'protected' : int,
                                         'rule_type' : str,
                                         'description' : str,
                                         'comment' : str,
                                         'expiration' : float,
                                         'policy_order' : int,
                                         'policy_id' : int,
                                         'user' : str,
                                         'timestamp' : float },
                                       (('index_1', ('rule_id',)),),
                                       0)
            d.addCallback(create_ok)
            d.addErrback(create_err, 2)
            return d

        d = self.storage.get_connection()
        d.addCallbacks(create1, conn_err)
        return d

    def getInterface(self):
        return str(PolicyStore)

    def get_policy(self, res=None):
        d = self.conn.get(self.cur_policy_table, {})
        d.addCallback(self.get_one_row_cursor)
        return d

    def get_rule(self, rule_id):
        d = self.conn.get(self.rule_table, {'rule_id' : rule_id})
        d.addCallback(self.get_one_row_cursor)
        return d

    def get_one_row_cursor(self, res):
        cursor = res[1]
        d = cursor.get_next()
        d.addCallback(self.get_one_row, cursor)
        return d

    def get_one_row(self, res, cursor):
        if res[0][0] == Storage.NO_MORE_ROWS:
            row = None
        else:
            row = res[1]
        d = cursor.close()
        d.addCallback(self.return_row, row)
        return d

    def return_row(self, res, row):
        return row

    def get_rules(self, res=None):
        d = self.conn.get(self.rule_table, {})
        d.addCallback(self.get_rules_cursor)
        return d

    def get_rules_cursor(self, res):
        cursor = res[1]
        d = cursor.get_next()
        d.addCallback(self.get_rules_next, cursor, [])
        return d

    def get_rules_next(self, res, cursor, rules):
        if res[0][0] == Storage.NO_MORE_ROWS:
            d = cursor.close()
            d.addCallback(self.return_rules, rules)
            return d
        rules.append(res[1])
        d = cursor.get_next()
        d.addCallback(self.get_rules_next, cursor, rules)
        return d

    def return_rules(self, res, rules):
        return rules

    def delete_rules(self):
        d = self.get_rules()
        d.addCallback(self.got_rules)
        return d

    def got_rules(self, rules):
        return self.delete_rules2(None, rules)

    def delete_rules2(self, res, rules):
        if len(rules) == 0:
            return res
        rule = rules.pop()
        d = self.conn.remove(self.rule_table, rule)
        d.addCallback(self.delete_rules2, rules)
        return d

    def update(self, modified, policy_id, user, timestamp):
        d = None
        for mod in modified:
            if d == None:
                d = self.modify_rule(None, mod)
            else:
                d.addCallback(self.modify_rule, mod)

        if d == None:
            d = self.modify_policy(None, policy_id, user, timestamp)
        else:
            d.addCallback(self.modify_policy, policy_id, user, timestamp)
        return d

    def reset(self, rules, policy_id, user, timestamp):
        d = self.delete_rules()
        for rule in rules:
            d.addCallback(self.add_rule, rule)

        d.addCallback(self.modify_policy, policy_id, user, timestamp)
        return d

    def modify_policy(self, res, policy_id, user, timestamp):
        d = self.get_policy()
        d.addCallback(self.modify_policy2, policy_id, user, timestamp)
        return d

    def modify_policy2(self, row, policy_id, user, timestamp):
        if row == None:
            row = { 'id' : policy_id,
                    'user' : user,
                    'timestamp' : timestamp }
            d = self.conn.put(self.cur_policy_table, row)
            return d

        row['id'] = policy_id
        row['user'] = user
        row['timestamp'] = timestamp
        d = self.conn.modify(self.cur_policy_table, row)
        return d

    def modify_rule(self, res, rule):
        d = self.get_rule(rule.global_id)
        d.addCallback(self.modify_rule2, rule)
        return d

    def modify_rule2(self, row, rule):
        if row == None:
            return defer.fail(Exception('Row to modify does not exist'))

        row['priority'] = rule.priority
        row['text'] = rule.ustr()
        row['exception'] = rule.exception
        row['protected'] = rule.protected
        row['rule_type'] = rule.rule_type
        row['description'] = rule.description
        row['comment'] = rule.comment
        row['expiration'] = rule.expiration
        row['policy_order'] = rule.order
        row['policy_id'] = rule.policy_id
        row['user'] = rule.user
        row['timestamp'] = rule.timestamp

        d = self.conn.modify(self.rule_table, row)
        return d

    def add_rule(self, res, rule):
        row = {'rule_id' : rule.global_id,
               'priority' : rule.priority,
               'text' : rule.ustr(),
               'exception' : rule.exception,
               'protected' : rule.protected,
               'rule_type' : rule.rule_type,
               'description' : rule.description,
               'comment' : rule.comment,
               'expiration' : rule.expiration,
               'policy_order' : rule.order,
               'policy_id' : rule.policy_id,
               'user' : rule.user,
               'timestamp' : rule.timestamp }

        d = self.conn.put(self.rule_table, row)
        return d

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return PolicyStore(ctxt)

    return Factory()

