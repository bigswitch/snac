dnl Process this file with autoconf to produce a configure script.

AC_PREREQ(2.59)
AC_INIT(ext, v0.0.1, nox-dev@nicira.com)
AC_CONFIG_AUX_DIR(config)
AC_CONFIG_MACRO_DIR(config)

AM_INIT_AUTOMAKE

AC_PROG_CXX
AC_PROG_CC
AC_PROG_CPP

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE

AC_DISABLE_STATIC
AC_LIBTOOL_DLOPEN
AC_PROG_LIBTOOL

CHECK_OPENFLOW

AC_CHECK_FUNCS([fdatasync])
AC_CONFIG_SRCDIR([apps/])
AC_CONFIG_HEADER([config.h])

AX_BOOST_BASE([1.34.1])

AX_BOOST_FILESYSTEM
if test "$ax_cv_boost_filesystem" != "yes"; then
   AC_MSG_ERROR([cannot find the Boost::Filesystem library])
fi

CHECK_PCAP
CHECK_SSL
CHECK_NDEBUG
CHECK_PROFILING
CHECK_NETLINK
CHECK_RTC
CHECK_THREAD_LOCAL
CHECK_WITH_VM
CHECK_LTDL
CHECK_LDAP

CHECK_TWISTED
dnl only check for swig if python was enabled
if test -n "$PYTHON"; then
    AC_PROG_SWIG(1.3.0)
    if test -z "$SWIG"; then
        AC_MSG_ERROR([When configured with python, NOX requires swig 1.3.0 or later to be installed])
    fi
    SWIG_ENABLE_CXX
    SWIG_PYTHON
fi    

ACI_MODULE([directory_ldap],[LDAP authentication store],
               [],[],[yes])

dnl TODO automatically generate the following list of submodules
ACI_MODULE([apps],[main source libarary],
               [],
               [directory_ldap],
               [yes])
ACI_MODULES_VERIFY
AC_SUBST(MODULES_apps)               


AC_CONFIG_FILES([
Makefile 
apps/Makefile
apps/audit/Makefile
apps/captiveportal/Makefile
apps/configuration/Makefile
apps/ctlflood/Makefile
apps/dhcp/Makefile
apps/directory/Makefile
apps/directory_ldap/Makefile
apps/directory_nox/Makefile
apps/dwh/Makefile
apps/failover/Makefile
apps/http_redirector/Makefile
apps/exttests/Makefile
apps/exttests/pyunittests/Makefile
apps/ndb/Makefile
apps/pf/Makefile
apps/static_registration/Makefile
apps/userauthportal/Makefile
apps/sepl/Makefile
apps/snackui/Makefile
apps/snackui/help_src/Makefile
apps/storage/Makefile
apps/dbexplorer/Makefile
apps/webservice_testui/Makefile
apps/miscws/Makefile
apps/debug/Makefile
apps/notification/Makefile
apps/redirproxy/Makefile
apps/restracker/Makefile
apps/local_config/Makefile
apps/local_config/debian/Makefile
apps/visibility/Makefile
])

AC_OUTPUT
