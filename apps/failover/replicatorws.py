# Copyright 2008 (C) Nicira, Inc.
import os, logging, shutil, simplejson, time

from twisted.internet import reactor
from twisted.internet.defer import Deferred

#from nox.ext.apps.coreui.coreui import *
from nox.webapps.webservice.webservice import *
from nox.ext.apps.storage.transactional_storage import TransactionalStorage, TransactionalConnection
from nox.lib.core import Component

from pyreplicator import PyStorage_replicator

lg = logging.getLogger('replicator')

class Replicator(Component):
    """\
    Web service interface to request for a transactional storage
    snapshot, browse the existing snapshots, and restore one.
    """

    directory = "/var/log/snacdb"
    prefix = "snac.cdb"
    database = "testing.sqlite"

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.snapshots = {}

    def getInterface(self): return str(Replicator)

    def configure(self, configuration):
        for param in configuration['arguments']:
            if param.find('=') != -1:
                key, value = param[:param.find('=')], param[param.find('=')+1:]
            else:
                key, value = param, ''

            if key == 'database': self.database = value
            elif key == 'directory': self.directory = value
            elif key == 'prefix': self.prefix = value
            else:
                raise RuntimeError('Unsupported configuration option: ' + param)

        self.impl = PyStorage_replicator(self.ctxt)
        self.storage = self.ctxt.resolve(str(TransactionalStorage))

    def install(self):
        self.refresh()

        ws  = self.resolve(str(webservice))
        v1  = ws.get_version("1")
        reg = v1.register_request

        # /ws.v1/nox
        noxpath = ( WSPathStaticString("nox"), )

        # /ws.v1/nox/snapshot
        noxsnapshotpath = noxpath + ( WSPathStaticString("snapshot"), )

        reg(self.get_snapshots, "GET", noxsnapshotpath,
            """List existing NOX database snapshots""")
        reg(self.create_snapshot, "PUT", noxsnapshotpath,
            """Initiate the NOX database snapshot process""")

        # /ws.v1/nox/snapshot/delete
        noxsnapshotdel = noxsnapshotpath + ( WSPathStaticString("delete"), )
        reg(self.del_snapshot, "PUT", noxsnapshotdel,
            """Delete the current NOX database""")

        # /ws.v1/nox/snapshot/<id>
        noxsnapshotfilepath = noxpath + \
            ( WSPathStaticString("snapshot"), WSPathValidSnapshotID(self) )
        reg(self.restore_snapshot, "PUT", noxsnapshotfilepath,
            """Restore the NOX database snapshot file""")

    def get_snapshots(self, request, data):
        self.refresh()
        items = self.snapshots.items()
        items.sort((lambda x,y : cmp(x[1],y[1])))
        result = []
        for i in items:
            result.append({ 'timestamp': i[1], 'id': i[0] })
        
        request.write(simplejson.dumps(result))
        request.finish()

    def del_snapshot(self, request, data):
        self.refresh()

        try:
            shutil.copy(self.database, self.database + ".restore.backup")
            os.remove(self.database)
        except:
            request.setResponseCode(500)
            request.setHeader("Content-Type", "text/plain")
            request.write("Unable to backup or delete database".\
                              encode("utf-8"))
            request.finish()
            return
        
        request.write(simplejson.dumps(True))
        request.finish()
        lg.warn("Shutting down to create new database.")
        os._exit(1)

    def create_snapshot(self, request, data):
        new = "manual%d" % int(time.time())

        snapshot = self.directory + '/' + self.prefix + "." + new

        def complete(path, request, file, identifier):
            if path == "":
                request.setResponseCode(500)
                request.setHeader("Content-Type", "text/plain")
                request.write("Unable to create a snapshot".encode("utf-8"))
                request.finish()
            else:
                try:
                    self.refresh()
                    request.write(simplejson.dumps({
                                'timestamp': self.snapshots[identifier],
                                'id' : identifier
                                }))
                    request.finish()
                except:
                    request.setResponseCode(500)
                    request.setHeader("Content-Type", "text/plain")
                    request.write("Unable to access the snapshot".\
                                      encode("utf-8"))
                    request.finish()
                
        d = Deferred()
        d.addCallback(complete, request, snapshot, new)
        self.impl.snapshot(snapshot, False, d.callback)
        return NOT_DONE_YET

    def restore_snapshot(self, request, data):
        snapshot = self.directory + "/" + self.prefix + "." + \
            data['<snapshotid>']

        # Before restoring the database, lock it exclusively for us
        # first.
        self.connection = None

        def begin(r):
            result, self.connection = r
            return self.connection.begin(TransactionalConnection.EXCLUSIVE)

        def report(ignore, request):
            request.write(simplejson.dumps(True))
            request.finish()
            
            # Little delay to avoid unnecessary response truncated
            # error on the client-side

            def timeout(d): d.callback(None)

            d = Deferred()
            reactor.callLater(3, timeout, d)
            return d

        def execute(ignore, snapshot):
            # Before committing to the operation, check the files are
            # there by statting them.  If there's an error, an
            # exception will be thrown.
            get_file_timestamp(snapshot)
            get_file_timestamp(self.database)

            # Move the old file away, copy the new one and restart the
            # platform.
            shutil.move(self.database, self.database + ".restore.backup")
            shutil.copy2(snapshot, self.database)
            
            lg.warn("Shutting down to activate a snapshot.")
            os._exit(1)

        def abort(failure):
            try:
                failure.raiseException()
            except:
                lg.exception("Unable to restore a snapshot.")

            if self.connection:
                return self.connection.rollback()
        
        self.storage.get_connection().\
            addCallback(begin).\
            addCallback(report, request).\
            addCallback(execute, snapshot).\
            addErrback(abort)

        return NOT_DONE_YET

    def refresh(self):
        self.snapshots = {}
        for f in os.listdir(self.directory):
            if f.startswith(self.prefix) and (not f.endswith(".tmp")):
                try:
                    self.snapshots[f[len(self.prefix) + 1:]] = \
                        get_file_timestamp(self.directory + '/' + f)
                except:
                    pass

class WSPathValidSnapshotID(WSPathComponent):
    def __init__(self, replicator):
        WSPathComponent.__init__(self)
        self.replicator = replicator

    def __str__(self): return "<snapshotid>"

    def extract(self, pc, data):
        if pc == None:
            return WSPathExtractResult(error="End of requested URI")
        try:
            if self.replicator.snapshots.has_key(pc):
                return WSPathExtractResult(value=pc)
        except:
            pass
        return WSPathExtractResult(error="Invalid SnapshotID value '" + pc+"'.")

def get_file_timestamp(file): return os.stat(file)[8]

def getFactory():
    class Factory:
        def instance(self, ctxt): return Replicator(ctxt)

    return Factory()

__all__ = [ 'Replicator', 'getFactory' ]
