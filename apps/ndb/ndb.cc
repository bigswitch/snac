#include "ndb.hh"
#include "masterndb.hh"
#include "threads/cooperative.hh"
#include "timeval.hh"

using namespace std;
using namespace vigil;
using namespace vigil::container;

namespace vigil {

NDB::NDB() {
    commit_period.tv_sec = 300;
    commit_period.tv_usec = 0;
}
    
NDB::~NDB() {
}

void 
NDB::getInstance(const container::Context* ctxt, vigil::NDB*& ndb) {
    ndb = dynamic_cast<NDB*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(NDB).name())));
}

timeval
NDB::get_commit_period()
{
    return commit_period;
}

void
NDB::set_commit_period(const timeval& tv) 
{
    changed.broadcast();
    commit_period = tv;
}

Co_cond*
NDB::get_commit_change_condition() 
{
    return &changed;
}
/*
void
set_commit_period(std::vector<std::string>& arg)
{
    NDB::set_commit_period(make_timeval(atoi(arg[0].c_str()), 0));
}
//static Application commit_period_app("ndb.commit-period", 1, 1,
//                                     set_commit_period);*/

}

REGISTER_COMPONENT(container::Simple_component_factory<MasterNDB>, NDB);
