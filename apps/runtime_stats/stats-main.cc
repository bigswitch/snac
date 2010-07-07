/* Copyright 2008 (C) Nicira, Inc.
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
/*
 *
 */

#include <boost/bind.hpp>

#include "application-registry.hh"
#include "runtime-stats.hh"

namespace vigil 
{

using namespace std;    

static runtime_stats rs;

/* exposed for Python */
bool rotate()
{
    return rs.rotate();
}

bool get_packet_in_s(uint64_t swid, stats_snapshot& s_in)
{
    return rs.get_packet_in_s(swid, s_in);
}

bool get_packet_in_s5(uint64_t swid, stats_snapshot& s_in)
{
    return rs.get_packet_in_s5(swid, s_in);
}

bool get_packet_in_min(uint64_t swid, stats_snapshot& s_in)
{
    return rs.get_packet_in_min(swid, s_in);
}

int get_packet_in_s_history(uint64_t swid, std::list<float>& res)
{
    return rs.get_packet_in_s_history(swid, res);
}

int get_packet_in_s5_history(uint64_t swid, std::list<float>& res)
{
    return rs.get_packet_in_s5_history(swid, res);
}

int get_packet_in_min_history(uint64_t swid, std::list<float>& res)
{
    return rs.get_packet_in_min_history(swid, res);
}

void register_stats_handler()
{
    rs.register_callbacks();
}

Application app("runtime-stats", register_stats_handler);

} // vigil namespace
