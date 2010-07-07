%{
#include  "capps/runtime-stats.hh"
using namespace vigil;
%}

%include "std_list.i"

namespace std {
%template(listf) list<float>;
};

struct stats_snapshot
{
    float last_s;
    float max_s;
    float avg_s;

    int   samples;
};

bool get_packet_in_s(uint64_t swid, stats_snapshot& s_in);
bool get_packet_in_s5(uint64_t swid, stats_snapshot& s_in);
bool get_packet_in_min(uint64_t swid, stats_snapshot& s_in);

bool get_packet_in_s_history(uint64_t swid, std::list<float>& res);
bool get_packet_in_s5_history(uint64_t swid, std::list<float>& res);
bool get_packet_in_min_history(uint64_t swid, std::list<float>& res);

