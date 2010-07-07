/*
   Port of p0f to NOX application.  Original pulled from p0f 2.0.8, file
   p0f.c containing the following copyright notice:
  
===================================================================================
  p0f - passive OS fingerprinting 
  -------------------------------

  "If you sit down at a poker game and don't see a sucker, 
  get up. You're the sucker."

  (C) Copyright 2000-2006 by Michal Zalewski <lcamtuf@coredump.cx>

  WIN32 port (C) Copyright 2003-2004 by Michael A. Davis <mike@datanerds.net>
             (C) Copyright 2003-2004 by Kirby Kuehl <kkuehl@cisco.com>
===================================================================================

Re-released under MIT License after contacting Michal.  E-mail and license follows

"""
    On Thu, 24 Jan 2008, Martin Casado wrote:

    > (http://nicira.com/docs/nox-nodis.pdf).

    That's pretty sweet. I remember seeing some related projects for
    network discovery and inventory, but it's pretty interesting to
    integrate it into a more sophisticated control solution.

    I'm happy with relicensing this for you under MIT License. When you
    become rich, send me a t-shirt or somesuch ;-)

    /mz
"""

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:
  
  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.
  
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.

  TODO: Support for SYNACK mode


*/

#include "p0f-sigs.hh"
#include "pf-match.hh"
#include "vlog.hh"

#include "netinet++/ethernet.hh"

#include <sstream>
#include <cstdlib>
#include <cstdio>
#include <cstring>

#include <ctype.h>
#include <sys/types.h>
#  include <netinet/in.h>

extern "C" {
#include "types.h"
#include "tcp.h"
#include "mtu.h"
#include "tos.h"
#include "fpentry.h"
}

#define SIGHASH(tsize,optcnt,q,df) \
        (( (_u8) (((tsize) << 1) ^ ((optcnt) << 1) ^ (df) ^ (q) )) & 0x0f)

using namespace std;
using namespace vigil;
using namespace vigil::applications;

static Vlog_module lg("p0f");

int 
p0f_sigs::load_config(const string& file)
{

    _u32 ln=0;
    char  buf[MAXLINE];
    char* p;

    FILE* c = fopen(file.c_str(), "r");

    while ((p=fgets(buf, sizeof(buf),c))) {
        _u32 l;

        char obuf[MAXLINE],genre[MAXLINE],desc[MAXLINE],quirks[MAXLINE];
        char w[MAXLINE],sb[MAXLINE];
        char* gptr = genre;
        _u32 t,d,s;
        struct fp_entry* e;

        ln++;

        /* Remove leading and trailing blanks */
        while (isspace(*p)) p++;
        l=strlen(p);
        while (l && isspace(*(p+l-1))) *(p+(l--)-1)=0;

        /* Skip empty lines and comments */
        if (!l) continue;
        if (*p == '#') continue;

        if (sscanf(p,"%[0-9%*()ST]:%d:%d:%[0-9()*]:%[^:]:%[^ :]:%[^:]:%[^:]",
                    w,         &t,&d,sb,     obuf, quirks,genre,desc) != 8){
            lg.err("Syntax error in config line %d.\n",ln);
            return -1;
        }

        gptr = genre;

        if (*sb != '*') {
            s = atoi((char*)sb); 
        } else s = 0;

reparse_ptr:

        switch (*gptr) {
            case '-': sig[sigcnt].userland = 1; gptr++; goto reparse_ptr;
            case '*': sig[sigcnt].no_detail = 1; gptr++; goto reparse_ptr;
            case '@': sig[sigcnt].generic = 1; gptr++;  goto reparse_ptr;
            case 0: 
                lg.err("Empty OS genre in line %d.\n",ln);
                return -1;
        }

        sig[sigcnt].os     = (_u8*)strdup(gptr);
        sig[sigcnt].desc   = (_u8*)strdup(desc);
        sig[sigcnt].ttl    = t;
        sig[sigcnt].size   = s;
        sig[sigcnt].df     = d;

        if (w[0] == '*') {
            sig[sigcnt].wsize = 1;
            sig[sigcnt].wsize_mod = MOD_CONST;
        } else if (tolower(w[0]) == 's') {
            sig[sigcnt].wsize_mod = MOD_MSS;
            if (!isdigit(*(w+1))) {
                lg.err("Bad Snn value in WSS in line %d.\n",ln);
                return -1;
            }
            sig[sigcnt].wsize = atoi(w+1);
        } else if (tolower(w[0]) == 't') {
            sig[sigcnt].wsize_mod = MOD_MTU;
            if (!isdigit(*(w+1))) {
                lg.err("Bad Tnn value in WSS in line %d.\n",ln);
                return -1;
            }
            sig[sigcnt].wsize = atoi(w+1);
        } else if (w[0] == '%') {
            if (!(sig[sigcnt].wsize = atoi(w+1))){
                lg.err("Null modulo for window size in config line %d.\n",ln);
                return -1;
            }
            sig[sigcnt].wsize_mod = MOD_CONST;
        } else sig[sigcnt].wsize = atoi(w);

        /* Now let's parse options */

        p=obuf;

        sig[sigcnt].zero_stamp = 1;

        if (*p=='.') p++;

        while (*p) {
            _u8 optcnt = sig[sigcnt].optcnt;
            switch (tolower(*p)) {

                case 'n': sig[sigcnt].opt[optcnt] = TCPOPT_NOP;
                          break;

                case 'e': sig[sigcnt].opt[optcnt] = TCPOPT_EOL;
                          if (*(p+1)) {
                              lg.err("EOL not the last option (line %d).\n",ln);
                          }
                          break;

                case 's': sig[sigcnt].opt[optcnt] = TCPOPT_SACKOK;
                          break;

                case 't': sig[sigcnt].opt[optcnt] = TCPOPT_TIMESTAMP;
                          if (*(p+1)!='0') {
                              sig[sigcnt].zero_stamp=0;
                              if (isdigit(*(p+1))) {
                                  lg.err("Bogus Tstamp specification in line %d.\n",ln);
                              }
                          }
                          break;

                case 'w': sig[sigcnt].opt[optcnt] = TCPOPT_WSCALE;
                          if (p[1] == '*') {
                              sig[sigcnt].wsc = 1;
                              sig[sigcnt].wsc_mod = MOD_CONST;
                          } else if (p[1] == '%') {
                              if (!(sig[sigcnt].wsc = atoi(p+2))){
                                  lg.err("Null modulo for wscale in config line %d.\n",ln);
                              }
                              sig[sigcnt].wsc_mod = MOD_CONST;
                          } else if (!isdigit(*(p+1))){
                              lg.err("Incorrect W value in line %d.\n",ln);
                              return -1;
                          }
                          else sig[sigcnt].wsc = atoi(p+1);
                          break;

                case 'm': sig[sigcnt].opt[optcnt] = TCPOPT_MAXSEG;
                          if (p[1] == '*') {
                              sig[sigcnt].mss = 1;
                              sig[sigcnt].mss_mod = MOD_CONST;
                          } else if (p[1] == '%') {
                              if (!(sig[sigcnt].mss = atoi(p+2))){
                                  lg.err("Null modulo for MSS in config line %d.\n",ln);
                                  return -1;
                              }
                              sig[sigcnt].mss_mod = MOD_CONST;
                          } else if (!isdigit(*(p+1))){
                              lg.err("Incorrect M value in line %d.\n",ln);
                              return -1;
                          }
                          else sig[sigcnt].mss = atoi(p+1);
                          break;

                          /* Yuck! */
                case '?': if (!isdigit(*(p+1))){
                              lg.err("Bogus ?nn value in line %d.\n",ln);
                          }
                          else sig[sigcnt].opt[optcnt] = atoi(p+1);
                          break;

                default: 
                          lg.err("Unknown TCP option '%c' in config line %d.\n",*p,ln);
                          return -1;
            }

            if (++sig[sigcnt].optcnt >= MAXOPT) {
                lg.err("Too many TCP options specified in config line %d.\n",ln);
                return -1;
            }

            /* Skip separators */
            do { p++; } while (*p && !isalpha(*p) && *p != '?');

        }

        sig[sigcnt].line = ln;

        p = quirks;

        while (*p) 
            switch (toupper(*(p++))) {
                case 'E': 
                    lg.err("Quirk 'E' (line %d) is obsolete. Remove it, append E to the "
                            "options.\n",ln);
                    return -1;
                case 'K': 
                    sig[sigcnt].quirks |= QUIRK_RSTACK; 
                    break;

                case 'D': 
                    sig[sigcnt].quirks |= QUIRK_DATA; 
                    break;

                case 'Q': sig[sigcnt].quirks |= QUIRK_SEQEQ; break;
                case '0': sig[sigcnt].quirks |= QUIRK_SEQ0; break;
                case 'P': sig[sigcnt].quirks |= QUIRK_PAST; break;
                case 'Z': sig[sigcnt].quirks |= QUIRK_ZEROID; break;
                case 'I': sig[sigcnt].quirks |= QUIRK_IPOPT; break;
                case 'U': sig[sigcnt].quirks |= QUIRK_URG; break;
                case 'X': sig[sigcnt].quirks |= QUIRK_X2; break;
                case 'A': sig[sigcnt].quirks |= QUIRK_ACK; break;
                case 'T': sig[sigcnt].quirks |= QUIRK_T2; break;
                case 'F': sig[sigcnt].quirks |= QUIRK_FLAGS; break;
                case '!': sig[sigcnt].quirks |= QUIRK_BROKEN; break;
                case '.': break;
                default: 
                      lg.err("Bad quirk '%c' in line %d.\n",*(p-1),ln);
                      return -1;
            }

        e = bh[SIGHASH(s,sig[sigcnt].optcnt,sig[sigcnt].quirks,d)];

        if (!e) {
            bh[SIGHASH(s,sig[sigcnt].optcnt,sig[sigcnt].quirks,d)] = sig + sigcnt;
        } else {
            while (e->next) e = e->next;
            e->next = sig + sigcnt;
        } 

        sig[sigcnt].next = 0;

        if (++sigcnt >= MAXSIGS){
            lg.err("Maximum signature count exceeded.\n");
            return -1;
        }

    }

    fclose(c);

#ifdef DEBUG_HASH
    { 
        int i;
        struct fp_entry* p;
        printf("Hash table layout: ");
        for (i=0;i<16;i++) {
            int z=0;
            p = bh[i];
            while (p) { p=p->next; z++; }
            printf("%d ",z);
        }
        putchar('\n');
    }
#endif /* DEBUG_HASH */

    if (!sigcnt){
        lg.warn("[!] WARNING: no signatures loaded from config file.\n");
    }

    return sigcnt;
}


static const char* lookup_tos(_u8 t) {
  _u32 i;

  if (!t) return 0;

  for (i=0;i<TOS_CNT;i++) {
   if (t == tos[i].tos) return tos[i].desc;
   if (t < tos[i].tos) break;
  }

  return 0;

}

static const bool use_fuzzy = true;

static const char* lookup_link(_u16 mss,char txt) {
  _u32 i;
  static char tmp[32];

  if (!mss) return txt ? "unspecified" : 0;
  mss += 40;
  
  for (i=0;i<MTU_CNT;i++) {
   if (mss == mtu[i].mtu) return mtu[i].dev;
   if (mss < mtu[i].mtu)  goto unknown;
  }

unknown:

  if (!txt) return 0;
  sprintf(tmp,"unknown-%d",mss);
  return tmp;

}

static inline void display_signature(_u8 ttl,_u16 tot,_u8 df,_u8* op,_u8 ocnt,
                                     _u16 mss,_u16 wss,_u8 wsc,_u32 tstamp,
                                     _u32 quirks, string& fillme) 
{
    ostringstream ostr;

    _u32 j;
    _u8 d=0;

    if (mss && wss && !(wss % mss)) { 
        ostr<<"S"<<(int)wss/mss; 
    } else if (wss && !(wss % 1460)) {
        ostr<<"S"<<(int)wss/1460; 
    }else if (mss && wss && !(wss % (mss+40))) {
        ostr<<"T"<<(int)wss/(mss+40); 
    }else if (wss && !(wss % 1500)) {
        ostr<<"T"<<(int)wss/(1500); 
    } else if (wss == 12345) {
        ostr<<"*(12345)"; 
    } else {
        ostr<<(int)wss;
    }

    if (tot < PACKET_BIG){
        ostr << ":" << (int)ttl 
             << ":" << (int)df
             << ":" << (int)tot << ":";
    } else{
        ostr << ":"   << (int)ttl 
             << ":"   << (int)df
             << ":*(" << (int)tot << "):";
    }


    for (j=0;j<ocnt;j++) {
        switch (op[j]) {
            case TCPOPT_NOP: 
                ostr << 'N';
                d=1; 
                break;
            case TCPOPT_WSCALE: 
                ostr << 'W' << (int)wsc;
                d=1; 
                break;
            case TCPOPT_MAXSEG: 
                ostr << 'M' << (int)mss;
                d=1; 
                break;
            case TCPOPT_TIMESTAMP: 
                ostr << "T";
               if (!tstamp) {
                    ostr << "0";
               }
               d=1; 
               break;
            case TCPOPT_SACKOK: 
                ostr << "S";
                d=1; 
                break;
            case TCPOPT_EOL: 
                ostr << "E";
                d=1; 
                break;
            default: 
                ostr << "?" << (int)op[j];
                d=1; 
                break;
        }
        if (j != ocnt-1){
            ostr << ",";
        }
    }

    if (!d){
        ostr << ".";
    }

    ostr << ":";

    if (!quirks) {
        ostr << ".";
    } else {
        if (quirks & QUIRK_RSTACK) ostr << ("K");
        if (quirks & QUIRK_SEQEQ) ostr << ("Q");
        if (quirks & QUIRK_SEQ0) ostr << ("0");
        if (quirks & QUIRK_PAST) ostr << ("P");
        if (quirks & QUIRK_ZEROID) ostr << ("Z");
        if (quirks & QUIRK_IPOPT) ostr << ("I");
        if (quirks & QUIRK_URG) ostr << ("U");
        if (quirks & QUIRK_X2) ostr << ("X");
        if (quirks & QUIRK_ACK) ostr << ("A");
        if (quirks & QUIRK_T2) ostr << ("T");
        if (quirks & QUIRK_FLAGS) ostr << ("F");
        if (quirks & QUIRK_DATA) ostr << ("D");
        if (quirks & QUIRK_BROKEN) ostr << ("!");
    }

    ostr << "\0";
    fillme = ostr.str();
}

void 
p0f_sigs::find_match(_u16 tot,_u8 df,_u8 ttl,_u16 wss,_u32 src,
                       _u32 dst,_u16 sp,_u16 dp,_u8 ocnt,_u8* op,_u16 mss,
                       _u8 wsc,_u32 tstamp,_u8 tos,_u32 quirks,_u8 ecn,
                       _u8* pkt,_u8 plen,_u8* pay, p0f_match& fillme) 
{

    _u32 j;
    _u8* a;
    _u8  nat=0;
    struct fp_entry* p;
    _u8  orig_df  = df;
    const char* tos_desc = 0;

    struct fp_entry* fuzzy = 0;
    _u8 fuzzy_now = 0;

re_lookup:

    p = bh[SIGHASH(tot,ocnt,quirks,df)];

    if (tos) tos_desc = lookup_tos(tos);

    while (p) {

        /* Cheap and specific checks first... */

        if (ocnt ^ p->optcnt) { p = p->next; continue; }

        if (p->zero_stamp ^ (!tstamp)) { p = p->next; continue; }
        if (p->df ^ df) { p = p->next; continue; }
        if (p->quirks ^ quirks) { p = p->next; continue; }

        /* Check MSS and WSCALE... */
        if (!p->mss_mod) {
            if (mss ^ p->mss) { p = p->next; continue; }
        } else if (mss % p->mss) { p = p->next; continue; }

        if (!p->wsc_mod) {
            if (wsc ^ p->wsc) { p = p->next; continue; }
        } else if (wsc % p->wsc) { p = p->next; continue; }

        /* Then proceed with the most complex WSS check... */
        switch (p->wsize_mod) {
            case 0:
                if (wss ^ p->wsize) { p = p->next; continue; }
                break;
            case MOD_CONST:
                if (wss % p->wsize) { p = p->next; continue; }
                break;
            case MOD_MSS:
                if (mss && !(wss % mss)) {
                    if ((wss / mss) ^ p->wsize) { p = p->next; continue; }
                } else if (!(wss % 1460)) {
                    if ((wss / 1460) ^ p->wsize) { p = p->next; continue; }
                } else { p = p->next; continue; }
                break;
            case MOD_MTU:
                if (mss && !(wss % (mss+40))) {
                    if ((wss / (mss+40)) ^ p->wsize) { p = p->next; continue; }
                } else if (!(wss % 1500)) {
                    if ((wss / 1500) ^ p->wsize) { p = p->next; continue; }
                } else { p = p->next; continue; }
                break;
        }

        /* Numbers agree. Let's check options */

        for (j=0;j<ocnt;j++)
            if (p->opt[j] ^ op[j]) goto continue_search;

        /* Check TTLs last because we might want to go fuzzy. */
        if (p->ttl < ttl) {
            if (use_fuzzy) fuzzy = p;
            p = p->next;
            continue;
        }

        /* Naah... can't happen ;-) */
        if (!p->no_detail)
            if (p->ttl - ttl > MAXDIST) { 
                if (use_fuzzy) fuzzy = p;
                p = p->next; 
                continue; 
            }

continue_fuzzy:    

        /* Match! */

        // matched_packets++;

        if (mss & wss) {
            if (p->wsize_mod == MOD_MSS) {
                if ((wss % mss) && !(wss % 1460)) nat=1;
            } else if (p->wsize_mod == MOD_MTU) {
                if ((wss % (mss+40)) && !(wss % 1500)) nat=2;
            }
        }


        a=(_u8*)&src;

        fillme.os = (char*)p->os;

        fillme.os_desc = (char*)p->desc;

        if (nat == 1 || nat == 2){
            fillme.wss_mss_missmatch = true;
        }
        // if (nat == 1) printf("(NAT!) "); else
        //     if (nat == 2) printf("(NAT2!) ");

        if (ecn) {
            fillme.ecn = true;
        }
        if (orig_df ^ df) {
            fillme.df_missmatch = true;
        }

        if (tos) {
            // if (tos_desc) printf("[%s] ",tos_desc); else printf("[tos %d] ",tos);
        }

        if (p->no_detail) printf("* "); else{
            if (tstamp){
                fillme.timestamp = tstamp;
            }
        }


       display_signature(ttl,tot,orig_df,op,ocnt,mss,wss,wsc,tstamp,quirks,fillme.signature);

        if (!p->no_detail) {
            a=(_u8*)&dst;

            if (fuzzy_now) {
                fillme.link_type = (char*)lookup_link(mss,1);
            }
            else{
                fillme.ttl_distance = p->ttl - ttl;
                fillme.link_type    = (char*)lookup_link(mss,1);
            }
        }


        //  FIXME XXX
        //
        //  if (find_masq && !p->userland) {
        //     _s16 sc = p0f_findmasq(src,p->os,(p->no_detail || fuzzy_now) ? -1 : 
        //             (p->ttl - ttl), mss, nat, orig_df ^ df,p-sig,
        //             tstamp ? tstamp / 360000 : -1);
        //     a=(_u8*)&src;
        //     if (sc > masq_thres) {
        //         printf(">> Masquerade at %u.%u.%u.%u: indicators at %d%%.",
        //                 a[0],a[1],a[2],a[3],sc);
        //         putchar('\n');
        //         if (masq_flags) {
        //             printf("   Flags: ");
        //             p0f_descmasq();
        //             putchar('\n');
        //         }
        //     }
        // }
        // 
        // if (use_cache || find_masq)
        //     p0f_addcache(src,dst,sp,dp,p->os,p->desc,(p->no_detail || fuzzy_now) ? 
        //             -1 : (p->ttl - ttl),p->no_detail ? 0 : lookup_link(mss,0),
        //             tos_desc, orig_df ^ df, nat, !p->userland, mss, p-sig,
        //             tstamp ? tstamp / 360000 : -1);

        fflush(0);

        fillme.filled = true;
        return;

continue_search:

        p = p->next;

    }

    if (!df) { df = 1; goto re_lookup; }

    if (use_fuzzy && fuzzy) {
        df = orig_df;
        fuzzy_now = 1;
        p = fuzzy;
        fuzzy = 0;
        goto continue_fuzzy;
    }

    if (mss & wss) {
        if ((wss % mss) && !(wss % 1460)) nat=1;
        else if ((wss % (mss+40)) && !(wss % 1500)) nat=2;
    }

    a=(_u8*)&src;

    fillme.os = "unknown";

    display_signature(ttl,tot,orig_df,op,ocnt,mss,wss,wsc,tstamp,quirks, fillme.signature);

    if (nat == 1 || nat == 2){
        fillme.wss_mss_missmatch = true;
    }

    // if (nat == 1) printf("(NAT!) ");
    // else if (nat == 2) printf("(NAT2!) ");

    if (ecn) {
        fillme.ecn = true;
        // printf("(ECN) ");
    }

    if (tos) {
        // if (tos_desc) printf("[%s] ",tos_desc); else printf("[tos %d] ",tos);
    }

    if (tstamp){
        fillme.timestamp = tstamp;
    }

    a=(_u8*)&dst;
    fillme.link_type = (char*)lookup_link(mss,1);

    // if (use_cache)
    //     p0f_addcache(src,dst,sp,dp,0,0,-1,lookup_link(mss,0),tos_desc,
    //             0,nat,0 /* not real, we're not sure */ ,mss,(_u32)-1,
    //             tstamp ? tstamp / 360000 : -1);

    fillme.filled = true;
}


#define GET16(p) \
        ((_u16) *((_u8*)(p)+0) << 8 | \
         (_u16) *((_u8*)(p)+1) )


void 
p0f_sigs::parse(_u8* packet, int len, p0f_match& fillme) 
{
  struct ip_header *iph;
  struct tcp_header *tcph;
  _u8*   end_ptr;
  _u8*   opt_ptr;
  _u8*   pay = 0;
  _s32   ilen,olen;

  _u8    op[MAXOPT];
  _u8    ocnt = 0;
  _u16   mss_val = 0, wsc_val = 0;
  _u32   tstamp = 0;
  _u32   quirks = 0;

  // packet_count++;

  end_ptr = packet + len;

  // XXX Jump past Ethernet header
  ethernet* ethh = (ethernet*)packet; 
  if (ethh->type == ethernet::VLAN){
      iph = (struct ip_header*)(packet + 18);
  }else{
      iph = (struct ip_header*)(packet + 14);
  }

  /* Whoops, IP header ends past end_ptr */
  if ((_u8*)(iph + 1) > end_ptr) return;

  if ( ((iph->ihl & 0x40) != 0x40) || iph->proto != IPPROTO_TCP) {
    fprintf(stderr, "[!] WARNING: Non-IP packet received. Bad header_len!\n");
    return;
  }

  /* If the declared length is shorter than the snapshot (etherleak
     or such), truncate this bad boy. */

  opt_ptr = (_u8*)iph + htons(iph->tot_len);
  if (end_ptr > opt_ptr) end_ptr = opt_ptr;

  ilen = iph->ihl & 15;

  /* Borken packet */
  if (ilen < 5) return;

  if (ilen > 5) {

#ifdef DEBUG_EXTRAS
      _u8 i;
      printf("  -- EXTRA IP OPTIONS (packet below): ");
      for (i=0;i<ilen-5;i++) 
          printf("%08x ",(_u32)ntohl(*(((_u32*)(iph+1))+i)));
      putchar('\n');
      fflush(0);
#endif /* DEBUG_EXTRAS */

      quirks |= QUIRK_IPOPT;
  }

  tcph = (struct tcp_header*)((_u8*)iph + (ilen << 2));
  opt_ptr = (_u8*)(tcph + 1);
    
  /* Whoops, TCP header would end past end_ptr */
  if (opt_ptr > end_ptr) return;

  fillme.isn = ntohl(tcph->seq);

  if (tcph->seq == tcph->ack) quirks |= QUIRK_SEQEQ;
  if (!tcph->seq) quirks |= QUIRK_SEQ0;
 
  if (tcph->flags & ~(TH_SYN|TH_ACK|TH_RST|TH_ECE|TH_CWR)) 
    quirks |= QUIRK_FLAGS;

  ilen=((tcph->doff) << 2) - sizeof(struct tcp_header);
  
  if ( (_u8*)opt_ptr + ilen < end_ptr) { 
  
#ifdef DEBUG_EXTRAS
    _u32 i;
    
    printf("  -- EXTRA PAYLOAD (packet below): ");
    
    for (i=0;i< (_u32)end_ptr - ilen - (_u32)opt_ptr;i++)
      printf("%02x ",*(opt_ptr + ilen + i));

    putchar('\n');
    fflush(0);
#endif /* DEBUG_EXTRAS */
  
    quirks |= QUIRK_DATA;
    pay = opt_ptr + ilen;
   
  }

  while (ilen > 0) {

    ilen--;

    switch (*(opt_ptr++)) {
      case TCPOPT_EOL:  
        /* EOL */
        op[ocnt] = TCPOPT_EOL;
        ocnt++;

        if (ilen) {

          quirks |= QUIRK_PAST;

#ifdef DEBUG_EXTRAS

          printf("  -- EXTRA TCP OPTIONS (packet below): ");

          while (ilen) {
            ilen--;
            if (opt_ptr >= end_ptr) { printf("..."); break; }
            printf("%02x ",*(opt_ptr++));
          }

          putchar('\n');
          fflush(0);

#endif /* DEBUG_EXTRAS */

        }

        /* This goto will be probably removed at some point. */
        goto end_parsing;

      case TCPOPT_NOP:
        /* NOP */
        op[ocnt] = TCPOPT_NOP;
        ocnt++;
        break;

      case TCPOPT_SACKOK:
        /* SACKOK LEN */
        op[ocnt] = TCPOPT_SACKOK;
        ocnt++; ilen--; opt_ptr++;
        break;
        
      case TCPOPT_MAXSEG:
        /* MSS LEN D0 D1 */
        if (opt_ptr + 3 > end_ptr) {
borken:
          quirks |= QUIRK_BROKEN;
          goto end_parsing;
        }
        op[ocnt] = TCPOPT_MAXSEG;
        mss_val = GET16(opt_ptr+1);
        ocnt++; ilen -= 3; opt_ptr += 3;
        break;

      case TCPOPT_WSCALE:
        /* WSCALE LEN D0 */
        if (opt_ptr + 2 > end_ptr) goto borken;
        op[ocnt] = TCPOPT_WSCALE;
        wsc_val = *(_u8 *)(opt_ptr + 1);
        ocnt++; ilen -= 2; opt_ptr += 2;
        break;

      case TCPOPT_TIMESTAMP:
        /* TSTAMP LEN T0 T1 T2 T3 A0 A1 A2 A3 */
        if (opt_ptr + 9 > end_ptr) goto borken;
        op[ocnt] = TCPOPT_TIMESTAMP;

        memcpy(&tstamp, opt_ptr+5, 4);
        if (tstamp) quirks |= QUIRK_T2;

        memcpy(&tstamp, opt_ptr+1, 4);
        tstamp = ntohl(tstamp);

        ocnt++; ilen -= 9; opt_ptr += 9;
        break;

      default:

        /* Hrmpf... */
        if (opt_ptr + 1 > end_ptr) goto borken;

        op[ocnt] = *(opt_ptr-1);
        olen = *(_u8*)(opt_ptr)-1;
        if (olen > 32 || (olen < 0)) goto borken;

        ocnt++; ilen -= olen; opt_ptr += olen;
        break;

     }

     if (ocnt >= MAXOPT-1) goto borken;

     /* Whoops, we're past end_ptr */
     if (ilen > 0)
       if (opt_ptr >= end_ptr) goto borken;

   }

end_parsing:

   if (tcph->ack) quirks |= QUIRK_ACK;
   if (tcph->urg) quirks |= QUIRK_URG;
   if (tcph->_x2) quirks |= QUIRK_X2;
   if (!iph->id)  quirks |= QUIRK_ZEROID;

   find_match(
     /* total */ ntohs(iph->tot_len),
     /* DF */    (ntohs(iph->off) & IP_DF) != 0,
     /* TTL */   iph->ttl,
     /* WSS */   ntohs(tcph->win),
     /* src */   iph->saddr,
     /* dst */   iph->daddr,
     /* sp */    ntohs(tcph->sport),
     /* dp */    ntohs(tcph->dport),
     /* ocnt */  ocnt,
     /* op */    op,
     /* mss */   mss_val,
     /* wsc */   wsc_val,
     /* tst */   tstamp,
     /* TOS */   iph->tos,
     /* Q? */    quirks,
     /* ECN */   tcph->flags & (TH_ECE|TH_CWR),
     /* pkt */   (_u8*)iph,
     /* len */   end_ptr - (_u8*)iph,
     /* pay */   pay,
     fillme
  );

#ifdef DEBUG_EXTRAS

  if (quirks & QUIRK_FLAGS || tcph->ack || tcph->_x2 || tcph->urg) 
    lg.warn("  -- EXTRA TCP VALUES: ACK=0x%x, UNUSED=%d, URG=0x%x "
           "(flags = %x)\n",tcph->ack,tcph->_x2,tcph->urg,tcph->flags);
  fflush(0);

#endif /* DEBUG_EXTRAS */

}
