/*

   p0f - portable TCP/IP headers
   -----------------------------

   Well.

   Copyright (C) 2003-2006 by Michal Zalewski <lcamtuf@coredump.cx>

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

*/

#ifndef _HAVE_TCP_H
#define _HAVE_TCP_H

#include "types.h"

#define	TCPOPT_EOL		0	/* End of options */
#define	TCPOPT_NOP		1	/* Nothing */
#define	TCPOPT_MAXSEG		2	/* MSS */
#define TCPOPT_WSCALE   	3	/* Window scaling */
#define TCPOPT_SACKOK   	4	/* Selective ACK permitted */
#define TCPOPT_TIMESTAMP        8	/* Stamp out timestamping! */

#define IP_DF   0x4000	/* dont fragment flag */
#define IP_MF   0x2000	/* more fragments flag */

#define	TH_FIN	0x01
#define	TH_SYN	0x02
#define	TH_RST	0x04
#define	TH_PUSH	0x08
#define	TH_ACK	0x10
#define	TH_URG	0x20
/* Stupid ECN flags: */
#define TH_ECE  0x40
#define TH_CWR  0x80

struct ip_header {
  _u8  ihl,	/* IHL */
       tos;	/* type of service */
  _u16 tot_len,	/* total length */
       id,	/* identification */
       off;	/* fragment offset + DF/MF */
  _u8  ttl,	/* time to live */
       proto; 	/* protocol */
  _u16 cksum;	/* checksum */
  _u32 saddr,   /* source */
       daddr;   /* destination */
};


struct tcp_header {
  _u16 sport,	/* source port */
       dport;	/* destination port */
  _u32 seq,	/* sequence number */
       ack;	/* ack number */
#if BYTE_ORDER == LITTLE_ENDIAN
  _u8  _x2:4,	/* unused */
       doff:4;	/* data offset */
#else /* BYTE_ORDER == BIG_ENDIAN */
  _u8  doff:4,  /* data offset */
       _x2:4;	/* unused */
#endif			 
  _u8  flags;	/* flags, d'oh */
  _u16 win;	/* wss */
  _u16 cksum;	/* checksum */
  _u16 urg;	/* urgent pointer */
};

#endif /* ! _HAVE_TCP_H */
