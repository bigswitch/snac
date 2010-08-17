#ifndef CSIMPLE_CONFIG_HH
#define CSIMPLE_CONFIG_HH 1

#include "component.hh"
#include "config.h"
#include <boost/function.hpp>
#include "storage/transactional-storage.hh"
#include "configuration/properties.hh"
#include <map> 

namespace vigil {
namespace applications {
namespace configuration {

typedef std::map<std::string, storage::Column_value>  Prop_map; 
typedef boost::function<void(const Prop_map &)> Prop_map_callback; 
typedef boost::function<void(const Properties &)> Prop_callback; 

class CSimpleConfig : public container::Component {
public:
  
    CSimpleConfig(const container::Context* c, const json_object*)
        : Component(c) {
    }

    void configure(const container::Configuration*) {
      resolve(storage); 
    }

    void install() {
    }

    void get_config(const std::string &section_id, Prop_map_callback &cb); 
    void set_config_no_overwrite(const std::string &sec_id, 
                                 const Prop_map &pmap); 
    void set_config(const std::string &sec_id, const Prop_map &pmap); 
    
    static void getInstance(const container::Context*, CSimpleConfig *&);

private:
  
    storage::Async_transactional_storage* storage; 
};


}
} 
} 
#endif 
