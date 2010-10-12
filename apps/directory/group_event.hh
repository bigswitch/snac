#ifndef GROUP_NAME_EVENT_HH
#define GROUP_NAME_EVENT_HH 1

#include <boost/noncopyable.hpp>
#include <string>

#include "directory.hh"
#include "event.hh"

/*
 * Group name change event.
 */

namespace vigil {

struct Group_name_event
    : public Event,
      boost::noncopyable
{
    Group_name_event(applications::Directory::Group_Type type,
                     const std::string&, const std::string&);

    // -- only for use within python
    Group_name_event() : Event(static_get_name()) { }

    static const Event_name static_get_name() {
        return "Group_name_event";
    }

    applications::Directory::Group_Type type;
    std::string   oldname;
    std::string   newname;  // set to "" if group name deleted
};

} // namespace vigil

#endif /* group_event.hh */
