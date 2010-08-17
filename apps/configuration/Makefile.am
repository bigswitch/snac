include ../../Make.vars 

EXTRA_DIST = 								\
	__init__.py							\
	configuration.cc						\
	configuration.hh						\
	meta.xml 							\
	properties.cc							\
	properties.hh							\
	simple_configws.py							\
	simple_config.py							\
	properties.py

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

NOX_RUNTIMEFILES = meta.xml

pkglib_LTLIBRARIES =							\
	configuration.la  \
	csimple_config.la

configuration_la_CPPFLAGS = 						\
	$(AM_CPPFLAGS) 							\
	-I$(srcdir)/../ 						\
	-I$(top_srcdir)/..						\
	-I$(top_srcdir)/../netapps					\
	-D__COMPONENT_FACTORY_FUNCTION__=configuration_get_factory
configuration_la_SOURCES = 						\
	configuration.cc						\
	configuration.hh						\
	properties.cc							\
	properties.hh

configuration_la_LDFLAGS = -module -export-dynamic

csimple_config_la_CPPFLAGS = 						\
	$(AM_CPPFLAGS) 							\
	-I$(srcdir)/../ 						\
	-I$(top_srcdir)/../netapps					\
	-I$(top_srcdir)/../						
csimple_config_la_SOURCES = 						\
	csimple_config.hh		\
	csimple_config.cc						

csimple_config_la_LDFLAGS = -module -export-dynamic

if PY_ENABLED
NOX_RUNTIMEFILES +=							\
	__init__.py							\
	simple_config.py							\
	simple_configws.py							\
	properties.py
endif

all-local: nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
