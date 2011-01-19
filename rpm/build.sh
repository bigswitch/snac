#!/bin/bash

sourcedir=$(dirname $0)
builddir=$(pwd)

set -ex

tar -C ${sourcedir}/../../../../..  -c -z -f ${builddir}/openflow.tar.gz --exclude=.git --exclude=.gitignore openflow
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

HOME=${builddir} rpmbuild -ba ${builddir}/openflow.spec
HOME=${builddir} rpmbuild -ba ${builddir}/snac.spec
