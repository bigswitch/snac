Name: snac
Version: 0.4.2
Release: %{?release}%{!?release:devel.bigswitch}
Summary: SNAC OpenFlow controller

Group: Applications/Networking
License: GPL
Source0: snac.tar.gz
Source2: noxcore.init
Source3: noxcore.default
Source4: noxext.default
Source5: noxext.cron.daily
Source6: noxext.logrotate
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: autoconf >= 2.59
BuildRequires: automake >= 1.9.6
BuildRequires: libtool
BuildRequires: pkgconfig
BuildRequires: gcc-c++
BuildRequires: libstdc++-devel
BuildRequires: boost-devel >= 1.34.1
BuildRequires: sqlite-devel
BuildRequires: swig >= 1.3.0
BuildRequires: openssl-devel
BuildRequires: xerces-c-devel
BuildRequires: python-sphinx
BuildRequires: openldap-devel
BuildRequires: java-openjdk
BuildRequires: python-devel >= 2.4
BuildRequires: python-mako
BuildRequires: python-twisted-web
BuildRequires: python-simplejson
Requires(post): chkconfig
Requires: boost >= 1.34.1
Requires: python >= 2.4
Requires: python-mako
Requires: python-twisted-web
Requires: python-simplejson
Requires: openflow-pki

%description
SNAC OpenFlow controller

%post
/sbin/ldconfig
/sbin/chkconfig --add noxcore
# Obtain keys and certificates for NOX within the OpenFlow PKI.
cd %{_sysconfdir}/nox
if test ! -e cacert.pem; then
    ln -sf %{_datadir}/openflow/pki/controllerca/cacert.pem cacert.pem
fi
if test ! -e privkey.pem || test ! -e cert.pem; then
    oldumask=$(umask)
    umask 077
    ofp-pki req+sign tmp controller >/dev/null
    mv tmp-privkey.pem privkey.pem
    mv tmp-cert.pem cert.pem
    mv tmp-req.pem req.pem
    chmod go+r cert.pem req.pem
    umask $oldumask
fi
# Generate self-signed certificate for NOX as an SSL webserver.
cd %{_sysconfdir}/nox
if test ! -e noxca.key.insecure || test ! -e noxca.cert; then
    gen-nox-cert.sh %{_datadir}/
fi
true

%preun
if [ $1 = 0 ]; then
    /sbin/service noxcore stop >/dev/null 2>&1
    /sbin/chkconfig --del noxcore
fi
true

%postun
/sbin/ldconfig
true

%posttrans
/sbin/service noxcore condrestart >/dev/null 2>&1
true

%prep
%setup -q -n snac-nox
sed -i 's/0.4.1~beta/%{version}-%{release}/g' configure.ac
sed -i 's/$(bindir)/$(libdir)/g;s/^AM_LDFLAGS = -R.*/AM_LDFLAGS =/' src/Make.vars src/nox/ext/Make.vars

%build
aclocal --force -I config
autoheader
libtoolize --force
automake --add-missing --foreign --warnings=no-portability
autoconf
cd src/nox/ext
aclocal --force -I config
autoheader
libtoolize --force
automake --add-missing --foreign --warnings=no-portability
autoconf
cd ../../..
%configure --enable-ndebug --with-python=yes
make all html
make -C src/nox/ext all

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
make -C src/nox/ext install DESTDIR=$RPM_BUILD_ROOT
find $RPM_BUILD_ROOT%{_libdir} -name \*.la | xargs -t rm
install -D -m755 %{SOURCE2} $RPM_BUILD_ROOT%{_initrddir}/noxcore
install -D -m644 %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/noxcore
install -D -m644 %{SOURCE4} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/noxext
install -D -m755 %{SOURCE5} $RPM_BUILD_ROOT%{_sysconfdir}/cron.daily/noxext
install -D -m644 %{SOURCE6} $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/noxext
cat >$RPM_BUILD_ROOT%{_bindir}/noxcore <<"EOF"
#!/bin/bash
cd %{_libdir}
exec %{_bindir}/nox_core "$@"
EOF
chmod +x $RPM_BUILD_ROOT%{_bindir}/noxcore
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/log/snacdb
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/log/nox

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc COPYING LICENSE INSTALL README src/nox/ext/doc/* doc/manual/build/html
%config(noreplace) %{_sysconfdir}/nox
%{_initrddir}/noxcore
%config(noreplace) %{_sysconfdir}/sysconfig/noxcore
%config(noreplace) %{_sysconfdir}/sysconfig/noxext
%{_sysconfdir}/cron.daily/noxext
%{_sysconfdir}/logrotate.d/noxext
%{_bindir}/*
%{_libdir}/libnox*.so*
%{_libdir}/nox
%{_datadir}/nox*
%{_mandir}/man*/*
%dir %{_localstatedir}/log/snacdb
%dir %{_localstatedir}/log/nox

%changelog
