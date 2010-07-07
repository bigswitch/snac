include ../../Make.vars

MODULE=webservice_testui
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.xml __init__.py webservice_testui.py

all-local: nox-runtimefiles-build mako-template-build static-www-build
clean-local: nox-runtimefiles-clean mako-template-clean static-www-clean
install-exec-hook: nox-install-local
