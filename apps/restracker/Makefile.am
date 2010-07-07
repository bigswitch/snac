include ../../Make.vars 

# mako_modules should always be empty...
STATIC_SUBDIRS=templates

pkglib_LTLIBRARIES = \
	restracker.la

restracker_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/
restracker_la_SOURCES = restracker.cc restracker.hh 
restracker_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml	

if PY_ENABLED

AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
NOX_RUNTIMEFILES += \
	__init__.py \
	pyrestrackerws.py \
	restrackerui.py

NOX_PYBUILDFILES = \
	pyrestracker.py

pyrestracker_wrap.cc pyrestracker.py: pyrestracker.i
	swig -I$(top_srcdir)/../lib/ -outdir $(builddir)/. -o \
			pyrestracker_wrap.cc -c++ -python -module \
 			pyrestracker $(srcdir)/pyrestracker.i

pkglib_LTLIBRARIES += _pyrestracker.la
_pyrestracker_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(srcdir)/../ -I$(top_srcdir)/../ -I$(top_srcdir)/../../ -I$(top_srcdir)/../apps/ -I$(top_builddir)/../
_pyrestracker_la_SOURCES = restracker_proxy.cc
nodist__pyrestracker_la_SOURCES = pyrestracker_wrap.cc
_pyrestracker_la_LDFLAGS = -module

NOX_PYLIBFILES = _pyrestracker.so

endif # PY_ENABLED

all-local: nox-all-local mako-template-build
clean-local: nox-clean-local mako-template-clean
install-exec-hook: nox-install-local
