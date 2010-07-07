/* Passive fingerprinting app.
 *
 * class pf is essentially a facade
 * (http://en.wikipedia.org/wiki/Fa%C3%A7ade_pattern) for pf and p0f
 * fingerprinting methods.
 *
 */

#ifndef PF_HH__
#define PF_HH__

#include <xercesc/dom/DOM.hpp>

#include <map>
#include <vector>
#include <functional>
#include <algorithm>
#include <string> 
#include <list> 

#include "netinet++/ethernetaddr.hh"
#include "netinet++/ipaddr.hh"

#include "hash_map.hh"
#include "component.hh"
#include "pf-match.hh"
#include "authenticator/authenticator.hh"

extern "C" {
#include <time.h>
}

namespace vigil {
namespace applications {

struct pf_results
{
    timeval tv;
    p0f_match p0f; 
    pf_match  bpf;
};
    
class ipaddr_hash: std::unary_function<const ipaddr&, size_t> {
public:
  result_type operator()(argument_type i) const
  { 
    return i.addr; 
  }
};

class ethernetaddr_hash: std::unary_function<const ethernetaddr&, size_t> {
public:
  result_type operator()(argument_type i) const
  { 
    return ((int*)i.octet)[0]; // just use first 4 bytes 
  }
};


class p0f_sigs;
class pf_sigs;

class pf
    : public container::Component
{

public:


    typedef hash_map<ethernetaddr, hash_map<ipaddr, pf_results, ipaddr_hash >, ethernetaddr_hash  > FPMap;
    typedef hash_map<ipaddr, pf_results, ipaddr_hash> FP_IP_Map; 
    FPMap syn_fp_map;
    FPMap synack_fp_map;

    static char P0F_SFILE[];
    static char P0F_AFILE[];
    static char PF_SFILE [];
    
    pf(const container::Context*, const xercesc::DOMNode*);
    ~pf();

    static void getInstance(const container::Context*, pf*&);

    void configure(const container::Configuration*);
    void install();
    
    bool fp(const uint8_t* data, int size, pf_results& matchme);
    //bool fp(const Nonowning_buffer& packet, pf_results& res);

    //bool get_fingerprints(const ethernetaddr&, std::vector<pf_results>& );
    bool get_fingerprints(const ethernetaddr&, const ipaddr&, pf_results& );
    list<string> get_all_fingerprints(); // for debugging 
    
private:
    Authenticator *authenticator; // needs host_exists() function 
    Disposition pf_packet_handler(const Event& e);    
    Disposition host_event(const Event& e); 

    p0f_sigs* p0f_synsigs;
    p0f_sigs* p0f_synacksigs;
    
    pf_sigs * pf_synsigs;

};

} // application namespace
} // vigil namespace


#endif  /* PF_HH__ */
