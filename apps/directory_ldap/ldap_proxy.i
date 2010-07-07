%module "nox.ext.apps.directory_ldap"

%{
#include "directory/directory.hh"
#include "pyldap_proxy.hh"
#include "pyrt/pycontext.hh"
using namespace vigil;
using namespace vigil::applications;
using namespace vigil::applications::directory;
%}

%include "std_string.i"
%include "utf8_string.i"
%include "pyldap_proxy.hh"

