include ../../Make.vars

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

EXTRA_DIST = ldap_dir_factory.py pytestldap_proxy.py

pkglib_LTLIBRARIES =	ldap_proxy.la #testldap_proxy.la

ldap_proxy_la_CPPFLAGS = $(AM_CPPFLAGS) \
                         -I$(srcdir)/../\
                         -I$(top_srcdir)/../ \
			 -I$(top_srcdir)/../../\
			 -I$(top_srcdir)/apps/\
			 -I$(top_srcdir)/../netapps/\
			 -I$(top_srcdir)/../coreapps/\
			 -I$(top_srcdir)/../thirdparty
ldap_proxy_la_SOURCES = ldap_proxy.cc ldap_proxy.hh

ldap_proxy_la_LDFLAGS = -module -export-dynamic $(LDAP_LDFLAGS)

NOX_RUNTIMEFILES = meta.json

if PY_ENABLED

NOX_RUNTIMEFILES += __init__.py \
                    ldap_dir_factory.py \
                    pytestldap_proxy.py

NOX_PYBUILDFILES = \
	pyldap_proxy.py

pyldap_proxy_wrap.cc pyldap_proxy.py: ldap_proxy.i ldap_proxy.hh \
                                      pyldap_proxy.hh
	swig -I$(top_srcdir)/../lib/ -I$(srcdir)/../\
			-outdir $(builddir)/. -o pyldap_proxy_wrap.cc \
			-c++ -python -module pyldap_proxy -keyword $(srcdir)/ldap_proxy.i

pkglib_LTLIBRARIES += _pyldap_proxy.la
_pyldap_proxy_la_CPPFLAGS = $(AM_CPPFLAGS)\
							 -I$(srcdir)/../\
							 -I$(top_srcdir)/../ \
							 -I$(top_srcdir)/../../\
							 -I$(top_builddir)/../\
							 -I$(top_srcdir)/apps/\
							 -I$(top_srcdir)/../netapps/\
							 -I$(top_srcdir)/../coreapps/\
							 -I$(top_srcdir)/../thirdparty
_pyldap_proxy_la_SOURCES = pyldap_proxy.cc ldap_proxy.cc ldap_proxy.hh \
                           ldap_proxy.i

nodist__pyldap_proxy_la_SOURCES = pyldap_proxy_wrap.cc
_pyldap_proxy_la_LDFLAGS = -module  $(LDAP_LDFLAGS)

NOX_PYLIBFILES = _pyldap_proxy.so


endif #PY_ENABLED

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
