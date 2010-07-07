/*

   p0f - ToS database
   ------------------

   A list of known and used ToS / priority combinations. Rare settings 
   actually describe the originating network (since specific ISPs tend
   to set those values for all outgoing traffic). More popular settings
   are just described per their RFC meaning.

   The field we examine is actually 8 bits in the following format:

   PPP TTTT Z
   |   |    `- "must be zero" (yeah, sure)
   |   `------ Type of Service
   `---------- Precedence bits (now used to denote priority)

   But all this is usually just called "ToS". The "must be zero"
   value is often, well, not zero, of course.

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

#ifndef _HAVE_TOS_H
#define _HAVE_TOS_H

#include "types.h"

struct tos_def {
  _u8 tos;
  const char* desc;
};


/* THIS LIST MUST BE SORTED FROM LOWEST TO HIGHEST ToS */

/* Candidates:

    1 Tiscali Denmark (must-be-zero!)
    3 InfoAve (must-be-zero!)
    5 AOL (must-be-zero!)
  200 Borlange Sweden
   96 Nextra
   28 Menta 
  192 techtelnet.net

 */

static struct tos_def tos[] = {
  {   2, "low cost" },				/* LC */
  {   4, "high reliability" },			/* HR */
  {   8, "low delay" },				/* LD */
  {  12, "DNA.FI / CTINETS" },			/* LD, HR */
  {  16, "high throughput" },			/* HT */
  {  32, "priority1" },				/* PRI1 */
  {  40, "UTFORS Sweden" },			/* PRI1, LD */
  {  64, "Tiscali Denmark" },			/* PRI2 */
  {  80, "Bredband Scandinavia" },		/* PRI2, HT */
  { 112, "Bonet Sweden" },			/* PRI3, HT */
  { 128, "Cable.BG / Teleca.SE" },		/* PRI4 */
  { 144, "IPTelecom / Alkar" },			/* PRI4, HT */
  { 244, "top priority" },			/* PRI7 */
  { 255, "Arcor IP" },				/* (bad) */
};

#define TOS_CNT (sizeof(tos) / sizeof(struct tos_def))

#endif /* ! _HAVE_TOS_H */
