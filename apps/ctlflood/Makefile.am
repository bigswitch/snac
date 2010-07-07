include ../../Make.vars 

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

pkglib_LTLIBRARIES =		\
	ctlflood.la		

ctlflood_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../
ctlflood_la_SOURCES = ctlflood.cc
ctlflood_la_LDFLAGS = -module -export-dynamic

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
