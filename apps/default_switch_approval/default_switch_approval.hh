#ifndef SWITCH_APPROVAL_HH_
#define SWITCH_APPROVAL_HH_

#include "component.hh"
#include "config.h"
#include <boost/bind.hpp>
#include <boost/function.hpp>
#include <boost/shared_ptr.hpp>
#include <map> 
#include <vector>
#include <string> 
#include "directory/directorymanager.hh"
#include "directory/principal_types.hh"
#include "openflow/openflow.h" 
#include "openflow.hh" 
#include "switch_auth.hh" 

namespace vigil {
namespace applications {

class DefaultSwitchApproval : public container::Component, public Switch_Auth {

  public:

    DefaultSwitchApproval(const container::Context* c, const json_object*)
        : container::Component(c), auto_approve(false) {
    }

    void configure(const container::Configuration*);

    void install() {}

    void check_switch_auth(std::auto_ptr<Openflow_connection> &oconn, 
       ofp_switch_features* features, Auth_callback cb); 

    void getInstance(const container::Context* ctxt, DefaultSwitchApproval*& h);

  private:

    // only used internally
    struct approval_req {
      approval_req(datapathid &dp, const std::string& fp, bool app, 
          const Switch_Auth::Auth_callback &cb): 
          dpid(dp), fingerprint(fp), is_approved(app), callback(cb) { } 
      datapathid dpid; 
      std::string fingerprint; 
      bool is_approved; 
      Switch_Auth::Auth_callback callback;
    }; 

    typedef boost::shared_ptr<approval_req> approval_req_ptr; 

    void SearchCallback(const std::vector<std::string>& name_list, 
                  approval_req_ptr req); 
    void GetCredCallback(std::string &switch_name, 
            const std::vector<directory::CertFingerprintCredential>& cred_list,
            approval_req_ptr req); 
    void AddSwitchCredential(std::string& switch_name, approval_req_ptr req); 
    void Done(approval_req_ptr req); 
    void ErrorBack(approval_req_ptr req); 
 
    bool auto_approve; 
    DirectoryManager *dirmanager;
};

}
} 
#endif
