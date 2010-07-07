/*
 * memory representation of p0f sig file. 
 */

#ifndef P0F_SIGS_HH
#define P0F_SIGS_HH

#include <string>
#include <cstring>

extern "C" {
#include "fpentry.h"
}


namespace vigil {
namespace applications {

struct p0f_match;

struct p0f_sigs
{
private:    
    static const int MAX_SIGS    = 1024;

    // TODO: use vector with no limit
    struct fp_entry sig   [MAX_SIGS];
    struct fp_entry* bh[16];

    int sigcnt;

    void find_match(_u16 tot,_u8 df,_u8 ttl,_u16 wss,_u32 src,
                           _u32 dst,_u16 sp,_u16 dp,_u8 ocnt,_u8* op,_u16 mss,
                           _u8 wsc,_u32 tstamp,_u8 tos,_u32 quirks,_u8 ecn,
                           _u8* pkt,_u8 plen,_u8* pay, p0f_match&);

public:    

    p0f_sigs() : sigcnt(0) { 
        ::memset(sig, 0, sizeof(sig)); 
        ::memset(bh, 0, sizeof(bh)); 
    }

    int load_config(const std::string& file); 
    void parse(_u8* packet, int len, p0f_match&) ;

    int numsigs(){
        return sigcnt; 
    }

}; // class p0f_sigs

}
}

#endif // P0F_SIGS_HH
