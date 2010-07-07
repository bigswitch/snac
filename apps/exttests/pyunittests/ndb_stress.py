from twisted.python import log

from nox.ext.apps.ndb import API, GetOp, PutOp
from nox.ext.apps.exttests import unittest

pyunit = __import__('unittest')

class NDBStressCase(unittest.NoxTestCase):
    """
    Testing NDB by adding and deleting 10,000 elements.  Verifies test
    by ensuring final select query for * returns 0 items
    """

    def configure(self, config):
        self.ndb = self.resolve(API)

    def getInterface(self):
        return str(NDBStressCase)    

    def setUp(self):
        """
        Deploy the schema.
        """
        return self.ndb.drop_table('TEST').\
            addCallback(lambda x : self.ndb.create_table('TEST', {'NAME': "", 
                                                                  'IP': 1}, 
                                                         []))
 
    def tearDown(self):
        pass

    def verifyDel(self,results):    
        query = {}

        def _verify(results):
            self.failUnlessEqual(len(results), 1, 'Too many results')
            results = results[0]
            self.failUnlessEqual(len(results.results), 0, 'Not empty?')

        op = GetOp('TEST', query)
        d = self.ndb.execute([ op ])
        d.addCallback(_verify)
        return d

    def delPuts(self, results):
        """
        Delete all put entries 
        """
        ops = []
        for i in range(0,10000):
            ops.append(PutOp('TEST', None, {'NAME' : str(i)}))

        d = self.ndb.execute(ops)
        d.addCallback(self.verifyDel)
        return d

    def testPutDel(self):
        """
        Write 10,000 entries 
        """
        ops = []
        for i in range(0,10000):
            ops.append(PutOp('TEST', {'NAME' : str(i), 'IP' : i}))

        d = self.ndb.execute(ops)
        d.addCallback(self.delPuts)
        return d

def suite(ctxt):
    suite = pyunit.TestSuite()
    suite.addTest(NDBStressCase("testPutDel", ctxt))
    return suite
