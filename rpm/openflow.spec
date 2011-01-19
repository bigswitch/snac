Name: openflow
Version: 1.0.0
Release: 1.bigswitch
Summary: OpenFlow

Group: Applications/Networking
License: GPL
Source0: openflow.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: autoconf >= 2.59
BuildRequires: automake >= 1.9.6
BuildRequires: libtool
BuildRequires: openssl-devel
BuildRequires: ncurses-devel
BuildRequires: pcre-devel

%description
OpenFlow

%package pki
Summary: OpenFlow public key infrastructure
Group: Applications/Networking
Requires: openssl

%description pki
openflow-pki provides PKI (public key infrastructure) support for
OpenFlow switches and controllers, reducing the risk of
man-in-the-middle attacks on the OpenFlow network infrastructure.

OpenFlow is a protocol for flow-based control over network switching.

%prep
%setup -q -n openflow
sed -i 's/^AC_PREREQ(2.60)/AC_PREREQ(2.59)/;s/^AC_PROG_MKDIR_P/dnl AC_PROG_MKDIR_P/;/^AM_INIT_AUTOMAKE/a\AC_GNU_SOURCE' configure.ac
sed -i 's/AC_REQUIRE(\[AC_USE_SYSTEM_EXTENSIONS\])/dnl AC_REQUIRE([AC_USE_SYSTEM_EXTENSIONS])/' m4/libopenflow.m4
sed -i 's/$(MKDIR_P)/mkdir -p/g' lib/automake.mk

%build
touch debian/automake.mk
autoreconf --install --force
%configure --enable-ssl --enable-snat
make %{?_smp_mflags}

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
rm -f $RPM_BUILD_ROOT%{_bindir}/{controller,dpctl,ofdatapath,ofp-discover,ofp-kill,ofprotocol,vlogconf}
rm -f $RPM_BUILD_ROOT%{_mandir}/man8/{controller,dpctl,ofdatapath,ofp-discover,ofp-kill,ofprotocol,vlogconf}.8*
rm -f $RPM_BUILD_ROOT%{_datadir}/openflow/commands/reboot

%clean
rm -rf $RPM_BUILD_ROOT

%post pki
if ! test -d /usr/share/openflow/pki; then
    ofp-pki init
fi
true

%files pki
%defattr(-,root,root,-)
%doc COPYING ChangeLog
%{_bindir}/ofp-pki
%{_mandir}/man8/ofp-pki.8*
%dir %{_localstatedir}/log/openflow

%changelog
