# Copyright 2008 (C) Nicira, Inc.
from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *
from nox.lib import config
from twisted.internet import defer
from twisted.web.resource import Resource
from twisted.web import server
from twisted.web.util import redirectTo
from twisted.python import log
from twisted.python.failure import Failure

from mako.template import Template
from mako.lookup import TemplateLookup
import os
import types
from nox.netapps.configuration.simple_config import simple_config
import logging
import simplejson
import hashlib
from OpenSSL.crypto import *
from nox.webapps.webservice import webservice
from twisted.internet import defer

lg = logging.getLogger('pki')

from nox.webapps.coreui.authui import UIResource
from nox.webapps.coreui import coreui

# this class uses the PROPERTIES table in CDB to hold on to cert data
# with in that table, it maintains two 'sections', one for pending certificate 
# requests and another for signed certificates that can be retrieved by switches
REQUEST_SEC_ID = "pki_cert_requests"
CERT_SEC_ID = "pki_certs"


# note: we keep a static number of POSTed certificates signing requests 
# less recent requests will be overwritten 
MAX_OUTSTANDING_REQS = 30

# this class does not actually have a present on the web page, but 
# allows external elements (e.g., switches) to perform POST and GET 
# operations to request and fetch signed certificates
class PKIResource(UIResource):
    isLeaf = True
    noUser = True

    def __init__(self, component):
        UIResource.__init__(self, component)
        self.last_req_num = 0 
        self.simple_config = component.resolve(simple_config)

    # note: there is no security issue with allowing anyone to fetch this
    # data, as it simply replies with certificates contain the (already) public key
    def render_GET(self, request):
          if "req" not in request.args: 
            webservice.badRequest(request, "POST did not include a 'req' argument")
            return webservice.NOT_DONE_YET

          fp = request.args["fp"][0]
          print "trying to retreive cert with fingerprint = '%s'"
         
          def err(res): 
            lg.error("Error looking for signed cert: %s" % str(res))
            webservice.internalError(request, "server error: %s" % str(res))

          def find_cert(cert_dict): 
            if fp in cert_dict: 
              request.write(cert_dict[fp])
              request.finish()
            else: 
              webservice.notFound(request, "No approved cert with fingerprint = '%s'" % fp)

          d = self.simple_config.get_config(CERT_SEC_ID)
          d.addCallbacks(get_slot,err)
          return webservice.NOT_DONE_YET

    def render_POST(self,request): 
        try:
          if "req" not in request.args: 
            webservice.badRequest(request, "POST did not include a 'req' argument")
            return webservice.NOT_DONE_YET
            
          req = request.args["req"][0]
          fp = hashlib.sha1(req).hexdigest()

          def err(res): 
            lg.error("error submitting pki sign req: %s" % str(res))
            webservice.internalError(request, "server error: %s" % str(res))
           
          def write_ok(res): 
            request.write(fp)
            request.finish()
         
          def find_slot_ok(slot_id): 
            data = [fp,req]
            d = self.simple_config.set_config(REQUEST_SEC_ID,{slot_id : data})
            d.addCallbacks(write_ok,err)
          
          d = self.find_next_slot()
          d.addCallbacks(find_slot_ok,err)
          return webservice.NOT_DONE_YET

        except Exception,e:
            lg.error("exception: " + str(e)) 
            webservice.badRequest(request, "failed to get CSR")
            return webservice.NOT_DONE_YET

    
    # finds an request slot in the properties that is 
    # not being used, or returns one to be replaced
    def find_next_slot(self): 
        def get_slot(dict):  
          i = self.last_req_num
          count = 0
          while (count <= MAX_OUTSTANDING_REQS): 
            count += 1
            i = (i + 1) % MAX_OUTSTANDING_REQS
            if str(i) not in dict: 
              break
          self.last_req_num = i
          return str(i) 
        d = self.simple_config.get_config(REQUEST_SEC_ID)
        d.addCallback(get_slot)
        return d


PRIVATE_KEY_TEXT = """-----BEGIN DSA PRIVATE KEY-----
MIIDPwIBAAKCAQEA0Y+7bvnaSpLsMUBp6lbjBCyz7+1MvMWnlXD9+MmLGPB5Ekd8
oa7QVA86riOfalR1xGnU11fnJJn18KKvevtyTJcInv9KfOVlAUgL5EeJV1AIL8QO
ZJlfy9VBySxMBmYnb9fRpB0+6V3psu76VX1qk0QWZ4JaRUrDJXqLviepl/hKi5yo
qtUTInd1bQ0GcUp1NGnvN7tIwwyCeusCmCJBqoMOBitz6S/mMZxZLmGt9LII5LkM
as1au9NLG90OTDF1d6X8+GQRXdNt75ybMTvWUC1mVz1aO8m7zLq/kfGHtS2FLnx8
P8KoMHRY49VHMHUIcoV2sG+ihVxZBSazxLpnIQIVAMsUBfN+h+vuZPwzv08ODKRm
+dvBAoIBAQCHfeQa0IG8ILSEnJ0bu4N8BDIz+Rk9ipdHl2F05Y9DLmbY/R6mkBVG
7XDxG+hJ341NXQ/4yhFqvgxp6cd0wLDjQ7O7HKAsyGgsyyM+DU9XITQWrlF7gqYv
4omkL88LufHVGuYMS6kKOogGZZpaVGn6bEglZ4I+B+v1zc/I6kwcskGCF7f5dSB0
X3zwIgraLodmiVSka6vzMkXLvO2IEaf1qIOfq9uZODtSSypR9RD+O9MAx1ZCLVU8
7eeUM5f2MFzBR3cHtYD/3TJpmp5oArOpBAczlfJ2hUfHs+Kucda02+3/lTQnrEbv
Ymr4Z6AG509a2joxzQ/su+zyHzBAeXJtAoIBAQC303dXXqmcMLRhjDpm+aHwy6mX
AyDTRppINbl8nxFXgqPlhp7gP/LF6tY8kQnFUskQya+KP17gCM69KxZ+Lrilc+Wk
13Tjhlf6+7un72OybceSOarU6OL4Vo0dskws4VCt6fQC92iwp823Y6gqsq7SOckp
QDFKAY+fp1/sCX5QF1qPJyYPLZhZrfc254Di5E8xCZcUoP/hR9NkOCNWlOKsUfdp
mc0kAAHBX4zhyyFCPkiTwH48w9uEsIcGTtt6LHGzzL5GMx8z8P8BORNB+lEFagWa
ys5eB/VXFZb2NNHL3lUU0UpyhQVIGg4j4X9sa4afOEicg8CEW1AOrjixYu4fAhQ3
99LXRYcaGbEmHSF23UiRwxW9Xg==
-----END DSA PRIVATE KEY-----
"""

CA_CERT = """
-----BEGIN CERTIFICATE-----
MIIEWDCCBBgCAQEwCQYHKoZIzjgEAzBTMQswCQYDVQQGEwJVUzELMAkGA1UECBMC
Q0ExETAPBgNVBAoTCE9wZW5GbG93MREwDwYDVQQLEwhPcGVuRmxvdzERMA8GA1UE
AxMIT3BlbkZsb3cwHhcNMDgwOTA5MjAwMTUwWhcNMTEwOTA5MjAwMTUwWjBTMQsw
CQYDVQQGEwJVUzELMAkGA1UECBMCQ0ExETAPBgNVBAoTCE9wZW5GbG93MREwDwYD
VQQLEwhPcGVuRmxvdzERMA8GA1UEAxMIT3BlbkZsb3cwggM8MIICLgYHKoZIzjgE
ATCCAiECggEBANGPu2752kqS7DFAaepW4wQss+/tTLzFp5Vw/fjJixjweRJHfKGu
0FQPOq4jn2pUdcRp1NdX5ySZ9fCir3r7ckyXCJ7/SnzlZQFIC+RHiVdQCC/EDmSZ
X8vVQcksTAZmJ2/X0aQdPuld6bLu+lV9apNEFmeCWkVKwyV6i74nqZf4SoucqKrV
EyJ3dW0NBnFKdTRp7ze7SMMMgnrrApgiQaqDDgYrc+kv5jGcWS5hrfSyCOS5DGrN
WrvTSxvdDkwxdXel/PhkEV3Tbe+cmzE71lAtZlc9WjvJu8y6v5Hxh7UthS58fD/C
qDB0WOPVRzB1CHKFdrBvooVcWQUms8S6ZyECFQDLFAXzfofr7mT8M79PDgykZvnb
wQKCAQEAh33kGtCBvCC0hJydG7uDfAQyM/kZPYqXR5dhdOWPQy5m2P0eppAVRu1w
8RvoSd+NTV0P+MoRar4MaenHdMCw40OzuxygLMhoLMsjPg1PVyE0Fq5Re4KmL+KJ
pC/PC7nx1RrmDEupCjqIBmWaWlRp+mxIJWeCPgfr9c3PyOpMHLJBghe3+XUgdF98
8CIK2i6HZolUpGur8zJFy7ztiBGn9aiDn6vbmTg7UksqUfUQ/jvTAMdWQi1VPO3n
lDOX9jBcwUd3B7WA/90yaZqeaAKzqQQHM5XydoVHx7PirnHWtNvt/5U0J6xG72Jq
+GegBudPWto6Mc0P7Lvs8h8wQHlybQOCAQYAAoIBAQC303dXXqmcMLRhjDpm+aHw
y6mXAyDTRppINbl8nxFXgqPlhp7gP/LF6tY8kQnFUskQya+KP17gCM69KxZ+Lril
c+Wk13Tjhlf6+7un72OybceSOarU6OL4Vo0dskws4VCt6fQC92iwp823Y6gqsq7S
OckpQDFKAY+fp1/sCX5QF1qPJyYPLZhZrfc254Di5E8xCZcUoP/hR9NkOCNWlOKs
Ufdpmc0kAAHBX4zhyyFCPkiTwH48w9uEsIcGTtt6LHGzzL5GMx8z8P8BORNB+lEF
agWays5eB/VXFZb2NNHL3lUU0UpyhQVIGg4j4X9sa4afOEicg8CEW1AOrjixYu4f
MAkGByqGSM44BAMDLwAwLAIUMQUPBUCekSED4zBZqhWUFGkA3fUCFBZ8Qdy3JK6I
wbHiHfVhXjt1XLXD
-----END CERTIFICATE-----
"""


CSR = """
-----BEGIN CERTIFICATE REQUEST-----
MIIEAzCCA8MCAQAwfTELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNBMRIwEAYDVQQH
EwlQYWxvIEFsdG8xETAPBgNVBAoTCE9wZW5GbG93MRswGQYDVQQLExJPcGVuRmxv
dyBjZXJ0aWZpZXIxHTAbBgNVBAMTFE9wZW5GbG93IGNlcnRpZmljYXRlMIIDOzCC
Ai4GByqGSM44BAEwggIhAoIBAQDRj7tu+dpKkuwxQGnqVuMELLPv7Uy8xaeVcP34
yYsY8HkSR3yhrtBUDzquI59qVHXEadTXV+ckmfXwoq96+3JMlwie/0p85WUBSAvk
R4lXUAgvxA5kmV/L1UHJLEwGZidv19GkHT7pXemy7vpVfWqTRBZnglpFSsMleou+
J6mX+EqLnKiq1RMid3VtDQZxSnU0ae83u0jDDIJ66wKYIkGqgw4GK3PpL+YxnFku
Ya30sgjkuQxqzVq700sb3Q5MMXV3pfz4ZBFd023vnJsxO9ZQLWZXPVo7ybvMur+R
8Ye1LYUufHw/wqgwdFjj1UcwdQhyhXawb6KFXFkFJrPEumchAhUAyxQF836H6+5k
/DO/Tw4MpGb528ECggEBAId95BrQgbwgtIScnRu7g3wEMjP5GT2Kl0eXYXTlj0Mu
Ztj9HqaQFUbtcPEb6EnfjU1dD/jKEWq+DGnpx3TAsONDs7scoCzIaCzLIz4NT1ch
NBauUXuCpi/iiaQvzwu58dUa5gxLqQo6iAZlmlpUafpsSCVngj4H6/XNz8jqTByy
QYIXt/l1IHRffPAiCtouh2aJVKRrq/MyRcu87YgRp/Wog5+r25k4O1JLKlH1EP47
0wDHVkItVTzt55Qzl/YwXMFHdwe1gP/dMmmanmgCs6kEBzOV8naFR8ez4q5x1rTb
7f+VNCesRu9iavhnoAbnT1raOjHND+y77PIfMEB5cm0DggEFAAKCAQBRWcNWWVkV
94E/9qvS+PRZ2kX+9/lhLOfa562LBZQMdsIPgeO8JBvcejh9+IajFLJUVv/VwznB
uBsrcJ3HDoyobNb36OtzRw3tJ851VnNAE5TYvTtU8PhqpSwhPJveGGPqRqiz7Bfb
x/y+nlkVlglC35KQGg53tT508Hos5RVLlGxB0GhdeINQA5pIgaXnmvqCJUARobwQ
AffxroISRmIShDP2QKpRvbExPiOXgUvGlcylyoA7EqiCUfZbFuk5pzqetcqvMHgD
fevajZEhAYuWJSBQ6NZicYmOciA1m4q06jAhv7lwuqBlODjuojCepdHmCKSThaU5
WYzH6WVc/hA2oAAwCQYHKoZIzjgEAwMvADAsAhRU6YUpwlg+ck5Izx+zW1G2HcSZ
LwIUPo56DieYKk0A4vy3C5FGO3DGq9I=
-----END CERTIFICATE REQUEST-----
"""

class pki(Component):
    
    def install(self):
        self.coreui = self.resolve(str(coreui.coreui))
        self.coreui.install_resource("/pki", PKIResource(self))
        self.simple_config = self.resolve(simple_config)
        self.priv_key = load_privatekey(FILETYPE_PEM, PRIVATE_KEY_TEXT) 

#        self.approveSwitch("5e0eb7e8f1c91be9a1612355cab930abdddfc1c4")

    def getInterface(self):
        return str(pki)

    def approveSwitch(self, cert_fp): 
        def find_cert(request_dict): 
          for (fp,csr) in request_dict.values(): 
            if(cert_fp == fp):
              ca_cert = load_certificate(FILETYPE_PEM,CA_CERT) 

              print "here's the csr '%s'" % csr
              req = load_certificate_request(FILETYPE_PEM,csr)
              cert = X509()
              cert.set_issuer(ca_cert.get_subject()) 
              cert.set_subject(req.get_subject())
              cert.set_pubkey(req.get_pubkey())
              cert.sign(self.priv_key,"md5")
              cert_text = dump_certificate(FILETYPE_PEM,cert)
              print "signed cert = '%s'" % cert_text
              d = self.simple_config.set_config(CERT_SEC_ID, {fp : [cert_text]})
              return d
          raise Exception("No cert request found with fp = %s" % cert_fp)

        d = self.simple_config.get_config(REQUEST_SEC_ID)
        d.addCallback(find_cert)
        return d


def getFactory():
    class Factory:
        def instance(self, ctxt):
            return pki(ctxt)

    return Factory()
