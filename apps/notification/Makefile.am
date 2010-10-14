include ../../Make.vars

# Required for static_www build/install
MODULE=notification
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES =							\
	__init__.py							\
	 meta.json							\
	notifier.py							\
	smtp.py								\
	syslog.py							\
	twitter.py

# removed until we add a template directory
#all-local: nox-runtimefiles-build mako-template-build static-www-build
all-local: nox-runtimefiles-build 
clean-local: nox-runtimefiles-clean
install-exec-hook: nox-install-local
