    # Copyright 2008 (C) Nicira, Inc.
include ../../Make.vars 

EXTRA_DIST =								\
	__init__.py							\
	meta.xml							\
	pyreplicator.cc							\
	pyreplicator.hh							\
	replicator.i

pkglib_LTLIBRARIES =							\
	replicator.la

replicator_la_CPPFLAGS =						\
	$(AM_CPPFLAGS)							\
	-I$(srcdir)/../							\
	-I$(top_srcdir)/../						\
	-I$(top_srcdir)/../../					\
	-I$(top_srcdir)/../apps/				\
	-I$(top_srcdir)/../netapps/				\
	-I$(top_srcdir)/../coreapps/					\
	-D__COMPONENT_FACTORY_FUNCTION__=replicator_get_factory
replicator_la_SOURCES =							\
	replicator.cc							\
	replicator.hh
replicator_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml

if PY_ENABLED

AM_CPPFLAGS += $(PYTHON_CPPFLAGS)

pyreplicator_wrap_includes =						\
	replicator.i pyreplicator.hh pyreplicator.cc

pyreplicator_wrap.cc pyreplicator.py: $(pyreplicator_wrap_includes)
	swig -I$(top_srcdir)/../lib/ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -outdir $(builddir)/. -o pyreplicator_wrap.cc -c++ -python -module pyreplicator $(srcdir)/replicator.i

pkglib_LTLIBRARIES += _pyreplicator.la
_pyreplicator_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(top_srcdir)/../../
nodist__pyreplicator_la_SOURCES = pyreplicator_wrap.cc
_pyreplicator_la_LDFLAGS = -module

NOX_RUNTIMEFILES +=							\
	__init__.py							\
	replicatorws.py

NOX_PYLIBFILES =							\
	_pyreplicator.so

NOX_PYBUILDFILES = pyreplicator.py

endif

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
