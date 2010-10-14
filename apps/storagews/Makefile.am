include ../../Make.vars

EXTRA_DIST = meta.xml \
	__init__.py \
	storage_schema.py \
	base_storagews.py \
	storagews.py \
	transactional_storagews.py 

# Required for static_www build/install
MODULE=storagews
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.xml __init__.py storage_schema.py \
                   base_storagews.py storagews.py transactional_storagews.py

all-local: nox-runtimefiles-build nox-all-local
clean-local: nox-runtimefiles-clean nox-clean-local
install-exec-hook: nox-install-local

