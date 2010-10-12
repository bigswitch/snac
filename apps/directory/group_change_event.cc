#include "group_change_event.hh"

using namespace vigil::applications;

namespace vigil {

Group_change_event::Group_change_event(Directory::Group_Type gtype,
                                       const std::string& gname,
                                       Change_Type ctype,
                                       const std::string& cname)
    : Event(static_get_name()), type(gtype), group_name(gname),
      change_type(ctype), change_name(cname)
{ }

}
