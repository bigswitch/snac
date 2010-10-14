include ../../Make.vars

# mako_modules should always be empty...
STATIC_SUBDIRS=www templates
EMPTY_SUBDIRS=mako_modules

NOX_RUNTIMEFILES = meta.json __init__.py nox_directory.py default_groups.py \
                   testauthui.py schema_migration_plugin.py

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local

# Need to create a rule for actually installing LINK_SUBDIRS by
# copying them.
