/*

   p0f - type definitions
   ----------------------
  
   Short and portable names for various integer types.

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

#ifndef _HAVE_TYPES_H
#define _HAVE_TYPES_H

typedef unsigned char		_u8;
typedef unsigned short		_u16;
typedef unsigned int		_u32;

#ifdef WIN32
typedef unsigned __int64	_u64;
#else
typedef unsigned long long	_u64;
#endif /* ^WIN32 */

typedef signed char		_s8;
typedef signed short		_s16;
typedef signed int		_s32;

#ifdef WIN32
typedef signed __int64	_s64;
#else
typedef signed long long	_s64;
#endif /* ^WIN32 */

#endif /* ! _HAVE_TYPES_H */
