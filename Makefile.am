include Make.vars

SUBDIRS=apps
AUTOMAKE_OPTIONS = foreign
ACLOCAL_AMFLAGS = -I config

EXTRA_DIST = \
	__init__.py

if PY_ENABLED
swigpyrun.h: 
	$(SWIG) $(SWIG_PYTHON_OPT) -external-runtime swigpyrun.h

#BUILT_SOURCES = swigpyrun.h

NOX_RUNTIMEFILES = __init__.py
all: swigpyrun.h
endif # PY_ENABLED

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
