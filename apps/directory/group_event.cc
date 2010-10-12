#include "group_event.hh"

using namespace vigil::applications;

namespace vigil {

Group_name_event::Group_name_event(Directory::Group_Type t,
                                   const std::string& oname,
                                   const std::string& nname)
    : Event(static_get_name()), type(t), oldname(oname), newname(nname)
{ }

}
