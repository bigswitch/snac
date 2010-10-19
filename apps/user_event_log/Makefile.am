include ../../Make.vars

MODULE=user_event_log
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.json __init__.py UI_user_event_log.py

all-local: nox-runtimefiles-build static-www-build
clean-local: nox-runtimefiles-clean static-www-clean
install-exec-hook: nox-install-local
