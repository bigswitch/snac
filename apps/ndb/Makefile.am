include ../../Make.vars 

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES = ndb.la			

ndb_la_CPPFLAGS =					\
	$(AM_CPPFLAGS)					\
	-I$(srcdir)/../					\
	-I$(top_srcdir)/../				\
	-D__COMPONENT_FACTORY_FUNCTION__=ndb_get_factory

ndb_la_SOURCES = ndb.cc ndb.hh masterndb.cc masterndb.hh sqlitendb.cc sqlitendb.hh\
                 cachendb.cc cachendb.hh
ndb_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml

if PY_ENABLED
pyndb_wrap_includes = 		\
	ndb.i
EXTRA_DIST = $(pyndb_wrap_includes)

pyndb_wrap.cc pyndb.py: ndb.i
	swig -I$(srcdir)/../ -outdir $(builddir)/. -o pyndb_wrap.cc -c++ -python -module pyndb $(srcdir)/ndb.i
pkglib_LTLIBRARIES += _pyndb.la
_pyndb_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(top_srcdir)/../../
nodist__pyndb_la_SOURCES = pyndb_wrap.cc
_pyndb_la_LDFLAGS = -module

NOX_RUNTIMEFILES += 		\
	pyndb.py		\
	api.py			\
	ndb_utils.py		\
	ndbcomponent.py		\
	__init__.py

NOX_PYLIBFILES = _pyndb.so

endif # PY_ENABLED

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
