include ../../Make.vars

MODULE=dhcp
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = 		\
	__init__.py		\
	manager.py 		\
	config.py		\
	meta.xml

all-local: nox-runtimefiles-build 
clean-local: nox-runtimefiles-clean
install-exec-hook: nox-install-local
