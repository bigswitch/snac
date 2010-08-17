include ../../Make.vars

SUBDIRS = pyunittests

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES = tests.la

tests_la_CPPFLAGS = $(AM_CPPFLAGS) \
    -I$(srcdir)/..	\
    -I$(srcdir)/../ \
	-I$(top_srcdir)/../  \
	-I$(top_builddir)/../  \
    -I$(top_srcdir)/../apps/ \
    -I$(top_srcdir)/../netapps/ \
    -I$(top_srcdir)/../coreapps/ \
	-D__COMPONENT_FACTORY_FUNCTION__=tests_get_factory
tests_la_CFLAGS = $(AM_CFLAGS)
tests_la_LDFLAGS = -module -export-dynamic
tests_la_SOURCES = 				\
	tests.cc			

NOX_RUNTIMEFILES = 				\
	meta.xml		

if PY_ENABLED
NOX_PYLIBFILES = _pytests.so

NOX_RUNTIMEFILES += 				\
	pytests.py				\
	unittest.py				\
	__init__.py

pytests_wrap.cc pytests.py: pytests.i
	swig -outdir $(builddir)/. -o pytests_wrap.cc -c++ -python \
	-module pytests $(srcdir)/pytests.i
pkglib_LTLIBRARIES += _pytests.la
nodist__pytests_la_SOURCES = pytests_wrap.cc
_pytests_la_LDFLAGS = -module

endif # PY_ENABLED

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
