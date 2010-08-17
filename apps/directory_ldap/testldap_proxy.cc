#include "component.hh"

#include <boost/bind.hpp>

#include "vlog.hh"
#include "ldap_proxy.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace vigil::applications;

namespace {

static Vlog_module lg("testldap_proxy");

class Testldap_proxy
    : public Component {
public:
    Testldap_proxy(const Context* c,
                     const json_object*) 
        : Component(c) {
    }

    void configure(const Configuration*) {
        // Parse the configuration, register event handlers, and
        // resolve any dependencies.
        lg.dbg("testldap Configure called ");
        resolve(ldp);
    }

    void install() {
        // Start the component. For example, if any threads require
        // starting, do it now.
        lg.dbg("testldap Install called ");

        timeval dur_tv = {1, 0};
        for (int i = 0; i < LDAP_THREADS; ++i) {
            post(boost::bind(&Testldap_proxy::timer_cb, this), dur_tv);
        }
    }

    void timer_cb() {
        lg.dbg("**************************************************");
        lg.dbg("********Issuing scheduled auth request************");
        //ldp->simple_auth("casado", "casadoLdap!",
        //        boost::bind(&Testldap_proxy::auth_cb, this, _1));
        ldp->simple_auth("peter", "boguspassword",
                boost::bind(&Testldap_proxy::auth_cb, this, _1));
    }

    void auth_cb(const AuthResult& res) {
        lg.warn("Auth result for %s: %d (%s)",res.username.c_str(),
                res.status, res.status_str().c_str());
        lg.warn("  Nox Roles: %s", (res.nox_roles.empty() ? "<none>" : ""));
        for (Nox_role_list::const_iterator ci = res.nox_roles.begin();
                ci != res.nox_roles.end(); ++ci)
        {
            lg.warn("    %s", ci->c_str());
        }
        lg.warn("  Groups: %s",(res.groups.empty() ? "<none>" : ""));
        for (Groups_list::const_iterator ci = res.groups.begin();
                ci != res.groups.end(); ++ci)
        {
            lg.warn("    %s", ci->c_str());
        }
        //reschedule
        timeval dur_tv = {0, 0};
        sleep(2);
        post(boost::bind(&Testldap_proxy::timer_cb, this), dur_tv);
    }


private:
    Ldap_proxy *ldp;
    
};

REGISTER_COMPONENT(container::Simple_component_factory<Testldap_proxy>, 
                   Testldap_proxy);

} // unnamed namespace
