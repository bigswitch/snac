#include "principal_event.hh"

using namespace vigil::applications;

namespace vigil {

Principal_name_event::Principal_name_event(Directory::Principal_Type t,
                                           const std::string& oname,
                                           const std::string& nname)
    : Event(static_get_name()), type(t), oldname(oname), newname(nname)
{ }

}
