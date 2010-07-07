/*

   p0f - MTU database
   ------------------

   A list of known and used MTUs. Note: MSS is MTU-40 on a sane system.

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

#ifndef _HAVE_MTU_H
#define _HAVE_MTU_H

#include "types.h"

struct mtu_def {
  _u16 mtu;
  const char* dev;
};


/* THIS LIST MUST BE SORTED FROM LOWEST TO HIGHEST MTU */

static struct mtu_def mtu[] = {
  {   256, "radio modem" },
  {   386, "ethernut" },
  {   552, "SLIP line / encap ppp" },
  {   576, "sometimes modem" },
  {  1280, "gif tunnel" },
  {  1300, "PIX, SMC, sometimes wireless" },
  {  1362, "sometimes DSL (1)" },
  {  1372, "cable modem" },
  {  1400, "(Google/AOL)" }, 	/* To be investigated */
  {  1415, "sometimes wireless" },
  {  1420, "GPRS, T1, FreeS/WAN" },
  {  1423, "sometimes cable" },
  {  1440, "sometimes DSL (2)" },
  {  1442, "IPIP tunnel" },
  {  1450, "vtun" },
  {  1452, "sometimes DSL (3)" },
  {  1454, "sometimes DSL (4)" },
  {  1456, "ISDN ppp" },
  {  1458, "BT DSL (?)" },
  {  1462, "sometimes DSL (5)" },
  {  1470, "(Google 2)" },
  {  1476, "IPSec/GRE" },
  {  1480, "IPv6/IPIP" },
  {  1492, "pppoe (DSL)" },
  {  1496, "vLAN" },
  {  1500, "ethernet/modem" },
  {  1656, "Ericsson HIS" },
  {  2024, "wireless/IrDA" },
  {  2048, "Cyclom X.25 WAN" },
  {  2250, "AiroNet wireless" },
  {  3924, "loopback" },
  {  4056, "token ring (1)" },
  {  4096, "Sangoma X.25 WAN" },
  {  4352, "FDDI" },
  {  4500, "token ring (2)" },
  {  9180, "FORE ATM" },
  { 16384, "sometimes loopback (1)" },
  { 16436, "sometimes loopback (2)" },
  { 18000, "token ring x4" },
};

#define MTU_CNT (sizeof(mtu) / sizeof(struct mtu_def))

#endif /* ! _HAVE_MTU_H */
