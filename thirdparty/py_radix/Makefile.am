include ../../../Make.vars

if PY_ENABLED

AM_CPPFLAGS += $(PYTHON_CPPFLAGS)

EXTRA_DIST = __init__.py
NOX_RUNTIMEFILES = __init__.py

pkglib_LTLIBRARIES = radix.la
radix_la_CPPFLAGS = $(AM_CPPFLAGS)
radix_la_SOURCES = radix.c radix.h radix_python.c
radix_la_LDFLAGS = -module

NOX_PYLIBFILES = radix.so

endif #PY_ENABLED

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
