include ../../Make.vars 

pkglib_LTLIBRARIES =		\
	flow_cache.la

flow_cache_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/
flow_cache_la_SOURCES = flow_cache.cc flow_cache.hh flow_info.hh
flow_cache_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml	

if PY_ENABLED

AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
NOX_RUNTIMEFILES += __init__.py visibility_ws.py

NOX_PYBUILDFILES = \
	pyflow_cache.py

pyflow_cache_wrap.cc pyflow_cache.py: pyflow_cache.i
	swig -I$(top_srcdir)/../lib/ -outdir $(builddir)/. -o \
			pyflow_cache_wrap.cc -c++ -python -module \
 			pyflow_cache $(srcdir)/pyflow_cache.i

pkglib_LTLIBRARIES += _pyflow_cache.la
_pyflow_cache_la_CPPFLAGS = $(AM_CPPFLAGS) \
                            -I$(srcdir)/../ -I$(top_srcdir)/../ \
							-I$(top_srcdir)/../../ \
							-I$(top_srcdir)/../apps/ \
							-I$(top_srcdir)/../netapps/ \
							-I$(top_srcdir)/../coreapps/ \
							-I$(top_builddir)/../
_pyflow_cache_la_SOURCES = flow_cache_proxy.cc flow_cache_proxy.hh
nodist__pyflow_cache_la_SOURCES = pyflow_cache_wrap.cc
_pyflow_cache_la_LDFLAGS = -module

NOX_PYLIBFILES = _pyflow_cache.so

endif # PY_ENABLED

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
