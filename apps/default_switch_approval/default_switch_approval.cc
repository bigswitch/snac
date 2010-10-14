/* Copyright 2008 (C) Nicira, Inc. */
#include "vlog.hh"
#include "default_switch_approval.hh"
#include "openflow.hh" 
#include <vector> 
#include "directory/directory.hh" 
#include <boost/shared_ptr.hpp> 
#include "netinet++/datapathid.hh" 

using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace vigil::applications;


static Vlog_module lg("switch_approval");
  

void DefaultSwitchApproval::configure(const container::Configuration* conf) {
      Component_argument_list clist = conf->get_arguments(); 
      Component_argument_list::const_iterator cit = clist.begin();
      while(cit != clist.end()){
        if(*cit == "auto_approve") 
          auto_approve = true; 
        ++cit;
      }
      register_switch_auth(this); 
      resolve(dirmanager); 
}

void DefaultSwitchApproval::check_switch_auth(
                std::auto_ptr<Openflow_connection> &oconn, 
                ofp_switch_features* features, Auth_callback cb) {
  
  datapathid dpid = datapathid::from_net(features->datapath_id); 
  approval_req_ptr req = approval_req_ptr(new approval_req(dpid,"",false,cb)); 
  Openflow_connection::Connection_type type = oconn->get_conn_type(); 
  
  if (auto_approve){ 
    lg.err("Auto-approving switch: %s \n",dpid.string().c_str());  
    req->is_approved = true;
  } 
 
  if (type == Openflow_connection::TYPE_SSL){ 
    req->fingerprint = oconn->get_ssl_fingerprint(); 
  } 

  directory::SwitchInfo sinfo; 
  sinfo.dpid = req->dpid; 
  DirectoryManager::KeySet set_params; 
  set_params.insert("dpid"); // indicate that this query uses 'dpid' 

  dirmanager->search_switches(sinfo,set_params,"",
      boost::bind(&DefaultSwitchApproval::SearchCallback,this,_1,req),
      boost::bind(&DefaultSwitchApproval::ErrorBack,this,req));  
                  
} 

void DefaultSwitchApproval::ErrorBack(approval_req_ptr req) { 
    lg.err("Error checking authentication of switch dpid = %s. \n",
          req->dpid.string().c_str());   
    Done(req); 
}

// Add a credential for this switch 
// This is called in two cases:
// 1) If we have no name for the switch, we first add it to discovered
//    directory, then add a credential.
// 2) If we already have a name for the switch, but it has no approved
//    credentials, we delete all old credentials and add a new one.  
void DefaultSwitchApproval::AddSwitchCredential(string& switch_name, 
                                          approval_req_ptr req) { 
    directory::CertFingerprintCredential cred;
    cred.fingerprint = req->fingerprint; 
    cred.is_approved = req->is_approved; // false, unless auto-approved
    dirmanager->put_certfp_credential(Directory::SWITCH_PRINCIPAL, 
                                      switch_name, cred,   
        boost::bind(&DefaultSwitchApproval::Done,this,req),
        boost::bind(&DefaultSwitchApproval::ErrorBack,this,req));  
}

void DefaultSwitchApproval::SearchCallback( 
                  const std::vector<std::string>& name_list, 
                  approval_req_ptr req) { 
    
  if(name_list.size() == 0) {
    // Unknown switch, add to directory 
    string switch_name = dirmanager->add_discovered_switch(req->dpid);
    this->AddSwitchCredential(switch_name, req);  
    return; 
  } 
  if(name_list.size() > 1) { 
    lg.err("Got multiple switch names for dpid = '%s', using first one\n",
            req->dpid.string().c_str());
  } 
  string mangled_name = name_list.front(); 
  
  dirmanager->get_certfp_credential(Directory::SWITCH_PRINCIPAL,mangled_name,
      boost::bind(&DefaultSwitchApproval::GetCredCallback,this,mangled_name,_1,req),
      boost::bind(&DefaultSwitchApproval::ErrorBack,this,req));  
  
} 


void DefaultSwitchApproval::GetCredCallback(string & switch_name, 
                  const vector<directory::CertFingerprintCredential>& cred_list,
                  approval_req_ptr req) { 
  bool found_approved_cred = false; 
  for(int i = 0; i < cred_list.size(); i++) { 
    if(!cred_list[i].is_approved)
        continue; 
    found_approved_cred = true; 
    if(cred_list[i].fingerprint == req->fingerprint){ 
      req->is_approved = true; 
      break; 
    } 
  }
  if(!found_approved_cred) 
    this->AddSwitchCredential(switch_name, req);  
  else 
    Done(req); 
} 

void DefaultSwitchApproval::Done(approval_req_ptr req) { 
  post(boost::bind(req->callback,req->is_approved)); 
} 



void
DefaultSwitchApproval::getInstance(const container::Context* ctxt,
                           DefaultSwitchApproval*& h) {
    h = dynamic_cast<DefaultSwitchApproval*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(DefaultSwitchApproval).name())));
}


REGISTER_COMPONENT(container::Simple_component_factory<DefaultSwitchApproval>,
                   DefaultSwitchApproval);

