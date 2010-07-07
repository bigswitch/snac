#ifndef CONTROLLER_NDB_HH
#define CONTROLLER_NDB_HH 1

#include <list>
#include <string>
#include <boost/function.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/shared_ptr.hpp>

#include "component.hh"
#include "fnv_hash.hh"
#include "hash_map.hh"
#include "timeval.hh"
#include "threads/cooperative.hh"

namespace vigil {

class Co_cond;

class Op
{
public:
    enum ValueType { NONE, INT, DOUBLE, TEXT, BLOB };

    struct KeyValue {
        std::string key;
        ValueType type;
        std::string text_val;
        int64_t int_val;
        double double_val;
        int blob_len;
        uint8_t* blob_val;

        KeyValue(const std::string& k) :
            key(k), type(NONE), text_val(""), int_val(0), 
            double_val(0), blob_len(0), blob_val(0) { }

        KeyValue(const std::string& k, int64_t l) : 
            key(k), type(INT), text_val(""), int_val(l),
            double_val(0), blob_len(0), blob_val(0) { }

        KeyValue(const std::string& k, double d) : 
            key(k), type(DOUBLE), text_val(""), int_val(0), 
            double_val(d), blob_len(0), blob_val(0) { }

        KeyValue(const std::string& k, const std::string& s) : 
            key(k), type(TEXT), text_val(s), int_val(0), 
            double_val(0), blob_len(0), blob_val(0) { }

        KeyValue(const std::string& k, const int n, const uint8_t* b) : 
            key(k), type(BLOB), text_val(""), int_val(0), 
            double_val(0), blob_len(n) { 
            blob_val = new uint8_t[blob_len];
            if (!blob_val) {
                throw std::runtime_error("unable to allocate a blob buffer.");
            }
            if (blob_len) {
                ::memcpy(blob_val, b, blob_len);
            } 
        }

        ~KeyValue() {
            if (type == BLOB && blob_val) {
                delete blob_val;
            }
        }
        
        const std::string str() const { 
            switch (type) {
            case NONE:
                return key + " (null): NONE";
            case INT:
                return key + " (int): " + boost::lexical_cast<std::string>(int_val);
            case DOUBLE:
                return key + " (double): " + boost::lexical_cast<std::string>(double_val);
            case TEXT:
                return key + " (text): " + text_val;
            case BLOB:
                return key + " (blob): ";
            }
            
            // Never reached...
        }
    };

    typedef boost::shared_ptr<KeyValue> KeyValue_ptr;

    typedef std::list<KeyValue_ptr> Select;
    typedef boost::shared_ptr<Select> Select_ptr;

    typedef std::list<KeyValue_ptr> Row;
    typedef boost::shared_ptr<Row> Row_ptr;

    typedef std::list<Row_ptr> Results;
    typedef boost::shared_ptr<Results> Results_ptr;

    typedef boost::function<void()> Callback;

    Op(const std::string& t) : table(t) { }
    
    const std::string& get_table() const { return table; }
    
private:
    const std::string table;
};
    
class PutOp
    : public Op
{
public:
    /**
     * @param table the network database table name.
     * @param r the row to insert.
     * @param replace the row(s) to replace.
     */
    PutOp(const std::string& table, 
          const Row_ptr& r,
          const Select_ptr& repl = Select_ptr()) 
        : Op(table), row(r), replace(repl) { }

    inline const Row_ptr& get_row() const { return row; }

    inline const Select_ptr& get_replace() const { return replace; }
    
private:
    const Row_ptr row;
    const Select_ptr replace;    
};
    
class GetOp
    : public Op
{
public:
    GetOp(const std::string& table,
          const Select_ptr& s,
          Callback cb = 0) :
        Op(table), select(s), callback(cb), results() { }

    inline const Select_ptr& get_select() const { return select; }
    
    inline const Callback& get_callback() const { return callback; }

    inline Callback set_callback(const Callback &cb) { 
        Callback old = callback;
        callback = cb; 
        return old;
    }

    inline const Results_ptr& get_results() const { return results; }

    inline const bool has_results() const { return results.get(); }

    inline void set_results(Results_ptr& r) { results = r; }

private:
    const Select_ptr select;
    Callback callback;
    Results_ptr results;
};

} // namespace vigil

// Hash functions

namespace std {

template <>
struct equal_to<vigil::Op::KeyValue>
    : public std::binary_function<vigil::Op::KeyValue, 
                                  vigil::Op::KeyValue, 
                                  bool>
{
    bool operator()(const vigil::Op::KeyValue& r1,
                    const vigil::Op::KeyValue& r2) const {
        using namespace vigil;
        
        if (r1.type != r2.type) {
            return false;
        }

        switch (r1.type) {
        case Op::NONE:
            return true;

        case Op::INT:
            return r1.int_val == r2.int_val;

        case Op::TEXT:
            return r1.text_val == r2.text_val;

        case Op::DOUBLE:
            return r1.double_val == r2.double_val;

        case Op::BLOB:
            {
                const bool result = r1.blob_len == r2.blob_len &&
                    !memcmp(r1.blob_val, r2.blob_val, r1.blob_len);
                return result;
            }
        }

        // Never reached...
        return false;
    }
};

template <>
struct equal_to<vigil::Op::Row_ptr>
    : public std::binary_function<vigil::Op::Row_ptr, 
                                  vigil::Op::Row_ptr,
                                  bool>
{
    bool operator()(const vigil::Op::Row_ptr& r1,
                    const vigil::Op::Row_ptr& r2) const {
        using namespace vigil;

        Op::Row::const_iterator i = r1->begin();        
        bool match = true;
        while (match && i != r1->end()) {
            match = false;

            for (Op::Row::const_iterator j = r2->begin(); j != r2->end() && !match; ++j) {
                struct equal_to<Op::KeyValue> f;
                match = f(**i, **j);                
            }
            
            ++i; 
        }

        return match;
    }
};

template <>
struct equal_to<vigil::Op::Results_ptr>
    : public std::binary_function<vigil::Op::Results_ptr, 
                                  vigil::Op::Results_ptr, 
                                  bool>
{
    bool operator()(const vigil::Op::Results_ptr& r1,
                    const vigil::Op::Results_ptr& r2) const {
        using namespace vigil;

        if (r1.get() == 0 || r2.get() == 0) {
            return r1.get() == r2.get();
        }

        Op::Results::const_iterator i = r1->begin();
        Op::Results::const_iterator j = r2->begin();
        while (true) {
            if (i == r1->end() || j == r2->end()) {
                return (i == r1->end() && j == r2->end());
            }

            struct equal_to<Op::Row_ptr> f;
            if (!f(*i, *j)) {
                return false;
            }

            ++i; ++j;
        }
    }
};

} // namespace std

namespace vigil {

class NDB
{
public:
    /* Execute return codes */
    enum OpStatus {
        OK = 0,
        DEPENDENCY_ERROR,
        INVALID_SCHEMA_TYPE,
        GENERAL_ERROR
    };

    typedef boost::function<void(OpStatus)> Callback;
   
    typedef std::pair<std::string, Op::ValueType> ColumnDef;
    typedef std::list<ColumnDef> ColumnDef_List;
    
    typedef std::list<std::string> IndexDef;
    typedef std::list<IndexDef> IndexDef_List;

    NDB();
    virtual ~NDB();

    static void getInstance(const container::Context*, vigil::NDB*&);

    /**
     * Initialize the database.
     *
     * If no callback function is given, the call is blocking.
     */
    virtual OpStatus init(const Callback& = 0) = 0;

    /**
     * Create a table.
     */
    virtual OpStatus create_table(const std::string& table,
                                  const ColumnDef_List&,
                                  const IndexDef_List&,
                                  const Callback& = 0) = 0; 
    
    virtual OpStatus drop_table(const std::string&,
                                const Callback& = 0) = 0; 
    
    /**
     * If no callback function is given, the call is blocking.
     */
    virtual OpStatus execute(const std::list<boost::shared_ptr<GetOp> >&,
                             const Callback& = 0) = 0; 

    /**
     * If no callback function is given, the call is blocking.
     */
    virtual OpStatus execute(const std::list<boost::shared_ptr<PutOp> >&,
                             const std::list<boost::shared_ptr<GetOp> >&,
                             const Callback& = 0) = 0;

    /**
     * Flush all non-commited changes to disk.
     *
     * If no callback function is given, the call is blocking.
     */
    virtual OpStatus sync(const Callback& = 0) = 0;

    /**
     * Connect a extractor instance to receive a stream of all API
     * calls.  Can be called only when the components are being
     * configured.
     */
    virtual OpStatus connect_extractor(NDB*) = 0;

    /* Support for periodic commits. */
    timeval get_commit_period();
    void set_commit_period(const timeval&);
    Co_cond* get_commit_change_condition();

private:
    /* Support for periodic commits. */
    struct timeval commit_period;
    Co_cond changed;
};

} // namespace vigil

#endif /* controller/ndb.hh */
