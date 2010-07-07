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
#ifndef SEPL_STATS_HH
#define SEPL_STATS_HH 1

#include <vector>

#include "component.hh"
#include "hash_map.hh"
#include "hash_set.hh"
#include "netinet++/ethernetaddr.hh"

namespace vigil {
namespace applications {

class Sepl_stats
    : public container::Component
{

public:
    struct EthHash {
        std::size_t operator() (const ethernetaddr& eth) const {
            return HASH_NAMESPACE::hash<uint64_t>()(eth.hb_long());
        }
    };

    typedef hash_set<ethernetaddr, EthHash> eth_hash_set;

    struct RuleStatsEntry {
        uint32_t count;
        bool record_senders;
        eth_hash_set sender_macs;
    };

    // Component state management methods
    Sepl_stats(const container::Context*, const xercesc::DOMNode*);

    static void getInstance(const container::Context*, Sepl_stats*&);

    void configure(const container::Configuration*) { }
    void install() { }

    void set_record_rule_senders(uint32_t, bool);
    void record_stats(const ethernetaddr&, const hash_set<uint32_t>&);
    void get_rule_stats(uint32_t, RuleStatsEntry& entry);
    void remove_entry(uint32_t);
    void clear_stats() { rules.clear(); n_allows = 0; n_denies = 0;}

    void increment_allows() { ++n_allows; }
    void increment_denies() { ++n_denies; }
    uint64_t get_allows() { return n_allows; }
    uint64_t get_denies() { return n_denies; }
    void clear_allows() { n_allows = 0; }
    void clear_denies() { n_denies = 0; }

private:
    typedef hash_map<uint32_t, RuleStatsEntry> RuleStats;

    RuleStats rules;
    uint64_t n_allows;
    uint64_t n_denies;
}; // class Sepl_stats


} // namespace applications
} // namespace vigil

#endif // SEPL_STATS_HH
