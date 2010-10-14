include ../../Make.vars 

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES =		\
	pf.la	

pf_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/ -I$(srcdir)/p0f/
pf_la_SOURCES =			\
	p0f-sigs.cc		\
	p0f-sigs.hh		\
	p0f/crc32.h		\
	p0f/fpentry.h		\
	p0f/mtu.h		\
	p0f/p0f-query.h		\
	p0f/tcp.h		\
	p0f/tos.h		\
	p0f/types.h		\
	pf-match.hh		\
	pf-sigs.cc		\
	pf-sigs.hh		\
	pf.cc			\
	pf.hh
pf_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json

if PY_ENABLED
pypf_wrap_includes = 		\
  pf.i			

EXTRA_DIST = $(pypf_wrap_includes)

pypf_wrap.cc pypf.py: $(pypf_wrap_includes)
	swig -I$(top_srcdir)/../lib/ -outdir $(builddir)/. -o pypf_wrap.cc -c++ -python -module pypf $(srcdir)/pf.i
pkglib_LTLIBRARIES += _pypf.la
_pypf_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(top_srcdir)/../ -I$(srcdir)/../ -I$(top_srcdir)/../apps/ -I$(top_srcdir)/../netapps/ -I$(top_srcdir)/../coreapps/
nodist__pypf_la_SOURCES = pypf_wrap.cc
_pypf_la_LDFLAGS = -module

NOX_RUNTIMEFILES +=	\
	pypf.py \
	p0f.fp  \
	p0fa.fp \
	pf.os   \
	__init__.py \
  pfws.py

NOX_PYLIBFILES = _pypf.so

endif # PY_ENABLED

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
