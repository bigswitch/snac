#ifndef PRINCIPAL_NAME_EVENT_HH
#define PRINCIPAL_NAME_EVENT_HH 1

#include <boost/noncopyable.hpp>
#include <string>

#include "directory.hh"
#include "event.hh"

/*
 * Principal name change event.
 */

namespace vigil {

struct Principal_name_event
    : public Event,
      boost::noncopyable
{
    Principal_name_event(applications::Directory::Principal_Type type,
                         const std::string&, const std::string&);

    // -- only for use within python
    Principal_name_event() : Event(static_get_name()) { }

    static const Event_name static_get_name() {
        return "Principal_name_event";
    }

    applications::Directory::Principal_Type type;
    std::string   oldname;
    std::string   newname;  // set to "" if principal name deleted
};

} // namespace vigil

#endif /* principal_event.hh */
