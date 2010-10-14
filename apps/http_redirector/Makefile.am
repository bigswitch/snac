include ../../Make.vars 

pkglib_LTLIBRARIES =		\
	http_redirector.la

http_redirector_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/
http_redirector_la_SOURCES = http_redirector.cc http_redirector.hh \
                             redirected_flow_cache.cc redirected_flow_cache.hh
http_redirector_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json	

if PY_ENABLED

AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
NOX_RUNTIMEFILES += __init__.py

NOX_PYBUILDFILES = \
	pyhttp_redirector.py

pyhttp_redirector_wrap.cc pyhttp_redirector.py: pyhttp_redirector.i
	swig -I$(top_srcdir)/../lib/ -outdir $(builddir)/. -o \
			pyhttp_redirector_wrap.cc -c++ -python -module \
 			pyhttp_redirector $(srcdir)/pyhttp_redirector.i

pkglib_LTLIBRARIES += _pyhttp_redirector.la
_pyhttp_redirector_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(top_builddir)/../
_pyhttp_redirector_la_SOURCES = http_redirector_proxy.cc
nodist__pyhttp_redirector_la_SOURCES = pyhttp_redirector_wrap.cc
_pyhttp_redirector_la_LDFLAGS = -module

NOX_PYLIBFILES = _pyhttp_redirector.so

endif # PY_ENABLED

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
