/*
 * Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */
#include "principal_types.hh"
#include "pyrt/pyglue.hh"

using namespace std;
using namespace vigil;

namespace vigil {
namespace applications {
namespace directory {

const string NO_SUPPORT("NO");
const string READ_ONLY_SUPPORT("RO");
const string READ_WRITE_SUPPORT("RW");

const string AUTH_SIMPLE("simple_auth"); 
const string AUTHORIZED_CERT_FP("authorized_cert_fingerprint"); 

} /* directory */
} /* applications */
} /* vigil */

