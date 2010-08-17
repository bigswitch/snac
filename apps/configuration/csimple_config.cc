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
#include "vlog.hh"
#include <boost/bind.hpp>
#include <vector> 
#include "csimple_config.hh"

/*
 * CSimpleConfig is a wrapper around the Properties class that 
 * presents a simple interface for components that want to do only 
 * very simple getting and setting of properties (i.e., most apps). 
 * The key simpliciations are: 
 * 1) Properties are passed back and for as simple maps, and each
 * key corresponds to a single-value, not a list. 
 * 2) The asynchronous calls related to transactions and loaded 
 * are performed automatically, and simple error messages are 
 * reported on failures.  
 *
 * If you need more control, please use the Properties class directly. 
 */


using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace vigil::applications;
using namespace vigil::applications::configuration; 

static Vlog_module lg("csimple_config");
 
struct Get_Properties_Op { 
    Get_Properties_Op(const string &sec, Prop_map_callback &cb, 
          storage::Async_transactional_storage* storage): type(PMAP), 
      properties(storage,sec), section_id(sec), pmap_callback(cb) {
      start(); 
  }
    
  Get_Properties_Op(const string &sec, Prop_callback &cb, 
          storage::Async_transactional_storage* storage): type(FULL),
      properties(storage,sec), section_id(sec), full_callback(cb) {
      start(); 
  }
  
  void start() { 
      properties.async_load(
        boost::bind(&Get_Properties_Op::get_load_cb,this), 
        boost::bind(&Get_Properties_Op::get_eb,this));  
  } 
 
  void done() {
    if(type == FULL) { 
      full_callback(properties); 
      return; 
    } 

    // else PMAP 
    Prop_map pmap; 
    vector<string> keys = properties.get_loaded_keys();
    vector<string>::iterator it;
    for(it = keys.begin(); it != keys.end(); ++it) {
      Property_list_ptr pl = properties.get_value(*it); 
      if(pl->size() > 0)  
        pmap[*it] = (*pl)[0].get_value(); 
    } 
    pmap_callback(pmap); 
    delete this; 
  } 

  void get_eb() { 
    lg.err("Error loading properties for section id = '%s'\n", 
          section_id.c_str());
    done(); 
  } 

  void get_load_cb() { 
    done();  
  } 

 private:
  enum Type { PMAP, FULL } ;  
  Type type; 
  Properties properties; 
  string section_id;
  Prop_callback full_callback; 
  Prop_map_callback pmap_callback; 
}; 

struct Set_Properties_Op { 
    Set_Properties_Op(const string &sec, const Prop_map &map, 
          storage::Async_transactional_storage* storage, bool unset_only): 
      properties(storage,sec), section_id(sec), prop_map(map),
      only_modify_unset_props(unset_only){
  
      properties.async_begin(
        boost::bind(&Set_Properties_Op::begin_cb,this), 
        boost::bind(&Set_Properties_Op::set_eb,this));  
    }  
 
  void done() { 
    delete this; 
  } 

  void set_eb() { 
    lg.err("Error setting properties for section id = '%s'\n", 
          section_id.c_str());
    done(); 
  } 

  void begin_cb() { 
    Prop_map::iterator it; 
    for(it = prop_map.begin(); it != prop_map.end(); ++it) { 
      Property_list_ptr pl = properties.get_value(it->first);
      if(only_modify_unset_props && pl->size() > 0)
        continue; 
      pl->clear(); 
      pl->push_back(Property(it->second)); 
    } 
    properties.async_commit(
        boost::bind(&Set_Properties_Op::done,this), 
        boost::bind(&Set_Properties_Op::set_eb,this));  

  } 
  
  Properties properties; 
  string section_id; 
  Prop_map prop_map; 
  bool only_modify_unset_props; 
}; 

void CSimpleConfig::get_config(const string &sec_id, Prop_map_callback &cb) { 
  new Get_Properties_Op(sec_id,cb,storage);
} 

void CSimpleConfig::set_config(const string &sec_id, const Prop_map &pmap) { 
  new Set_Properties_Op(sec_id,pmap,storage,false); 
} 

void CSimpleConfig::set_config_no_overwrite(const string &sec_id, 
                                             const Prop_map &pmap) { 
  new Set_Properties_Op(sec_id,pmap,storage,true); 
} 

void
CSimpleConfig::getInstance(const container::Context* ctxt,
                           CSimpleConfig*& h) {
    h = dynamic_cast<CSimpleConfig*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(CSimpleConfig).name())));
}


REGISTER_COMPONENT(container::Simple_component_factory<CSimpleConfig>,
                   CSimpleConfig);

