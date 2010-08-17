include ../Make.vars

# These apps depend on storage/configuration functionality that
# existed in NOX 0.4 but has since been removed, so I'm
# temporarily disabling them.
# http_redirector sepl failover visibility

SUBDIRS=audit ctlflood dwh ndb pf static_registration exttests \
	directory_nox userauthportal \
	snackui dbexplorer webservice_testui miscws \
	notification captiveportal debug local_config dhcp \
	redirproxy restracker configuration

SUBDIRS += $(MODULES_apps)

EXTRA_DIST = \
	__init__.py

NOX_RUNTIMEFILES = \
	__init__.py

all-local:  nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
