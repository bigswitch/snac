/* Copyright 2008 (C) Nicira, Inc. */
/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */
#include "sepl_enforcer.hh"

#include <boost/bind.hpp>
#include <inttypes.h>

#include "assert.hh"
#include "bootstrap-complete.hh"
#include "cnode-result.hh"
#include "vlog.hh"

#define DEFAULT_FLOW_TIMEOUT  5
#define DEFAULT_NUM_PAIRS     5

#define SEPL_PROP_SECTION   "sepl"
#define ENFORCE_POLICY_VAR  "enforce_policy"

using namespace vigil::applications;
using namespace vigil::container;

namespace vigil {
namespace applications {

static Vlog_module lg("sepl_enforcer");

Sepl_enforcer::Action_set::Action_set()
    : types(Flow_action::MAX_ACTIONS, false),
      args(Flow_action::MAX_ACTIONS)
{}

Sepl_enforcer::Sepl_enforcer(const container::Context* c,
                             const xercesc::DOMNode*)
    : Classifier<Flow_expr, Flow_action>(),
      Component(c), tstorage(NULL), properties(NULL), stats(NULL),
      core(NULL), passive(false), most_secure(true), result(&data),
      actions(DEFAULT_NUM_PAIRS)
{ }

void
Sepl_enforcer::getInstance(const container::Context* ctxt,
                           Sepl_enforcer*& r)
{
    r = dynamic_cast<Sepl_enforcer*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(Sepl_enforcer).name())));
}

void
Sepl_enforcer::configure(const container::Configuration*)
{
    register_handler<Bootstrap_complete_event>
        (boost::bind(&Sepl_enforcer::handle_bootstrap, this, _1));
    register_handler<Flow_in_event>
        (boost::bind(&Sepl_enforcer::handle_flow, this, _1));
    clean_expired();
}


void
Sepl_enforcer::install()
{
    resolve(tstorage);
    resolve(stats);
    resolve(core);
}

Disposition
Sepl_enforcer::handle_bootstrap(const Event& e)
{
    configuration::Properties::Default_value_map default_val;
    default_val[ENFORCE_POLICY_VAR] = std::vector<configuration::Property>(1, configuration::Property(int64_t(1)));
    properties = new configuration::Properties(tstorage, SEPL_PROP_SECTION, default_val);
    update_passive();
    return CONTINUE;
}

void
Sepl_enforcer::update_passive()
{
    properties->load();
    passive = boost::get<int64_t>((*(properties->get_value(ENFORCE_POLICY_VAR)))[0].get_value()) == 0;
    if (!boost::get<0>(properties->add_callback(boost::bind(&Sepl_enforcer::update_passive, this)))) {
        VLOG_ERR(lg, "Could not add callback to update passive variable.  Defaulting to true.");
        passive = true;
    }
}

void
Sepl_enforcer::init_sepl_data(Flow_in_event& fi)
{
    data.fi = &fi;
    fi.active = false;
    data.role = Flow_expr::REQUEST;
    data.py_flow = NULL;
}

std::size_t
Sepl_enforcer::Flowhash::operator() (const Flow& flow) const
{
    HASH_NAMESPACE::hash<uint32_t> h;
    return (h(((uint32_t)flow.dl_src.hb_long())
              ^ ((uint32_t)flow.dl_dst.hb_long())
              ^ flow.dl_type ^ flow.nw_src ^ flow.nw_dst
              ^ flow.nw_proto ^ flow.tp_src ^ flow.tp_dst));
}

bool
Sepl_enforcer::Floweq::operator() (const Flow& a, const Flow& b) const
{
    if (a.dl_src.nb_long() != b.dl_src.nb_long() || a.dl_dst.nb_long() != b.dl_dst.nb_long())
        return false;
    else if (a.dl_type != b.dl_type)
        return false;
    else if (a.nw_src != b.nw_src || a.nw_dst != b.nw_dst)
        return false;
    else if (a.nw_proto != b.nw_proto)
        return false;
    else if (a.tp_src != b.tp_src || a.tp_dst != b.tp_dst)
        return false;
    return true;
}

void
Sepl_enforcer::clean_expired()
{
    timeval curtime = { 0, 0 };
    gettimeofday(&curtime, NULL);

    Flow_map::iterator rend = responses.end();
    for (Flow_map::iterator iter = responses.begin(); iter != rend;) {
        if (curtime.tv_sec >= iter->second) {
            responses.erase(iter++);
        } else {
            ++iter;
        }
    }

    timeval tv = { DEFAULT_FLOW_TIMEOUT * 2, 0 };
    post(boost::bind(&Sepl_enforcer::clean_expired, this), tv);
}

Disposition
Sepl_enforcer::handle_flow(const Event& e)
{
    Flow_in_event& fi =
        const_cast<Flow_in_event&>(assert_cast<const Flow_in_event&>(e));

    if (fi.flow.dl_dst.is_multicast() && !fi.flow.dl_dst.is_broadcast()) {
        stats->increment_allows();
        return CONTINUE;
    }

    init_sepl_data(fi);

    Flow_map::iterator iter = responses.find(fi.flow);
    if (iter != responses.end()) {
        if (fi.received.tv_sec <= iter->second)
            data.role = Flow_expr::RESPONSE;
        else
            responses.erase(iter);
    }

    check_destinations();

#ifdef TWISTED_ENABLED
    Py_XDECREF(data.py_flow);
#endif

    if (data.role == Flow_expr::REQUEST) {
        record_request(fi.flow, fi.received);
    }
    return CONTINUE;
}

void
Sepl_enforcer::check_destinations()
{
    const Connector& src(*(data.fi->source));
    const uint32_t n_susers = src.users.size();
    bool allowed_dst = false;

    data.dst_idx = 0;
    for (data.dst = data.fi->destinations.begin();
         data.dst != data.fi->destinations.end(); ++data.dst, ++data.dst_idx)
    {
        const Connector& dst(*(data.dst->connector));
        const uint32_t n_pairs = n_susers * dst.users.size();
        if (actions.size() < n_pairs) {
            actions.resize(n_pairs * 2);
        }
        data.suser_idx = 0;
        data.suser = src.users.begin();
        data.dst_current = false; // needs to be set for dst index
        std::vector<Action_set>::iterator pair_actions(actions.begin());
        for (; data.suser != src.users.end();
             ++data.suser, ++data.suser_idx)
        {
            data.src_current = false;
            data.duser = dst.users.begin();
            data.duser_idx = 0;
            for (; data.duser != dst.users.end();
                 ++data.duser, ++data.duser_idx, ++pair_actions)
            {
                data.dst_current = false;
                pair_actions->types.assign(Flow_action::MAX_ACTIONS, false);
                std::vector<std::vector<Flow_action::Arg_union> >::iterator iter;
                for (iter = pair_actions->args.begin();
                     iter != pair_actions->args.end(); ++iter)
                {
                    iter->clear();
                }
                get_actions(pair_actions);
            }
        }
        data.src_current = true; // doesn't need to be set
        bool terminate = process_actions();
        stats->record_stats(data.fi->flow.dl_src, data.dst->rules);
        if (terminate) {
            if (lg.is_dbg_enabled()) {
                os << "] " << data.fi->flow;
                lg.dbg("POLICY FN (consuming flow) %s to %llx:%"PRIu16"", os.str().c_str(),
                       data.dst->connector->location & 0xffffffffffffULL,
                       (uint16_t)(data.dst->connector->location >> 48));
                os.str("");
            }
            return;
        } else if (data.dst->allowed) {
            allowed_dst = true;
        }
    }
    if (!allowed_dst) {
        VLOG_DBG(lg, "No destinations to route to.  Denying flow.");
        stats->increment_denies();
        if (passive) {
            data.fi->active = true;
        }
    } else {
        stats->increment_allows();
        data.fi->active = true;
    }
}


void
Sepl_enforcer::get_actions(const std::vector<Action_set>::iterator& action)
{
    get_rules(result);
    const Rule<Flow_expr, Flow_action> *match(result.next());
    if (match != NULL) {
        action->pri = match->priority;
        do {
            const uint32_t atype = match->action.type;
            action->types[atype] = true;
            if (atype >= Flow_action::ARG_ACTION) {
                action->args[atype].push_back(match->action.arg);
            }
            data.dst->rules.insert(match->expr.global_id);
            match = result.next();
        } while (match != NULL && match->priority == action->pri);
    } else if (lg.is_warn_enabled()) {
        os << data.fi->flow;
        lg.warn("No matching rule found %s", os.str().c_str()); // specify
        os.str("");
    }
    result.clear();
}


bool
Sepl_enforcer::process_actions()
{
    if (lg.is_dbg_enabled()) {
        os << "[";
    }

    bool allow, waypoint, deny;
    int32_t cfn, pyfn;
    uint32_t fn_pri = 0;

    allow = waypoint = deny = false;
    cfn = pyfn = -1;

    uint32_t n_pairs = data.fi->source->users.size() * data.dst->connector->users.size();
    std::vector<Action_set>::iterator pair_actions(actions.begin());

    for (uint32_t i = 0; i < n_pairs; ++i, ++pair_actions) {
        const std::vector<bool>& action_types(pair_actions->types);
        if (most_secure) {
            if (action_types[Flow_action::DENY]) {
                deny = true;
            } else if (action_types[Flow_action::WAYPOINT]) {
                waypoint = true;
                args_t& a(pair_actions->args[Flow_action::WAYPOINT]);
                args_t::const_iterator aiter(a.begin());
                for (; aiter != a.end(); ++aiter) {
                    const std::vector<uint64_t>& points(boost::get<std::vector<uint64_t> >(*aiter));
                    data.dst->waypoints.insert(data.dst->waypoints.end(), points.begin(), points.end());
                }
            } else if (action_types[Flow_action::ALLOW]) {
                allow = true;
            } else if (action_types[Flow_action::C_FUNC]) {
                if ((cfn == -1 && pyfn == -1) || pair_actions->pri < fn_pri) {
                    cfn = i;
                    pyfn = -1;
                    fn_pri = pair_actions->pri;
                }
            } else if (action_types[Flow_action::PY_FUNC]) {
                if ((cfn == -1 && pyfn == -1) || pair_actions->pri < fn_pri) {
                    cfn = -1;
                    pyfn = i;
                    fn_pri = pair_actions->pri;
                }
            }
        } else {
            if (action_types[Flow_action::ALLOW]) {
                allow = true;
            } else if (action_types[Flow_action::WAYPOINT]) {
                waypoint = true;
                args_t& a(pair_actions->args[Flow_action::WAYPOINT]);
                args_t::const_iterator aiter(a.begin());
                for (; aiter != a.end(); ++aiter) {
                    const std::vector<uint64_t>& points(boost::get<std::vector<uint64_t> >(*aiter));
                    data.dst->waypoints.insert(data.dst->waypoints.end(), points.begin(), points.end());
                }
            } else if (action_types[Flow_action::DENY]) {
                deny = true;
            } else if (action_types[Flow_action::C_FUNC]) {
                if ((cfn == -1 && pyfn == -1) || pair_actions->pri < fn_pri) {
                    cfn = i;
                    pyfn = -1;
                    fn_pri = pair_actions->pri;
                }
            } else if (action_types[Flow_action::PY_FUNC]) {
                if ((cfn == -1 && pyfn == -1) || pair_actions->pri < fn_pri) {
                    cfn = -1;
                    pyfn = i;
                    fn_pri = pair_actions->pri;
                }
            }
        }

        if (lg.is_dbg_enabled()) {
            hash_set<uint32_t>::const_iterator id(data.dst->rules.begin());
            for (; id != data.dst->rules.end(); ++id) {
                os << *id << ",";
            }
        }
    }

    if (!(allow || waypoint)) {
        data.dst->allowed = false;
        if (!deny) {
            if (cfn != -1) {
                data.fi->active = false;
                data.fi->fn_applied = true;
                const Flow_fn_map::Flow_fn& fn =
                    boost::get<Flow_fn_map::Flow_fn>(actions[cfn].
                                                     args[Flow_action::C_FUNC].
                                                     front());
                fn(*data.fi);
                return true;
            } else if (pyfn != -1) {
                data.fi->active = false;
                data.fi->fn_applied = true;
                PyObject *fn =
                    boost::get<PyObject *>(actions[pyfn].
                                           args[Flow_action::PY_FUNC].
                                           front());
                call_python_action(fn);
                return true;
            }
        }
        if (lg.is_dbg_enabled()) {
            os << "] " << data.fi->flow;
            lg.dbg("DENY %s to %llx:%"PRIu16"", os.str().c_str(),
                   data.dst->connector->location & 0xffffffffffffULL,
                   (uint16_t)(data.dst->connector->location >> 48));
            os.str("");
        }
        data.dst->allowed = false;
    } else {
        if (lg.is_dbg_enabled()) {
            os.str("");
        }
        // choose least restrictive among matching
        if (allow) {
            data.dst->waypoints.clear();
        }
    }
    return false;
}


void
Sepl_enforcer::record_request(const Flow& request,
                              const timeval& curtime)
{
    if (request.dl_dst.is_broadcast()) {
        return;
    }
    Flow flow(request);
    flow.dl_src = request.dl_dst;
    flow.dl_dst = request.dl_src;
    flow.nw_src = request.nw_dst;
    flow.nw_dst = request.nw_src;
    flow.tp_src = request.tp_dst;
    flow.tp_dst = request.tp_src;
    responses[flow] = curtime.tv_sec + DEFAULT_FLOW_TIMEOUT;
}

} // namespace applications

static
bool
in_groups(const std::vector<uint32_t>& groups, uint32_t val)
{
    for (std::vector<uint32_t>::const_iterator iter = groups.begin();
         iter != groups.end(); ++iter)
    {
        if (val == *iter)
            return true;
        else if (val < *iter)
            return false;
    }

    return false;
}

template<>
bool
get_field<Flow_expr, Sepl_data>(uint32_t field, const Sepl_data& data,
                                uint32_t idx, uint32_t& value)
{
    uint64_t v;

    // if not a group predicate, no value for idx greater than 0
    if (idx > 0 && ((field < Flow_expr::HGROUPSRC)
                    || (field > Flow_expr::UGROUPDST && field < Flow_expr::ADDRGROUPSRC)
                    || (field > Flow_expr::ADDRGROUPDST)))
    {
        return false;
    }

    switch (field) {
    case Flow_expr::LOCSRC:
        value = data.fi->source->ap;
        return true;
    case Flow_expr::LOCDST:
        value = data.dst->connector->ap;
        return true;
    case Flow_expr::HSRC:
        value = data.fi->source->host;
        return true;
    case Flow_expr::HDST:
        value = data.dst->connector->host;
        return true;
    case Flow_expr::USRC:
        value = data.suser->user;
        return true;
    case Flow_expr::UDST:
        value = data.duser->user;
        return true;
    case Flow_expr::CONN_ROLE:
        value = data.role;
        return true;
    case Flow_expr::HGROUPSRC:
        if (idx >= data.fi->source->hostgroups.size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.fi->source->hostgroups[idx];
        }
        return true;
    case Flow_expr::HGROUPDST:
        if (idx >= data.dst->connector->hostgroups.size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.dst->connector->hostgroups[idx];
        }
        return true;
    case Flow_expr::UGROUPSRC:
        if (idx >= data.suser->groups.size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.suser->groups[idx];
        }
        return true;
    case Flow_expr::UGROUPDST:
        if (idx >= data.duser->groups.size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.duser->groups[idx];
        }
        return true;
    case Flow_expr::DLVLAN:
        value = data.fi->flow.dl_vlan;
        return true;
    case Flow_expr::DLSRC:
        v = data.fi->flow.dl_src.nb_long();
        value = ((uint32_t) v) ^ (v >> 32);
        return true;
    case Flow_expr::DLDST:
        v = data.fi->flow.dl_dst.nb_long();
        value = ((uint32_t) v) ^ (v >> 32);
        return true;
    case Flow_expr::DLTYPE:
        value = data.fi->flow.dl_type;
        return true;
    case Flow_expr::NWSRC:
        value = data.fi->flow.nw_src;
        return true;
    case Flow_expr::NWDST:
        value = data.fi->flow.nw_dst;
        return true;
    case Flow_expr::NWPROTO:
        value = data.fi->flow.nw_proto;
        return true;
    case Flow_expr::TPSRC:
        value = data.fi->flow.tp_src;
        return true;
    case Flow_expr::TPDST:
        value = data.fi->flow.tp_dst;
        return true;
    case Flow_expr::ADDRGROUPSRC:
        if (idx >= data.fi->src_addr_groups->size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.fi->src_addr_groups->at(idx);
        }
        return true;
    case Flow_expr::ADDRGROUPDST:
        if (idx >= data.fi->dst_addr_groups->size()) {
            if (idx > 0)
                return false;
            value = 0;
        } else {
            value = data.fi->dst_addr_groups->at(idx);
        }
        return true;
    }

    VLOG_ERR(lg, "Classifier was split on field not retrievable from a Sepl_data.");

    // return true so that doesn't try to do ANY and look at all children
    value = 0;
    return true;
}


template<>
bool
matches(const Flow_expr& expr, const Sepl_data& data)
{
    const Connector& src = *data.fi->source;
    const Connector& dst = *(data.dst->connector);
    const Flow& flow = data.fi->flow;

    bool bad_result = false; // equality result signaling failed match
    int32_t t;

    std::vector<Flow_expr::Pred>::const_iterator end = expr.m_preds.end();
    for (std::vector<Flow_expr::Pred>::const_iterator iter = expr.m_preds.begin();
         iter != end; ++iter)
    {
        if (iter->type < 0) {
            t = -1 * iter->type;
            bad_result = true;
        } else {
            t = iter->type;
            // bad_result should already be set
        }

        switch (t) {
        case Flow_expr::LOCSRC:
            if (((uint32_t)(iter->val) == src.ap) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::LOCDST:
            if (((uint32_t)(iter->val) == dst.ap) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::HSRC:
            if (((uint32_t)(iter->val) == src.host) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::HDST:
            if (((uint32_t)(iter->val) == dst.host) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::USRC:
            if (((uint32_t)(iter->val) == data.suser->user) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::UDST:
            if (((uint32_t)(iter->val) == data.duser->user) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::CONN_ROLE:
            if (((Flow_expr::Conn_role_t) iter->val == data.role) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::HGROUPSRC:
            if (in_groups(src.hostgroups, iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::HGROUPDST:
            if (in_groups(dst.hostgroups, iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::UGROUPSRC:
            if (in_groups(data.suser->groups, iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::UGROUPDST:
            if (in_groups(data.duser->groups, iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::DLVLAN:
            if (((uint32_t)(iter->val) == flow.dl_vlan) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::DLSRC:
            if ((iter->val == flow.dl_src.nb_long()) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::DLDST:
            if ((iter->val == flow.dl_dst.nb_long()) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::DLTYPE:
            if (((uint32_t)(iter->val) == flow.dl_type) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::NWSRC:
            if (((uint32_t)(iter->val) == flow.nw_src) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::NWDST:
            if (((uint32_t)(iter->val) == flow.nw_dst) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::NWPROTO:
            if (((uint32_t)(iter->val) == flow.nw_proto) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::TPSRC:
            if (((uint32_t)(iter->val) == flow.tp_src) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::TPDST:
            if (((uint32_t)(iter->val) == flow.tp_dst) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::ADDRGROUPSRC:
            if (in_groups(*(data.fi->src_addr_groups), iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::ADDRGROUPDST:
            if (in_groups(*(data.fi->dst_addr_groups), iter->val) == bad_result) {
                return false;
            }
            break;
        case Flow_expr::SUBNETSRC:
            if ((((uint32_t)(iter->val >> 32) & flow.nw_src)
                 == (uint32_t)iter->val) == bad_result)
            {
                return false;
            }
            break;
        case Flow_expr::SUBNETDST:
            if ((((uint32_t)(iter->val >> 32) & flow.nw_dst)
                 == (uint32_t)iter->val) == bad_result)
            {
                return false;
            }
            break;
        default:
            VLOG_ERR(lg, "Rule defined on field not retrievable from a Sepl_data.");
            return false;
        }
    }

    if (expr.m_fn == NULL) {
        return true;
    }

    return const_cast<Sepl_data&>(data).call_python_pred(expr.m_fn);
}

} // namespace vigil

REGISTER_COMPONENT(Simple_component_factory<Sepl_enforcer>,
                   Sepl_enforcer);

