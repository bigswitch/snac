/*
 */
#ifndef P0F_MATCH_HH
#define P0F_MATCH_HH

#include <string>

namespace vigil {
namespace applications {

struct pf_match
{
    std::string os;
    std::string signature;
};


struct p0f_match
{
    std::string os;
    std::string os_desc;
    std::string signature;
    std::string link_type;

    bool wss_mss_missmatch; // for NAT detection 
    bool ecn;
    bool df_missmatch; // may indicate firewall 

    bool filled;

    unsigned int timestamp;
    int isn;

    int ttl_distance; // OS default ttl - ttl

    p0f_match():
        wss_mss_missmatch(false), ecn(false), df_missmatch(false),
        filled(false), timestamp(0), isn(-1), ttl_distance(-1)
    { }
    
};

} // namespace applications
} // namespace vigil

#endif // -- P0F_MATCH_HH
