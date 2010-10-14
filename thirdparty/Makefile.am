include ../Make.vars

AUTOMAKE_OPTIONS = foreign

SUBDIRS = py_radix
DIST_SUBDIRS = py_radix

if PY_ENABLED

NOX_RUNTIMEFILES = __init__.py
EXTRA_DIST = __init__.py

endif # PY_ENABLED

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
