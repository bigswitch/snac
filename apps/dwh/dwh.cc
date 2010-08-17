/* Copyright 2008 (C) Nicira, Inc. */
#include <cstdio>
#include <fstream>
#include <iostream>
#include <list>

#include <boost/lexical_cast.hpp>
#include <xercesc/dom/DOM.hpp>

#include "assert.hh"
#include "component.hh"
#include "flow.hh"
#include "flow-mod-event.hh"
#include "flow-expired.hh"
#include "hash_map.hh"
#include "netinet++/ethernetaddr.hh"
#include "ndb/ndb.hh"
#include "packet-in.hh"
#include "threads/cooperative.hh"
#include "threads/native-pool.hh"
#include "timeval.hh"
#include "vlog.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;

namespace {

Vlog_module lg("dwh");

class TableExtractor;
typedef boost::shared_ptr<TableExtractor> TableExtractor_ptr; 

string replace(const string& s, const char c, const string& n) {
    string v = s;
    while (true) {
        string::size_type p = v.find(c, 0);
        if (p == string::npos) {
            return v;
        }

        v = v.replace(p, 1, n);
    }
};

ostream& operator<<(ostream &os, const Op::KeyValue& kv) {
    switch (kv.type) {
    case Op::NONE:
        os << "\\N";
        break;

    case Op::INT:
        os << boost::lexical_cast<string>(kv.int_val);
        break;

    case Op::DOUBLE:
        os << boost::lexical_cast<string>(kv.double_val);
        break;

    case Op::TEXT:
        // Escape if necessary, optimized for case not requiring
        // escaping.
        os << "\"";
        if (kv.text_val.find(',', 0) != string::npos ||
            kv.text_val.find('\b', 0) != string::npos ||
            kv.text_val.find('\n', 0) != string::npos ||
            kv.text_val.find('\r', 0) != string::npos ||
            kv.text_val.find('\t', 0) != string::npos) {

            
            string v = replace(kv.text_val, ',', "\\,");
            v = replace(v, '\b', "\\b");
            v = replace(v, '\n', "\\n");
            v = replace(v, '\r', "\\r");
            v = replace(v, '\t', "\\t");
            os << v;
        } else {
            os << kv.text_val;
        }
        os << "\"";
        break;

    case Op::BLOB:
        {
            os << "\"";
            const uint8_t* end = kv.blob_val + kv.blob_len;
            for (uint8_t* i = kv.blob_val; i != end; ++i) {
                if (*i == '\0') {
                    os << "\\0";
                } else if (*i == ',') { 
                    os << "\\,";
                } else if (*i == '\\') { 
                    os << "\\\\";
                } else if (*i == '"') {
                    os << "\\\"";
                } else if (*i == '\n') {
                    os << "\\n";
                } else if (*i == '\t') {
                    os << "\\t";
                } else {
                    os << *i;
                }
            }
            os << "\"";
        }

        break;
    }
    
    return os;
};

class TableExtractor {
public:
    TableExtractor(const string& table_, const NDB::ColumnDef_List& columns_)
        : table(table_), columns(columns_), serial(0) { }
    
    ~TableExtractor() {
        if (of.is_open()) {
            of.close();
        }
    }
    
    bool log(const struct timeval& t, 
             const Op::Row& row, 
             void*) {
        if (!of.is_open()) {
            of.open(string(PKGLOCALSTATEDIR"/" + table + ".sql").c_str(), 
                    ios_base::trunc);
            
            // XXX: set exception mask
            
            // Write a header defining the order of columns.
            of << "ID,CREATED_DT";
            
            for (NDB::ColumnDef_List::const_iterator i = columns.begin(); 
                 i != columns.end(); ++i) {
                of << "," + (*i).first;
            }
            
            of << "\n";
            
            oldest = newest = t;
            
        } else {    
            if (oldest > t) { 
                oldest = t;
            }
            if (newest < t) {
                newest = t;
            }
        }
        
        // ID, CREATED_DT, ...
        snprintf(f, sizeof f, ",%ld%06ld", t.tv_sec, t.tv_usec);
        of << "\\N" << f;
        
        // ... and then the rest, in the pre-defined order. Note: this is
        // slight waste of CPU cycles, but optimizing this would require
        // changing the API semantics.
        for (NDB::ColumnDef_List::const_iterator i = columns.begin(); 
             i != columns.end(); ++i) {
            bool found = false;
            for (list<Op::KeyValue_ptr>::const_iterator j = row.begin(); 
                 j != row.end(); ++j) {
                if ((*j)->key == (*i).first) {
                    of << ',' << **j;
                    found = true;
                    break;
                }
            }
            if (!found) {
                of << ",\\N";
            }
        }
                
        of << "\n";
        return true;
    }

    bool flush(void*) {
        /* If something has been written, move the file. */
        if (of.is_open()) {
            of.close();
            
            if (rename(string(PKGLOCALSTATEDIR"/" + table + ".sql").c_str(), 
                       (string(PKGLOCALSTATEDIR"/export/") + table + "-" +
                        convert_time(oldest) + "-" + convert_time(newest) + "-" +
                        boost::lexical_cast<string>(serial) + ".sql").c_str()) == -1) {
                lg.err("Unable to move an export file to export/.");
            }
            
            ++serial;
            return true;
        } else {
            return false;
        }
    }

    string convert_time(const struct timeval& tv) {
        char ts1[15];    
        char ts2[7];    
        time_t t1 = tv.tv_sec;
        struct tm t2;
        
        strftime(ts1, sizeof ts1, "%Y%m%d%H%M%S", localtime_r(&t1, &t2));
        snprintf(ts2, sizeof ts2, "%06ld", tv.tv_usec);
        
        return string(ts1) + string(ts2);
    }

    /* Table name */
    const string table;

    /* Columns */
    const NDB::ColumnDef_List columns;
    
    /* File being written */
    ofstream of;

    /* Oldest and newest entries in the current file */
    struct timeval oldest, newest;

    /* File counter */
    int serial;

    /* Formatting buffer */
    char f[21];    
};

inline
Op::KeyValue_ptr define_column(const int wildcards, const int mask, 
                               const string& column, const int64_t& value) {
    return wildcards & mask ?
            Op::KeyValue_ptr(new Op::KeyValue(column)) :
            Op::KeyValue_ptr(new Op::KeyValue(column, value));
}

static uint32_t make_netmask(int n_wild_bits)
{
    n_wild_bits &= (1u << OFPFW_NW_SRC_BITS) - 1;
    return n_wild_bits < 32 ? htonl(~((1u << n_wild_bits) - 1)) : 0;
}

static
void define_nw_mask_column(int64_t addr, int64_t addr_mask,
                           const string& column_pfx, Op::Row& row) {
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue(column_pfx, addr)));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue(column_pfx + "_MASK",
                                                    addr_mask)));
}

template <typename T>
Op::Row transform(const T&);

template <>
Op::Row transform(const Packet_in_event& pie) {
    Op::Row row;

    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "O")));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("DP_ID", (int64_t)pie.datapath_id.as_host())));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("PORT_ID", (int64_t)pie.in_port)));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("REASON", (int64_t)pie.reason)));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("BUFFER", 
                                                    pie.get_buffer()->size(), 
                                                    pie.get_buffer()->data())));
    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TOTAL_LEN", (int64_t)pie.total_len)));
    
    return row;
}

template <>
Op::Row transform(const Flow_mod_event& fme) {
    const ofp_match* om = fme.get_flow();
    const ofp_flow_mod* ofm = fme.get_flow_mod();
    const uint32_t w = ntohl(om->wildcards);
    Op::Row row;

    switch (ofm->command) {
    case OFPFC_ADD:
        row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "O")));
        break;

    case OFPFC_DELETE: 
        // TODO: not implemented. 
        break;

    case OFPFC_DELETE_STRICT:
        row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "C")));
        break;
    }
    
    row.push_back(define_column(0, 0, "DP_ID", fme.datapath_id.as_host()));
    row.push_back(define_column(w, OFPFW_IN_PORT, "PORT_ID", ntohs(om->in_port)));
    row.push_back(define_column(0, 0, "ETH_VLAN", ntohs(om->dl_vlan)));
    row.push_back(define_column(0, 0, "ETH_TYPE", ntohs(om->dl_type)));
    const ethernetaddr srcaddr(om->dl_src);
    row.push_back(define_column(w, OFPFW_DL_SRC, "SOURCE_MAC", srcaddr.hb_long()));
    const ethernetaddr dstaddr(om->dl_dst);
    row.push_back(define_column(w, OFPFW_DL_DST, "DESTINATION_MAC", dstaddr.hb_long()));
    const uint32_t srcaddr_mask(make_netmask(w >> OFPFW_NW_SRC_SHIFT));
    define_nw_mask_column(ntohl(om->nw_src), srcaddr_mask, "SOURCE_IP", row);
    const uint32_t dstaddr_mask(make_netmask(w >> OFPFW_NW_DST_SHIFT));
    define_nw_mask_column(ntohl(om->nw_dst), dstaddr_mask, "DESTINATION_IP", row);
    row.push_back(define_column(w, OFPFW_NW_PROTO, "PROTOCOL_ID", om->nw_proto));
    row.push_back(define_column(w, OFPFW_TP_SRC, "SOURCE_PORT", ntohs(om->tp_src)));
    row.push_back(define_column(w, OFPFW_TP_DST, "DESTINATION_PORT", ntohs(om->tp_dst)));
    // May want to add "OUT_PORT" argument
    row.push_back(define_column(0, 0, "DURATION", 0));
    row.push_back(define_column(0, 0, "PACKET_COUNT", 0));
    row.push_back(define_column(0, 0, "BYTE_COUNT", 0));

    return row;
}

template <>
Op::Row transform(const Flow_expired_event& fee) {
    const struct ofp_match* om = fee.get_flow();
    const struct ofp_flow_expired* ofe = fee.get_flow_expired();
    uint32_t w = ntohl(om->wildcards);
    Op::Row row;

    row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "C")));
    row.push_back(define_column(0, 0, "DP_ID", fee.datapath_id.as_host()));
    row.push_back(define_column(w, OFPFW_IN_PORT, "PORT_ID", ntohs(om->in_port)));
    row.push_back(define_column(0, 0, "ETH_VLAN", ntohs(om->dl_vlan)));
    row.push_back(define_column(0, 0, "ETH_TYPE", ntohs(om->dl_type)));
    const ethernetaddr srcaddr(om->dl_src);
    row.push_back(define_column(w, OFPFW_DL_SRC, "SOURCE_MAC", srcaddr.hb_long()));
    const ethernetaddr dstaddr(om->dl_dst);
    row.push_back(define_column(w, OFPFW_DL_DST, "DESTINATION_MAC", dstaddr.hb_long()));
    const uint32_t srcaddr_mask(make_netmask(w >> OFPFW_NW_SRC_SHIFT));
    define_nw_mask_column(ntohl(om->nw_src), srcaddr_mask, "SOURCE_IP", row);
    const uint32_t dstaddr_mask(make_netmask(w >> OFPFW_NW_DST_SHIFT));
    define_nw_mask_column(ntohl(om->nw_dst), dstaddr_mask, "DESTINATION_IP", row);
    row.push_back(define_column(w, OFPFW_NW_PROTO, "PROTOCOL_ID", om->nw_proto));
    row.push_back(define_column(w, OFPFW_TP_SRC, "SOURCE_PORT", ntohs(om->tp_src)));
    row.push_back(define_column(w, OFPFW_TP_DST, "DESTINATION_PORT", ntohs(om->tp_dst)));
    row.push_back(define_column(0, 0, "DURATION", ofe->duration));
    row.push_back(define_column(0, 0, "PACKET_COUNT", ofe->packet_count));
    row.push_back(define_column(0, 0, "BYTE_COUNT", ofe->byte_count));
    
    return row;
}

template <typename T>
class EventExtractor {
public:
    EventExtractor(NDB* ndb_, 
                   TableExtractor* te_,
                   Native_thread_pool<bool, void>* pool_)
        : ndb(ndb_), te(te_), pool(pool_) { }
    
    Disposition
    handle_event(const Event& e) {
        const Op::Row row = transform(assert_cast<const T&>(e));
        const struct timeval tv = do_gettimeofday();        
        pool->execute(boost::bind(&TableExtractor::log, te, tv, row, _1), 0);
        
        // Pass the event for the next handler.
        return CONTINUE;
    }

    void enable_sync() {
        fsm.start(boost::bind(&EventExtractor::sync, this));
    }

private:
    NDB* ndb;
    TableExtractor* te;
    Native_thread_pool<bool, void>* pool;
    Auto_fsm fsm;

    void sync() {
        pool->execute(boost::bind(&TableExtractor::flush, te, _1), 0);
        co_timer_wait(do_gettimeofday() + ndb->get_commit_period(), NULL);
        ndb->get_commit_change_condition()->wait();
        co_fsm_block();
    }
};

class DWH
    : public NDB, public Component {
public:
    DWH(const Context* c,
        const xercesc::DOMNode*) 
        : Component(c) {
    }
    
    void configure(const Configuration*) {
        /* Dump network database */
        resolve(ndb);
        ndb->connect_extractor(this);

        /* Dump flow and flow setup events.
         * 
         * We register our handlers at priority 0, the highest priority available,
         * so that we see all flow events before they can be dropped. */
        p = new Native_thread_pool<bool, void>();

        NDB::ColumnDef_List fc;
        fc.push_back(make_pair("TYPE", Op::TEXT));
        fc.push_back(make_pair("DP_ID", Op::INT));
        fc.push_back(make_pair("PORT_ID", Op::INT));
        fc.push_back(make_pair("ETH_VLAN", Op::INT));
        fc.push_back(make_pair("ETH_TYPE", Op::INT));
        fc.push_back(make_pair("SOURCE_MAC", Op::INT));
        fc.push_back(make_pair("DESTINATION_MAC", Op::INT));
        fc.push_back(make_pair("SOURCE_IP", Op::INT));
        fc.push_back(make_pair("DESTINATION_IP", Op::INT));
        fc.push_back(make_pair("PROTOCOL_ID", Op::INT));
        fc.push_back(make_pair("SOURCE_PORT", Op::INT));
        fc.push_back(make_pair("DESTINATION_PORT", Op::INT));
        fc.push_back(make_pair("DURATION", Op::INT));
        fc.push_back(make_pair("PACKET_COUNT", Op::INT));
        fc.push_back(make_pair("BYTE_COUNT", Op::INT));
        
        TableExtractor* te = new TableExtractor("FLOW", fc);
        EventExtractor<Flow_mod_event>* fme = 
            new EventExtractor<Flow_mod_event>(ndb, te, p);
        EventExtractor<Flow_expired_event>* fee = 
            new EventExtractor<Flow_expired_event>(ndb, te, p);    
        fme->enable_sync();
        
        NDB::ColumnDef_List fsc;
        fsc.push_back(make_pair("TYPE", Op::TEXT));
        fsc.push_back(make_pair("DP_ID", Op::INT));
        fsc.push_back(make_pair("PORT_ID", Op::INT));
        fsc.push_back(make_pair("REASON", Op::INT));
        fsc.push_back(make_pair("BUFFER", Op::BLOB));
        fsc.push_back(make_pair("TOTAL_LEN", Op::INT));
        
        te = new TableExtractor("FLOW_SETUP", fsc);
        EventExtractor<Packet_in_event>* fse = 
            new EventExtractor<Packet_in_event>(ndb, te, p);
        fse->enable_sync();

        register_handler<Flow_mod_event>
            (boost::bind(&EventExtractor<Flow_mod_event>::handle_event, fme, _1));
        register_handler<Flow_expired_event>
            (boost::bind(&EventExtractor<Flow_expired_event>::handle_event,  fee, _1));
        register_handler<Packet_in_event>
            (boost::bind(&EventExtractor<Packet_in_event>::handle_event, fse, _1));
    }

    void install() {
        p->add_worker((void*)1, 0);
    }

    OpStatus init(const NDB::Callback& = 0) { return OK; }

    OpStatus create_table(const string& table,
                          const NDB::ColumnDef_List& columns_,
                          const NDB::IndexDef_List& indices,
                          const NDB::Callback& f = 0) {
        NDB::ColumnDef_List columns = columns_;
        columns.push_front(make_pair("TYPE", Op::TEXT));
        tables[table] = TableExtractor_ptr(new TableExtractor(table, columns));
        
        std::list<Op::KeyValue_ptr> row;
        row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "C")));
        tables[table]->log(do_gettimeofday(), row, 0);
        return OK;
    }
    
    OpStatus drop_table(const string& table, const NDB::Callback& = 0) {
        tables.erase(table);
        return OK;
    }
    
    OpStatus execute(const list<boost::shared_ptr<GetOp> >&,
                     const NDB::Callback& = 0)  {
        return OK;
    }
    
    OpStatus execute(const list<boost::shared_ptr<PutOp> >& q,
                     const list<boost::shared_ptr<GetOp> >& d,
                     const NDB::Callback& f = 0) {
        for (list<boost::shared_ptr<PutOp> >::const_iterator i = q.begin(); 
             i != q.end(); ++i) {
            boost::shared_ptr<PutOp> put = *i;        
            if (put->get_replace().get()) {
                std::list<Op::KeyValue_ptr> row;
                row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "C")));
                row.insert(row.end(), put->get_replace()->begin(), 
                           put->get_replace()->end());
                tables[put->get_table()]->log(do_gettimeofday(), row, 0); // XXX
            }
            
            if (put->get_row().get()) {
                std::list<Op::KeyValue_ptr> row;
                row.push_back(Op::KeyValue_ptr(new Op::KeyValue("TYPE", "O")));
                row.insert(row.end(), put->get_row()->begin(), 
                           put->get_row()->end());
                tables[put->get_table()]->log(do_gettimeofday(), row, 0); /// XXX
            }
        }

        return OK;
    }

    OpStatus sync(const NDB::Callback& = 0) {
        for (TableExtractor_map::iterator i = tables.begin(); 
             i != tables.end(); ++i) {
            (*i).second->flush(0);
        }

        return OK;
    }

    OpStatus connect_extractor(NDB*) {
        return OK; 
    } 

private:
    /* Defined tables */
    typedef vigil::hash_map<string, TableExtractor_ptr> TableExtractor_map;
    TableExtractor_map tables;

    NDB* ndb;
    Native_thread_pool<bool, void>* p;
};

REGISTER_COMPONENT(container::Simple_component_factory<DWH>, DWH);

} // unnamed namespace
