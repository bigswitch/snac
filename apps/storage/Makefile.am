include ../../Make.vars 

EXTRA_DIST = \
	meta.xml \
	__init__.py	\
	StorageTableUtil.py	\
	transactional-storage.i \
	pytransactional-storage.cc \
	pytransactional-storage.hh \
	transactional_storage.py

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED

NOX_RUNTIMEFILES = meta.xml

pkglib_LTLIBRARIES =							\
	transactional-storage-backend.la

#	storage-client.la						\
#	storage-server.la						\
#

#storage_common_la_CPPFLAGS = 						\
#	$(AM_CPPFLAGS) 							\
#	-I$(srcdir)/../ 						\
#	-I$(top_srcdir)/../						\
#	-I$(top_srcdir)/../coreapps/					\
#	-I$(top_srcdir)/../netapps/					\
#	-D__COMPONENT_FACTORY_FUNCTION__=storage_common_get_factory

#storage_common_la_SOURCES = 						\
#	sha1.cc								\
#	sha1.hh								\
#	transactional-storage.cc					\
#	transactional-storage.hh					\
#	transactional-storage-blocking.cc				\
#	transactional-storage-blocking.hh
#	connection.cc							\
#	connection.hh							\
#

#storage_common_la_LDFLAGS = -module -export-dynamic

transactional_storage_backend_la_CPPFLAGS =				\
	$(AM_CPPFLAGS)							\
	-I$(srcdir)/../							\
	-I$(top_srcdir)/../						\
	-I$(top_srcdir)/../coreapps/					\
	-I$(top_srcdir)/../netapps/					\
	-D__COMPONENT_FACTORY_FUNCTION__=transactional_storage_backend_get_factory

transactional_storage_backend_la_SOURCES =				\
	sha1.cc								\
	sha1.hh								\
	transactional-storage.cc					\
	transactional-storage.hh					\
	transactional-storage-blocking.cc				\
	transactional-storage-blocking.hh				\
	sqlite3.c							\
	sqlite3.h							\
	sqlite3-impl.cc							\
	sqlite3-impl.hh

transactional_storage_backend_la_LDFLAGS = -module -export-dynamic

#storage_client_la_CPPFLAGS =						\
#	$(AM_CPPFLAGS)							\
#	-I$(srcdir)/../							\
#	-I$(top_srcdir)/../						\
#	-I$(top_srcdir)/../coreapps/					\
#	-I$(top_srcdir)/../netapps/					\
#	-D__COMPONENT_FACTORY_FUNCTION__=storage_client_get_factory
#storage_client_la_SOURCES =						\
#        client.cc							\
#        client.hh
#storage_client_la_LDFLAGS = -module -export-dynamic
#
#storage_server_la_CPPFLAGS =						\
#	$(AM_CPPFLAGS)							\
#	-I$(srcdir)/../							\
#	-I$(top_srcdir)/../						\
#	-D__COMPONENT_FACTORY_FUNCTION__=storage_server_get_factory
#storage_server_la_SOURCES =						\
#	listener.hh							\
#        server.cc							\
#        server.hh
#storage_server_la_LDFLAGS = -module -export-dynamic

if PY_ENABLED
#pystorage_wrap_includes = storage.i

pytransactional_storage_wrap_includes = transactional-storage.i

pytransactional_storage_wrap.cc pytransactional_storage.py: 		\
	transactional-storage.i
	swig								\
	-I$(top_srcdir)/../						\
	-I$(top_srcdir)/../../coreapps					\
	-I$(top_srcdir)/../../netapps					\
	-outdir $(builddir)/.						\
	-o pytransactional_storage_wrap.cc				\
	-c++								\
	-python								\
	-module pytransactional_storage					\
	$(srcdir)/transactional-storage.i

pkglib_LTLIBRARIES += _pytransactional_storage.la

_pytransactional_storage_la_CPPFLAGS =					\
	$(AM_CPPFLAGS)							\
	-I$(top_srcdir)/../						\
	-I$(top_srcdir)/../coreapps					\
	-I$(top_srcdir)/../netapps					\
	-I$(top_srcdir)/../

nodist__pytransactional_storage_la_SOURCES = pytransactional_storage_wrap.cc transactional-storage.i
_pytransactional_storage_la_LDFLAGS = -module

NOX_RUNTIMEFILES +=							\
	__init__.py							\
	transactional_storage.py					\
	StorageTableUtil.py					

NOX_PYBUILDFILES = pytransactional_storage.py

NOX_PYLIBFILES = \
	transactional-storage-backend.so \
	_pytransactional_storage.so

endif # PY_ENABLED

all-local: nox-all-local 
clean-local: nox-clean-local
install-exec-hook: nox-install-local
