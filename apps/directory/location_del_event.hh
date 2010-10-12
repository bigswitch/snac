#ifndef LOCATION_DEL_EVENT_HH
#define LOCATION_DEL_EVENT_HH 1

#include <boost/noncopyable.hpp>
#include <string>

#include "event.hh"
#include "netinet++/datapathid.hh"

/*
 * Location delete event.
 */

namespace vigil {

struct Location_delete_event
    : public Event,
      boost::noncopyable
{
    Location_delete_event(const std::string&, const std::string&,
                          const datapathid&, uint16_t);

    // -- only for use within python
    Location_delete_event() : Event(static_get_name()) { }

    static const Event_name static_get_name() {
        return "Location_delete_event";
    }

    std::string   oldname;
    std::string   newname;
    datapathid    dpid;
    uint16_t      port;
};

} // namespace vigil

#endif /* location_del_event.hh */
