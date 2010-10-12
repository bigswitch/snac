#ifndef GROUP_CHANGE_EVENT_HH
#define GROUP_CHANGE_EVENT_HH 1

#include <boost/noncopyable.hpp>
#include <string>

#include "directory.hh"
#include "event.hh"

/*
 * Group definition change event.
 */

namespace vigil {

struct Group_change_event
    : public Event,
      boost::noncopyable
{
    enum Change_Type {
        ADD_PRINCIPAL,
        DEL_PRINCIPAL,
        ADD_SUBGROUP,
        DEL_SUBGROUP
    };

    Group_change_event(applications::Directory::Group_Type,
                       const std::string&, Change_Type, const std::string&);

    // -- only for use within python
    Group_change_event() : Event(static_get_name()) { }

    static const Event_name static_get_name() {
        return "Group_change_event";
    }

    applications::Directory::Group_Type type;     // Group's type
    std::string   group_name;                     // Group's name
    Change_Type   change_type;                    // Type of change
    std::string   change_name;                    // Entity added/deleted
};

} // namespace vigil

#endif /* group_change_event.hh */
