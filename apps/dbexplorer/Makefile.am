include ../../Make.vars

# Required for static_www build/install
MODULE=dbexplorer
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.xml __init__.py dbexplorerui.py


# Need to create a rule for actually installing LINK_SUBDIRS by
# copying them.

all-local: nox-runtimefiles-build mako-template-build static-www-build
clean-local: nox-runtimefiles-clean mako-template-clean static-www-clean
install-exec-hook: nox-install-local
