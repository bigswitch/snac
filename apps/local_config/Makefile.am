include ../../Make.vars 

SUBDIRS=debian

EXTRA_DIST = \
	meta.json \
	interface_change_event.py \
	local_config.py \
	local_configws.py \
	__init__.py 

NOX_RUNTIMEFILES = meta.json	\
	interface_change_event.py \
	local_config.py \
	local_configws.py \
	__init__.py	

all-local: nox-all-local
install-exec-hook: nox-install-local
