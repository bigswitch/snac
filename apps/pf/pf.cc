#include "pf.hh"

#include <string>

#include <boost/bind.hpp>

#include "assert.hh"
#include "netinet++/ethernet.hh"
#include "netinet++/ip.hh"
#include "netinet++/tcp.hh"
#include "netinet++/vlan.hh"
#include "packet-in.hh"
#include "vlog.hh"
#include "authenticator/host-event.hh"
#include <sstream> 

#include "pf-sigs.hh"
#include "p0f-sigs.hh"

extern "C" {
#include <sys/stat.h>
}

using namespace vigil;
using namespace vigil::applications;
using namespace vigil::container;
using namespace std;

namespace {

Vlog_module lg("pf");

/* This should be moved to a public utility header to standardize access
 * to data files 
 */

string find_file(const string& base)
{
    struct stat s;

    if (stat(base.c_str(), &s) == 0) {
        return base; 
    } else if (stat((PKGDATADIR+base).c_str(), &s) == 0) {
        return PKGDATADIR+base;
    }else{
        lg.err("%s",("Unable to find " + base).c_str());
        return "";
    }
}

template <typename T>
void load_pf_file(const char* filename, T* sigs)
{
    string pffile    = find_file(filename);
    if (pffile == ""){
        lg.warn("unable to locate pf file %s", filename);
        // TODO: shouldn't we fail and throw runtime_exception here?
    }else{
        if (sigs->load_config(pffile) >= 0){
            lg.dbg("loaded %d SYN signatures from %s", sigs->numsigs(),
                   pffile.c_str());
        }
    }
}

} // unnamed namespace

namespace vigil {
namespace applications {

char pf::P0F_SFILE[] = "nox/ext/apps/pf/p0f.fp";
char pf::P0F_AFILE[] = "nox/ext/apps/pf/p0fa.fp";
char pf::PF_SFILE [] = "nox/ext/apps/pf/pf.os";

pf::pf(const vigil::container::Context* c,
       const xercesc::DOMNode*) 
    : Component(c)
{
    p0f_synsigs    = new p0f_sigs();
    assert(p0f_synsigs);
    p0f_synacksigs = new p0f_sigs();
    assert(p0f_synacksigs);
    pf_synsigs     = new pf_sigs();
    assert(pf_synsigs);
}

pf::~pf()
{
    if(p0f_synsigs){
        delete p0f_synsigs;
    }
    if(p0f_synacksigs){
        delete p0f_synacksigs;
    }
    if(pf_synsigs){
        delete pf_synsigs;
    }
}

void 
pf::getInstance(const container::Context* ctxt, pf*& p) {
    p = dynamic_cast<pf*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(pf).name())));
}

void pf::configure(const Configuration*)
{
    /* p0f */
    load_pf_file(P0F_SFILE, p0f_synsigs);
    load_pf_file(P0F_AFILE, p0f_synacksigs);
    /* pf */
    load_pf_file(PF_SFILE, pf_synsigs);

    // only call on TCP packets 
    Packet_expr expr;
    uint32_t val = ethernet::IP;
    expr.set_field(Packet_expr::DL_TYPE,  &val); 
    val = ip_::proto::TCP;
    expr.set_field(Packet_expr::NW_PROTO, &val); 

    register_handler_on_match(100,
                              expr,            
                              boost::bind(&pf::pf_packet_handler, this, _1));
    
    //needed to determine if a src IP address is 'local'
    resolve(authenticator);

    //used to time out fingerprint data
    register_handler<Host_event>(boost::bind(&pf::host_event, this, _1)); 
}

bool pf::fp(const uint8_t* data, int size, pf_results& matchme)
{
    int bufsize = size; 
    int min_header_len = 0;

    if (bufsize < 14 + 20 + 20) {
        return false; 
    }

    ethernet* ethh = (ethernet*)data;
    min_header_len += 14;
    ip_* iph = 0;

    uint16_t ethtype_nbo = ethh->type;

    // jump past VLAN header if necessary
    if (ethtype_nbo == ethernet::VLAN){
        min_header_len += 4;
        vlan* vlanh = (vlan*)(data + sizeof(struct ethernet));
        ethtype_nbo = vlanh->encapsulated_proto;
        iph = (ip_*)(data + sizeof(struct ethernet) + sizeof(vlan));
    }else{
        iph = (ip_*)(data + sizeof(struct ethernet));
    }
    if(ethtype_nbo != ethernet::IP){
        return false;
    }

    min_header_len += (iph->ihl * 4);
    if (bufsize < min_header_len){
        return false; 
    }

    if(iph->protocol != ip_::proto::TCP){
        return false;
    }

    tcp* tcph = (tcp*)(((uint8_t*)iph) + (iph->ihl * 4));

    if (tcph->flags == tcp::SYN) {
        p0f_synsigs->parse ((uint8_t*)data, bufsize, matchme.p0f);
        pf_synsigs->parse  ((uint8_t*)data, bufsize, matchme.bpf);
        return true;
    } else if (tcph->flags == (tcp::SYN | tcp::ACK)) {
        p0f_synacksigs->parse((uint8_t*)data, bufsize, matchme.p0f);
        return true;
    } 

    return false;
}

Disposition 
pf::pf_packet_handler(const Event& e)
{
    const Packet_in_event& pi = assert_cast<const Packet_in_event&>(e);
    pf_results res;

    const uint8_t* data = pi.get_buffer()->data();
    int size = pi.get_buffer()->size();
    int min_header_len = 0;

    if (size < 14 + 20 + 20) {
        return CONTINUE; 
    }

    ethernet* ethh = (ethernet*)data;
    min_header_len += 14;
    ip_* iph = 0;

    uint16_t ethtype_nbo = ethh->type;

    // jump past VLAN header if necessary
    if (ethtype_nbo == ethernet::VLAN){
        min_header_len += 4;
        vlan* vlanh = (vlan*)(data + sizeof(struct ethernet));
        ethtype_nbo = vlanh->encapsulated_proto;
        iph = (ip_*)(data + sizeof(struct ethernet) + sizeof(vlan));
    }else{
        iph = (ip_*)(data + sizeof(struct ethernet));
    }
    if(ethtype_nbo != ethernet::IP){
        return CONTINUE;
    }

    min_header_len += (iph->ihl * 4);
    if (size < min_header_len){
        return CONTINUE; 
    }

    if(iph->protocol != ip_::proto::TCP){
        return CONTINUE;
    }

    if(!authenticator->host_exists(ethh->saddr, ntohl(iph->saddr.addr))) { 
      return CONTINUE; 
    }
    
    tcp* tcph = (tcp*)(((uint8_t*)iph) + (iph->ihl * 4));

    // SYN fingerprint is better than a SYN ACK fingerprint
    // If we have a SYN print already, always ignore
    // If we have a SYN-ACK print already, ignore only if packet is not a SYN
    // If we have no existing fingerprints, always take fingerprint
    if (syn_fp_map[ethh->saddr].find(iph->saddr) == syn_fp_map[ethh->saddr].end()
          && tcph->flags == tcp::SYN ){
        pf_results& matchme = syn_fp_map[ethh->saddr][iph->saddr];
        p0f_synsigs->parse ((uint8_t*)data, size, matchme.p0f);
        pf_synsigs->parse  ((uint8_t*)data, size, matchme.bpf);
        ::gettimeofday(&matchme.tv, 0);
    }else if (synack_fp_map[ethh->saddr].find(iph->saddr) == synack_fp_map[ethh->saddr].end()
          && tcph->flags == (tcp::SYN | tcp::ACK)){
        pf_results& matchme = synack_fp_map[ethh->saddr][iph->saddr];
        p0f_synacksigs->parse((uint8_t*)data, size, matchme.p0f);
        ::gettimeofday(&matchme.tv, 0);
    }
    
    return CONTINUE;
}

Disposition 
pf::host_event(const Event& e) { 
    const Host_event& hi = assert_cast<const Host_event&>(e);
    if(hi.action != Host_event::LEAVE) return CONTINUE; 

    // tasha says that if IP is non-zero, remove only that mac-ip pair.
    // otherwise, remove all entries for that mac.  
    if(hi.nwaddr != 0) { 
      ipaddr ip = ipaddr(hi.nwaddr); 
      if(syn_fp_map.find(hi.dladdr) != syn_fp_map.end()
          && syn_fp_map[hi.dladdr].find(ip) != syn_fp_map[hi.dladdr].end()){
          syn_fp_map[hi.dladdr].erase(ip); 
          if(syn_fp_map[hi.dladdr].size() == 0) 
            syn_fp_map.erase(hi.dladdr); 
      }
      if(synack_fp_map.find(hi.dladdr) != synack_fp_map.end()
          && synack_fp_map[hi.dladdr].find(ip) != synack_fp_map[hi.dladdr].end()){
          synack_fp_map[hi.dladdr].erase(ip); 
          if(synack_fp_map[hi.dladdr].size() == 0) 
            synack_fp_map.erase(hi.dladdr); 
      }

    } else  {
        if(syn_fp_map.find(hi.dladdr) != syn_fp_map.end()){
          syn_fp_map.erase(hi.dladdr); 
        }
        if(synack_fp_map.find(hi.dladdr) != synack_fp_map.end()){
          synack_fp_map.erase(hi.dladdr); 
        }
    }
    return CONTINUE; 
}
/*
bool 
pf::get_fingerprints(const ethernetaddr& etha, vector<pf_results>& vpf)
{
    if(fp_map.find(etha) == fp_map.end()){
        return false;
    }

    for ( hash_map<ipaddr, pf_results, ipaddr_hash>::iterator iter = fp_map[etha].begin();
            iter != fp_map[etha].end(); ++iter){
        vpf.push_back(iter->second);
    }

    return true;
}
*/ 

bool 
pf::get_fingerprints(const ethernetaddr& etha, const ipaddr& ipa,  pf_results& vpf)
{
    if(syn_fp_map.find(etha) != syn_fp_map.end() && 
       syn_fp_map[etha].find(ipa) != syn_fp_map[etha].end()){
        vpf = syn_fp_map[etha][ipa];
        return true;
    }
    if(synack_fp_map.find(etha) != synack_fp_map.end() &&
       synack_fp_map[etha].find(ipa) != synack_fp_map[etha].end()){
        vpf = synack_fp_map[etha][ipa];
        return true;
    }
  return false; 
}

// for debugging, dump a list of all fingerprints as a list
list<string> 
pf::get_all_fingerprints() { 
    list<string> fps;   
    for ( FPMap::iterator iter1 = syn_fp_map.begin(); iter1 != syn_fp_map.end(); ++iter1){
        for(FP_IP_Map::iterator iter2 = iter1->second.begin(); iter2 != iter1->second.end(); iter2++){
          stringstream ss; 
          ss << "syn: " << iter1->first.string() << ", " << iter2->first.string()
              << ", '" << iter2->second.bpf.os << "'"; 
          fps.push_back(ss.str()); 
        } 
    }
    for ( FPMap::iterator iter1 = synack_fp_map.begin(); iter1 != synack_fp_map.end(); ++iter1){
        for(FP_IP_Map::iterator iter2 = iter1->second.begin(); iter2 != iter1->second.end(); iter2++){
          stringstream ss; 
          ss << "synack: " << iter1->first.string() << ", " << iter2->first.string()
              << ", '" << iter2->second.bpf.os << "'"; 
          fps.push_back(ss.str()); 
        } 
    }
    return fps; 
} 

void pf::install()
{

}

} // application namespace
} // vigil namespace

namespace {

REGISTER_COMPONENT(container::Simple_component_factory<pf>, pf);
    
}
