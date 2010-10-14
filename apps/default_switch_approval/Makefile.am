include ../../Make.vars 

EXTRA_DIST =\
	meta.json \
	static_www

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED 

pkglib_LTLIBRARIES =		\
	default_switch_approval.la

default_switch_approval_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/apps/ -I $(top_srcdir)/.. -I $(top_srcdir)/../webapps/ -I $(top_srcdir)/../coreapps/ -I $(top_srcdir)/../netapps/
default_switch_approval_la_SOURCES = default_switch_approval.cc default_switch_approval.hh
default_switch_approval_la_LDFLAGS = -module -export-dynamic

# Required for static_www build/install
MODULE=default_switch_approval
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.json	

all-local: nox-all-local static-www-build
clean-local: nox-clean-local static-www-clean
install-exec-hook: nox-install-local
