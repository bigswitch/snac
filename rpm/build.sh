#!/bin/bash

sourcedir=$(dirname $0)
builddir=$(pwd)

set -ex

tar -C ${sourcedir}/../../../../..  -c -z -f ${builddir}/snac.tar.gz --exclude=.git --exclude=.gitignore snac-nox

cp ${sourcedir}/* ${builddir}/

cat >${builddir}/.rpmmacros <<EOF
%_topdir ${builddir}
%_builddir ${builddir}
%_sourcedir ${builddir}
%_specdir ${builddir}
%_srcrpmdir ${builddir}
%_rpmdir ${builddir}
EOF

HOME=${builddir} rpmbuild -ba ${builddir}/snac.spec
