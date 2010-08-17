/* Copyright 2008 (C) Nicira, Inc. */
#ifndef SEPL_ENFORCER_HH
#define SEPL_ENFORCER_HH 1

#include "config.h"

#ifdef TWISTED_ENABLED
#include <Python.h>
#else
class PyObject;
#endif // TWISTED_ENABLED

#include <ctime>
#include <sstream>
#include <vector>

#include "authenticator/flow_in.hh"
#include "authenticator/flow_util.hh"
#include "classifier.hh"
#include "component.hh"
#include "configuration/properties.hh"
#include "flow.hh"
#include "hash_map.hh"
#include "hash_set.hh"
#include "sepl_stats.hh"

/*
 * Core SEPL.
 * Sepl_enforcer enforces the policy by listening for Flow_in_events, finding
 * matching rules, and dropping non-complying flows.
 *
 * More specific descriptions of individual classes below.
 *
 * WAYPOINTING NOT CURRENTLY SUPPORTED BY ROUTING.
 */

namespace vigil {
namespace applications {

/*
 * Data type passed to the classifier to find matching Flow_expr rules.
 */

struct Sepl_data {
    Flow_in_event *fi;
    Flow_in_event::DestinationList::iterator dst;
    //std::list<user_info>::const_iterator suser;
    //std::list<user_info>::const_iterator duser;
    uint32_t dst_idx;
    uint32_t suser_idx;
    uint32_t duser_idx;
    Flow_expr::Conn_role_t role;
    PyObject *py_flow;
    bool src_current;
    bool dst_current;

    bool call_python_pred(PyObject *fn);
};


/*
 * SEPL enforcing flow classifier.  Listens for Flow_in_events, finds matching
 * rules, and takes requested action.  For a single flow, a permission check is
 * performed for each src/dst user pair for each possible destination in the
 * flow.  For a given permission check, if 'most_secure' == true, the most
 * secure matching action is returned, else the least secure action is.  Per
 * destination, the least secure action returned by the user pair permission
 * checks is deemed the action for the destination as a whole.  Action
 * precedence order from most to least secure is DENY > WAYPOINT > ALLOW.
 *
 * A flow is logged as denied for each unpermitted destination and the
 * destination's allowed flag is marked as false.  If 'passive' == false and
 * all destinations are denied, the flow will be marked as inactive.  The flow
 * is also marked as active if a policy function is called - which right now is
 * called regardless of the value of 'passive'.
 *
 * C_FUNC and PY_FUNC are currently only called if they are the highest
 * priority matching function for a single destination (diff functions could be
 * returned based on user).  If  function is called, the remaining
 * destinations are not evaluated against the policy and thus are not marked as
 * denied (although the flow is marked as inactive).  
 */

class Sepl_enforcer
    : public Classifier<Flow_expr, Flow_action>, public container::Component
{

public:
    // Component state management methods
    Sepl_enforcer(const container::Context*, const json_object*);

    static void getInstance(const container::Context*, Sepl_enforcer*&);

    void configure(const container::Configuration*);
    void install();

    // set 'most_secure' value
    void set_most_secure(bool secure) { most_secure = secure; }

private:
    // hash fn for storing flows in a hash_map
    struct Flowhash {
        std::size_t operator() (const Flow& flow) const;
    };

    // eq fn for flows in hash_map
    struct Floweq {
        bool operator() (const Flow& a, const Flow& b) const;
    };


    typedef std::vector<Flow_action::Arg_union> args_t;
    typedef std::vector<args_t> argsvec_t;

    // struct to hold actions returned by permission checks
    struct Action_set {
        Action_set();
        ~Action_set() { };
        uint32_t pri;
        std::vector<bool> types;
        argsvec_t args;
    };

    typedef hash_map<Flow, time_t, Flowhash, Floweq> Flow_map;

    storage::Async_transactional_storage *tstorage;
    configuration::Properties *properties;
    Sepl_stats *stats;
    Flow_util *core;                  // core containing Flow_fn_map
    bool passive;                     // don't enforce SEPL if true
    bool most_secure;                 // return most secure action if true
    Flow_map responses;               // flow entries to consider as responses

    // datatypes used in flow handler.  declared here to avoid reallocating on
    // each flow
    Sepl_data data;
    Cnode_result<Flow_expr, Flow_action, Sepl_data> result;
    std::vector<Action_set> actions;
    std::ostringstream os;

    Disposition handle_bootstrap(const Event& e);
    void update_passive();
    Disposition handle_flow(const Event&);
    void init_sepl_data(Flow_in_event&);

    void check_destinations();

    // Get actions from classifier
    void get_actions(const std::vector<Action_set>::iterator&);

    // Resolve returned actions to take appropriate final action on flow
    bool process_actions();
    bool call_python_action(PyObject*);

    // Record flow as a request in the network in order to categorize responses
    void record_request(const Flow&,
                        const timeval& curtime);

    // clean expired flow request entries
    void clean_expired();

}; // class Sepl_enforcer


} // namespace applications

template<>
bool
get_field<Flow_expr, applications::Sepl_data>(uint32_t,
                                              const applications::Sepl_data&,
                                              uint32_t, uint32_t& val);
bool matches(const Flow_expr&, const applications::Sepl_data&);

} // namespace vigil

#endif // SEPL_ENFORCER_HH
