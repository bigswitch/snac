include ../../Make.vars 

EXTRA_DIST = meta.xml		\
	compile.py		\
	declare.py		\
	example_policy.py	\
	example_principals.py	\
	__init__.py		\
	policy.py		\
	policystore.py		\
	sepl_enforcer.i		\
	sepl_stats.i		\
	sepl_directory.py

# if current policy doesn't exist, use example_policy.py
current_policy.py:
	ln -s $(srcdir)/example_policy.py current_policy.py
principals.py:
	ln -s $(srcdir)/example_principals.py principals.py

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES =		\
	seplenforcer.la		\
	seplstats.la

seplenforcer_la_CPPFLAGS =	\
	$(AM_CPPFLAGS)		\
	-I$(srcdir)/../		\
	-I$(top_srcdir)/../	\
	-I$(top_srcdir)/../../ \
	-I$(top_srcdir)/../apps/ \
	-I$(top_srcdir)/../netapps/ \
	-I$(top_srcdir)/../coreapps/ \
	-D__COMPONENT_FACTORY_FUNCTION__=seplenforcer_get_factory

seplenforcer_la_SOURCES = sepl_enforcer.hh sepl_enforcer.cc sepl_enforcer_python.cc
seplenforcer_la_LDFLAGS = -module -export-dynamic

seplstats_la_CPPFLAGS =		\
	$(AM_CPPFLAGS)		\
	-I$(srcdir)/../		\
	-I$(top_srcdir)/../	\
	-D__COMPONENT_FACTORY_FUNCTION__=seplstats_get_factory

seplstats_la_SOURCES = sepl_stats.hh sepl_stats.cc
seplstats_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml

if PY_ENABLED

pyseplenforcer_wrap_includes =	\
	sepl_enforcer.i

pyseplenforcer_wrap.cc pyseplenforcer.py: $(pyseplenforcer_wrap_includes)
	swig -I$(top_srcdir)/../lib/ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -outdir $(builddir)/. -o pyseplenforcer_wrap.cc -c++ -python -module pyseplenforcer $(srcdir)/sepl_enforcer.i

pkglib_LTLIBRARIES += _pyseplenforcer.la
_pyseplenforcer_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(top_srcdir)/../../
_pyseplenforcer_la_SOURCES = pysepl_enforcer.hh pysepl_enforcer.cc
nodist__pyseplenforcer_la_SOURCES = pyseplenforcer_wrap.cc
_pyseplenforcer_la_LDFLAGS = -module

pyseplstats_wrap_includes =	\
	sepl_stats.i

pyseplstats_wrap.cc pyseplstats.py: $(pyseplstats_wrap_includes)
	swig -I$(top_srcdir)/../lib/ -outdir $(builddir)/. -o pyseplstats_wrap.cc -c++ -python -module pyseplstats $(srcdir)/sepl_stats.i

pkglib_LTLIBRARIES += _pyseplstats.la
_pyseplstats_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(top_srcdir)/../../
_pyseplstats_la_SOURCES = pysepl_stats.cc pysepl_stats.hh
nodist__pyseplstats_la_SOURCES = pyseplstats_wrap.cc
_pyseplstats_la_LDFLAGS = -module

NOX_RUNTIMEFILES += __init__.py \
	compile.py		\
	current_policy.py	\
	declare.py		\
	principals.py		\
	policy.py		\
	policystore.py		\
	sepl_directory.py

NOX_PYLIBFILES = 		\
	_pyseplenforcer.so	\
	_pyseplstats.so

NOX_PYBUILDFILES =		\
	pyseplenforcer.py	\
	pyseplstats.py

endif # PY_ENABLED

all-local: current_policy.py nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
