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
