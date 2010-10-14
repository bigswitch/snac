include ../../Make.vars

SUBDIRS=help_src

MODULE=snackui
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = meta.json __init__.py \
	snackmonitors.py policyui.py reportsui.py settingsui.py helpui.py \
	snackui.py principal_list_pages.py search.py flow_table_page.py

all-local: nox-runtimefiles-build mako-template-build static-www-build
clean-local: nox-runtimefiles-clean mako-template-clean static-www-clean
install-exec-hook: nox-install-local
