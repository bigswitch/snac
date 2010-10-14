include ../../Make.vars 

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES =		\
	dwh.la			

dwh_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../
dwh_la_SOURCES = dwh.cc                  
dwh_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json

if PY_ENABLED
NOX_RUNTIMEFILES += 	\
	api.py          \
	__init__.py
endif # PY_ENABLED

all-local:  nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
