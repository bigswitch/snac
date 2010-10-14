include ../../Make.vars

EXTRA_DIST=\
   __init__.py \
   authui.py \
   coreui.py \
   meta.json \
   base_www \
   static_www \
   templates/ \
   monitorsui.py \
   template_utils.py\
   asyncwebserviceclient.py

# Required for static_www build/install
MODULE=coreui
MODULE_BASE_PATH=nox/ext/apps
MODULE_BASE_ESCAPE=../../..

NOX_RUNTIMEFILES = \
   __init__.py \
   asyncwebserviceclient.py \
   authui.py \
   coreui.py \
   meta.json \
   monitorsui.py \
   template_utils.py

DOJO_VERSION=1.2.1

BASE_WWW_FILES=dojo-release-$(DOJO_VERSION)/dojo \
	dojo-release-$(DOJO_VERSION)/dijit \
	dojo-release-$(DOJO_VERSION)/dojox \
	dojo-release-$(DOJO_VERSION)/util

www-build:
	mkdir -p ${builddir}/www
	@dlist="$(BASE_WWW_FILES)";for f in $$dlist; do \
		echo "Soft-linking from base_www: $$f";\
		(cd $(builddir)/www && ln -sf ../$(srcdir)/base_www/$$f .);\
	done;

www-clean:
	rm -rf "$(builddir)/www"
	rm -rf "$(builddir)/www-dojo-build"

all-local: nox-runtimefiles-build mako-template-build www-build static-www-build
clean-local: nox-runtimefiles-clean mako-template-clean www-clean static-www-clean

install-exec-hook : nox-install-local
	rm -rf $(builddir)/www-dojo-build
	@echo "Copying files to prepare dojo build."
	cp -rLlf $(builddir)/www $(builddir)/www-dojo-build
	@echo "Copy complete, starting build.."
	if [ -f "$(top_srcdir)/etc/dojo-build.profile.js" ]; then \
		(cd www-dojo-build/util/buildscripts; ./build.sh action=release profileFile="$(top_srcdir)/etc/dojo-build.profile.js" releaseName="nox-dojo-build" releaseVersion="$(DOJO_VERSION)" optimize=shrinksafe cssOptimize=comments copyTests=false internStrings=true;); \
	else \
		(cd www-dojo-build/util/buildscripts; ./build.sh action=release profileFile="$(top_srcdir)/src/etc/dojo-build.profile.js" releaseName="nox-dojo-build" releaseVersion="$(DOJO_VERSION)" optimize=shrinksafe cssOptimize=comments copyTest=false internStrings=true;); \
	fi
	mkdir -p $(nox_installwwwdir)
	cp -r www-dojo-build/release/nox-dojo-build/* $(nox_installwwwdir)
	rm -rf $(builddir)/www-dojo-build
