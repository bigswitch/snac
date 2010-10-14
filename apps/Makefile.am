include ../Make.vars

SUBDIRS=audit coreui ctlflood dwh ndb pf static_registration exttests \
	directory directory_nox http_redirector userauthportal \
	snackui sepl dbexplorer webservice_testui miscws failover \
	notification captiveportal debug local_config dhcp \
	redirproxy restracker storage configuration visibility \
	default_switch_approval

SUBDIRS += $(MODULES_apps)

EXTRA_DIST = \
	__init__.py

NOX_RUNTIMEFILES = \
	__init__.py

all-local:  nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
