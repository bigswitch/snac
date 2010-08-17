import simplejson
import logging

from nox.webapps.webservice import webservice
from nox.ext.apps.sepl import compile
from nox.lib.directory import DirectoryException

from twisted.python.failure import Failure

lg = logging.getLogger('policyws')

def err(failure, request, fn_name, msg):
    lg.error('%s: %s' % (fn_name, str(failure)))
    if isinstance(failure.value, DirectoryException) \
            and (failure.value.code == DirectoryException.COMMUNICATION_ERROR \
                     or failure.value.code == DirectoryException.REMOTE_ERROR):
        msg = failure.value.message
    return webservice.internalError(request, msg)
    
def get_protocols(request, data):
    try:
        return simplejson.dumps([ to_json_protocol_obj(n, d) \
                                      for n, d in compile.__protos__.iteritems() ])
    except Exception, e:
        return err(Failure(), request, "get_protocols",
                   "Could not retrieve protocols.")

def get_protocol(request, data):
    try:
        name = data['<existing protocol>']
        return simplejson.dumps(to_json_protocol_obj(name, compile.__protos__[name]))
    except Exception, e:
        return err(Failure(), request, "get_protocol",
                   "Could not retrieve protocol.")

def __modify_protocol2__(tup, request, data):
    if tup == None:
        return
    name = data['<protocol>']
    compile.__protos__[name] = tup
    request.write(simplejson.dumps(to_json_protocol_obj(name, tup)))
    request.finish()

def modify_protocol(request, data):
    try:
        content = webservice.json_parse_message_body(request)
        if content == None:
            return webservice.badRequest(request, "Unable to parse message body.")

        d = to_protocol_tup(request, content)
        d.addCallback(__modify_protocol2__, request, data)
        d.addErrback(err, request, "modify_protocol",
                     "Could not modify protocol.")
        return webservice.NOT_DONE_YET
    except Exception, e:
        return err(Failure(), request, "modify_protocol",
                   "Could not modify protocol.")

def delete_protocol(request, data):
    try:
        del compile.__protos__[data['<existing protocol>']]
        return simplejson.dumps("Success")
    except Exception, e:
        return err(Failure(), request, "delete_protocol",
                   "Could not delete protocol.")

def to_json_protocol_obj(name, tup):
    return { 'name' : name,
             'dltype' : tup[0],
             'nwproto' : tup[1],
             'tport' : tup[2] }

def checked_proto(checked, request, tup):
    if checked == None:
        webservice.badRequest(request, "Invalid protocol defintion.")
        return None
    return tup

def to_protocol_tup(request, content):
    dltype = nwproto = tport = None
    if content.has_key('dltype'):
        dltype = content['dltype']
    if content.has_key('nwproto'):
        nwproto = content['nwproto']
    if content.has_key('tport'):
        tport = content['tport']
    tup = (dltype, nwproto, tport)
    d = compile.proto_check(tup)
    d.addCallback(checked_proto, request, tup)
    return d

class WSPathExistProtocolIdent(webservice.WSPathComponent):
    def __init__(self):
        webservice.WSPathComponent.__init__(self)

    def __str__(self):
        return "<existing protocol>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI.")

        if compile.__protos__.has_key(pc):
            return webservice.WSPathExtractResult(value=pc)
        return webservice.WSPathExtractResult(error='Protocol %s does not exist.' % pc)

class WSPathProtocolIdent(webservice.WSPathComponent):
    def __init__(self):
        webservice.WSPathComponent.__init__(self)

    def __str__(self):
        return "<protocol>"

    def extract(self, pc, data):
        if pc == None:
            return webservice.WSPathExtractResult(error="End of requested URI.")

        return webservice.WSPathExtractResult(value=pc)
