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

from nox.lib.core import *
from nox.webapps.webservice import webservice
from nox.ext.apps.configuration.simple_config import simple_config
import logging
import simplejson
import base64
from twisted.python.failure import Failure

lg = logging.getLogger('simple_configws')

class simple_configws(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.simple_config = None

    def err(self, failure, request, fn_name, msg):
        lg.error('%s: %s' % (fn_name, str(failure)))
        return webservice.internalError(request, msg)

    # special put method for files, which base 64 encodes 
    # each key value pair in the form.  This is often called
    # with a form that only contains a single field that is 
    # a file upload input. 
    # There is no corresponding 'GET' method for now, as
    # this method is mainly used for binary data like images
    # which are often rendered in the UI via a direct reference
    # to the resource.
    # NOTE: hacking this function to be able to get at the 
    # content-type and file name of individual parts of the 
    # multi-part message is a horrible hack.  twisted.web2 
    # has functions to do this for us, but aren't part of
    # standard twisted yet.  If someone knows a better way, 
    # please help!
    def post_config_base64(self,request, arg): 
        try:
            section_id = arg['<section>']
            content = {}
      
            boundary = None
            content_type = request.getHeader("Content-Type")
            for field in content_type.split("; "):
                arr = field.split("=")
                if arr[0] == "boundary": 
                    boundary = arr[1] 
                    break

            if not boundary: 
                lg.error("Could not find boundary in multipart request") 
                return webservice.badRequest(request, \
                                                 "Could not find boundary to parse multipart/form-data")
        
            if str(type(request.content)) == "<type 'cStringIO.StringO'>": 
                multipart_str = str(request.content.getvalue()).lower()
            elif isinstance(request.content,file): 
                multipart_str = request.content.read()
            else:
                lg.error("request.content has unknown type '%s'" % \
                             str(type(request.content)))
                return webservice.internalError(request,"Cannot handle request.content type.")

            multipart_arr = multipart_str.split(boundary)

            for key,value in request.args.iteritems():
                if key == "section_id":
                    continue  # TODO: figure out how to stop this in javascript
                content[key] = [ base64.b64encode(value[0])] 
                found = False
                for chunk in multipart_arr:
                    if chunk.find("name=\""+key+"\"") >= 0: 
                        start_index = chunk.find("content-type:")
                        end_index = chunk.find("\n",start_index)
                        content [key + "_content_type"] = \
                            chunk[start_index:end_index].split(" ")[1].strip()
                        start_index = chunk.find("filename=")
                        q1_index = chunk.find("\"", start_index)
                        q2_index = chunk.find("\"", q1_index + 1) 
                        content [key + "_filename"] =  chunk[(q1_index + 1):q2_index]
                        found = True
                        break
                if not found:
                    msg = "Could not find Content-Type in multipart/form-data for item %s" % key
                    lg.error("post_config_base64: %s" % msg)
                    return webservice.badRequest(request, msg)

            request.setHeader("Content-Type", "text/plain") 
            return self.set_config_common(request,section_id,content)
        
        except Exception, e:
            return self.err(Failure(), request, "post_config_base64", "Could not set key.")

    # main method for putting string->string key value pairs
    def put_config_from_request(self,request, arg): 
        try:
            section_id = arg['<section>']
            content = webservice.json_parse_message_body(request)
            if content == None:
                return webservice.badRequest(request, "Unable to parse message body.")
            return self.set_config_common(request,section_id,content)
        except Exception, e:
            return self.err(Failure(), request, "put_config_from_request",
                            "Could not set config.")

    # code shared by put_config and put_config_base64
    def set_config_common(self,request,section_id,content): 

        def finish_request(res):
          request.write(simplejson.dumps("success"))
          request.finish()
        
        if not content:
            request.write(simplejson.dumps("success"))
            request.finish()
            return webservice.NOT_DONE_YET
        
        d = self.simple_config.set_config(section_id,content)
        d.addCallback(finish_request)
        d.addErrback(self.err, request, "set_config_common",
                     "Could not set configuration.")
        return webservice.NOT_DONE_YET

    def get_config_from_request(self,request,arg):
        try:
            section_id = arg['<section>']
        
            def finish_request(res) :
                request.write(simplejson.dumps(res))
                request.finish()

            d = self.simple_config.get_config(section_id)
            d.addCallback(finish_request)
            d.addErrback(self.err, request, "get_config_from_request",
                         "Could not retrieve configuration.")
            return webservice.NOT_DONE_YET
        except Exception, e:
            return self.err(Failure(), request, "get_config_from_request",
                            "Could not retrieve configuration.")


    def install(self):
        self.simple_config = self.resolve(simple_config)

        ws  = self.resolve(webservice.webservice)
        v1  = ws.get_version("1")
        reg = v1.register_request

        configpath    = ( webservice.WSPathStaticString("config"), ) + \
                        (webservice.WSPathArbitraryString("<section>"), )
        
        #PUT /ws.v1/config/<section>
        reg(self.put_config_from_request, "PUT", configpath,
            """Write each supplied value to this section's configuration.""")
        
        #GET /ws.v1/config/<section>
        reg(self.get_config_from_request, "GET", configpath,
            """Get all stored values for this section.""")
        
        config64path = ( webservice.WSPathStaticString("config_base64"), ) + \
                        (webservice.WSPathArbitraryString("<section>"), )
        
        # POST /ws.v1/config_base64/<section/ 
        reg(self.post_config_base64, "POST", config64path, 
         """Base 64 encode, then write each value supplied for this section""")


    def getInterface(self):
        return str(simple_configws)


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return simple_configws(ctxt)

    return Factory()
