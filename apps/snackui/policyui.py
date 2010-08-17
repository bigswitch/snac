from nox.coreapps.pyrt.pycomponent import *
from nox.lib.core import *

from nox.webapps.coreui.authui import UISection, UIResource, Capabilities
from nox.webapps.coreui.authui import redirect

from nox.netapps.user_event_log.UI_user_event_log import UI_user_event_log

from nox.webapps.coreui import coreui

from twisted.web import server
from nox.lib.netinet.netinet import create_datapathid_from_host, \
    create_eaddr, create_ipaddr, c_ntohl

class QuickSetupRes(UIResource):
    required_capabilities = set([ "viewpolicy" ])

    def render_GET(self, request):
        return self.render_tmpl(request, "quicksetup.mako")

class RulesRes(UIResource):
    required_capabilities = set([ "viewpolicy" ])

    def render_GET(self, request):
        return self.render_tmpl(request, "rules.mako")

class HostAuthRes(UIResource):
    required_capabilities = set([ "viewpolicy" ])

    def render_GET(self, request):
        return self.render_tmpl(request, "hostauth.mako")

class UserAuthRes(UIResource):
    required_capabilities = set([ "viewpolicy" ])

    def render_GET(self, request):
        return self.render_tmpl(request, "userauth.mako")

class PolicySec(UISection):
    isLeaf = False
    required_capabilities = set([ "viewpolicy" ])

    def __init__(self, component):
        UISection.__init__(self, component, "Policy", "policyButtonIcon")
        self.putChild("QuickSetup", QuickSetupRes(self.component))
        self.putChild("Rules", RulesRes(self.component))
        self.putChild("HostAuthRules", HostAuthRes(self.component))
        self.putChild("UserAuthRules", UserAuthRes(self.component))

    def render_GET(self, request):
        return redirect(request, request.childLink('Rules?view=auth'))

from nox.ext.apps import sepl
from nox.ext.apps.sepl import compile
from nox.ext.apps.sepl.declare import *

class policyui(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)
        self.coreui = None

    def install(self):
        Capabilities.register("viewpolicy", "View policy configuration.",
                              ["Policy Administrator",
                               "Network Operator",
                               "Security Operator",
                               "Viewer"])
        self.coreui = self.resolve(str(coreui.coreui))
        self.coreui.install_section(PolicySec(self))
        
        self.coreui.install_section(PolicyDebugSec(self), True) # always hidden

    def getInterface(self):
        return str(policyui)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return policyui(ctxt)

    return Factory()

class PolicyDebugSec(UISection): 
    isLeaf = True

    def __init__(self, component):
        UISection.__init__(self, component, "PolicyDebug")
        self.policy = component.resolve(str(sepl.policy.PyPolicyComponent))
        self.dpsrc = self.inport = self.dlsrc = self.dldst = self.nwsrc = self.nwdst = ''
        self.args = ['nwdst', 'dldst', 'nwsrc', 'dlsrc', 'inport', 'dpsrc']

    def render_GET(self, request):
        reset = False
        for a in request.args:
            if a in self.args:
                if not reset:
                    self.dpsrc = self.inport = self.dlsrc = self.dldst = self.nwsrc = self.nwdst = ''
                    reset = True
                setattr(self, a, request.args[a][-1])
        
        mako_args = { 'dpsrc' : self.dpsrc, 'inport' : self.inport,
                      'dlsrc' : self.dlsrc, 'dldst' : self.dldst,
                      'nwsrc' : self.nwsrc, 'nwdst' : self.nwdst }

        retrieve = False
        for v in mako_args.values():
            if v != '':
                retrieve = True
                break

        mako_args['policy'] = self.policy
        mako_args['names'] = None

        if not retrieve:
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        try:
            if self.dpsrc == '':
                dpsrc = create_datapathid_from_host(0)
            else:
                dpsrc = create_datapathid_from_host(long(self.dpsrc))
            if dpsrc == None:
                mako_args["name_err"] = "Invalid dpsrc."
                return self.render_tmpl(request, "policydebug.mako", args=mako_args)
        except ValueError, e:
            mako_args["name_err"] = "Invalid dpsrc."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        try:
            if self.inport != '':
                inport = int(self.inport)
            else:
                inport = 0
        except ValueError, e:
            mako_args["name_err"] = "Invalid inport."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        if self.dlsrc == '':
            dlsrc = create_eaddr(0)
        else:
            dlsrc = create_eaddr(self.dlsrc)
        if dlsrc == None:
            mako_args["name_err"] = "Invalid dlsrc."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        if self.dldst == '':
            dldst = create_eaddr(0)
        else:
            dldst = create_eaddr(self.dldst)
        if dldst == None:
            mako_args["name_err"] = "Invalid dldst."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        if self.nwsrc == '':
            nwsrc = create_ipaddr(0)
        else: 
            nwsrc = create_ipaddr(self.nwsrc)
        if nwsrc == None:
            mako_args["name_err"] = "Invalid nwsrc."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        if self.nwdst == '':
            nwdst = create_ipaddr(0)
        else:
            nwdst = create_ipaddr(self.nwdst)
        if nwdst == None:
            mako_args["name_err"] = "Invalid nwdst."
            return self.render_tmpl(request, "policydebug.mako", args=mako_args)

        def cb(names):
            mako_args['names'] = names
            request.write(self.render_tmpl(request, "policydebug.mako", args=mako_args))
            request.finish()
        self.policy.authenticator.get_names(dpsrc, inport, dlsrc, c_ntohl(nwsrc.addr), dldst,
                                            c_ntohl(nwdst.addr), cb)
        return server.NOT_DONE_YET
