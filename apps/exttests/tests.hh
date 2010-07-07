#ifndef CONTROLLER_TESTS_HH
#define CONTROLLER_TESTS_HH 1

#include <string>

#include <boost/bind.hpp>
#include <boost/test/unit_test.hpp>

#include "component.hh"
#include "kernel.hh"
#include "static-deployer.hh"

namespace vigil {
namespace testing {

/*
 * Test cases requiring access to other components should inherit
 * TestComponent class and be registered with the
 * BOOST_AUTO_COMPONENT_TEST_CASE macre below.
 */

class Test_component
    : public container::Component {
public:
    Test_component(const container::Context* c)
        : Component(c) { } 
    
    virtual void run_test() = 0;
};

} // namespace testing
} // namespace vigil

#define BOOST_AUTO_COMPONENT_TEST_CASE(COMPONENT_NAME, COMPONENT_CLASS) \
    BOOST_AUTO_TEST_CASE(COMPONENT_NAME) {                              \
        using namespace vigil::container;                               \
        static Interface_description                                    \
            i(typeid(COMPONENT_CLASS).name());                          \
        static Simple_component_factory<COMPONENT_CLASS> cf(i);         \
        Kernel* kernel = Kernel::get_instance();                        \
        try {                                                           \
            kernel->install(new vigil::Static_component_context         \
                            (kernel, #COMPONENT_NAME, &cf, 0));         \
            Component_context* ctxt =                                   \
                (kernel->get(#COMPONENT_NAME, INSTALLED));              \
            BOOST_REQUIRE(ctxt);                                        \
            vigil::testing::Test_component* tc =                        \
                dynamic_cast<vigil::testing::Test_component*>           \
                (ctxt->get_instance());                                 \
            BOOST_REQUIRE(tc);                                          \
            tc->run_test();                                             \
        } catch (const std::runtime_error& e) {                         \
            BOOST_REQUIRE_MESSAGE(0, "Unable to install :"              \
                                  #COMPONENT_NAME);                     \
        }                                                               \
    }

#endif
