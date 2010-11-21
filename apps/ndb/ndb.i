%module "nox.ext.apps.pyndb"

%{
#include "pyndb.cc"
%}

class PyNDB {
public:
    PyNDB(PyObject*);

    void configure(PyObject*);

    void install(PyObject*);

    PyObject* create_table(PyObject*);

    PyObject* drop_table(PyObject*);

    PyObject* execute(PyObject*);
};

%pythoncode
%{
    def getFactory():
        class Factory:
            def instance(self, context):
                from nox.ext.apps.ndb import API, PutOp, DependencyError, SchemaError
                from twisted.internet import defer
                from twisted.python import failure
    
                class NDB(API):
                    """
                    An adaptor over the C++ based Python bindings to
                    simplify their implementation.
                    """  
                    def __init__(self, ctxt):
                        self.ndb = PyNDB(ctxt)

                    def configure(self, configuration):
                        self.ndb.configure(configuration)

                    def install(self):
                        pass

                    def getInterface(self):
                        return str(API)
                        
                    def create_table(self, table, columns, indices=[]):
                        d = defer.Deferred()
        
                        def callback(result):
                            if result == 0:
                                d.callback(None)
                            else:
                                try:
                                    if result == 2:
                                        raise SchemaError("Schema definition error.")
                                    else:
                                        # General error
                                        raise Exception
                                except:
                                    print result # TODO
                                    d.errback(failure.Failure())
                                    
                        p = (table, columns, indices, callback)
                        self.ndb.create_table(p)
                        return d

                    def drop_table(self, table):
                        d = defer.Deferred()

                        def callback(result):
                            if result == 0:
                                d.callback(None)
                            else:
                                try:
                                    # General error
                                    raise Exception
                                except Exception, e:
                                    d.errback(failure.Failure())

                        p = (table, callback)
                        self.ndb.drop_table(p)
                        return d

                    def execute(self, ops, dependencies=[]):
                        d = defer.Deferred()
                        
                        p = filter(lambda op: isinstance(op, PutOp), ops)
                        type = ""
                        if len(p) == 0:
                            type = "get"
                        elif len(p) == len(ops):
                            type = "put"
                        else:
                            return defer.fail()

                        del p
                        cpp_ops = []
                        for op in ops:
                            cpp_ops.append(op.__dict__)
                            
                        cpp_dependencies = []
                        for dep in dependencies:
                            cpp_dependencies.append(dep.__dict__)

                        def callback(result):
                            if result == 0:
                                d.callback(ops)
                            else:
                                try:
                                    if result == 1:
                                        raise DependencyError("Dependency check failed.")
                                    elif result == 2:
                                        raise SchemaError("Schema definition error.")
                                    else:
                                        # General error
                                        raise Exception
                                except:
                                    d.errback(failure.Failure())
            
                        p = (type, cpp_ops, cpp_dependencies, callback)
                        self.ndb.execute(p)
                        return d

                return NDB(context)


        return Factory()
%}
