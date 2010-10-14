include ../../Make.vars 

EXTRA_DIST =\
	meta.json

pkglib_LTLIBRARIES =		\
	audit.la

audit_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../
audit_la_SOURCES = audit.cc
audit_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json	

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
