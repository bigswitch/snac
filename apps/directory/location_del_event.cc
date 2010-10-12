#include "location_del_event.hh"

namespace vigil {

Location_delete_event::Location_delete_event(const std::string& oname,
                                             const std::string& nname,
                                             const datapathid& dp, uint16_t pt)
    : Event(static_get_name()), oldname(oname), newname(nname),
      dpid(dp), port(pt)
{ }

}
