This directory contains spec files for
SNAC/NOX and the OpenFlow codebase, targeting CentOS/RHEL 5.5.


Notes on compiling SNAC/NOX on CentOS 5.5:

sudo rpm -Uv http://blackopsoft.com/el5/RPMS/noarch/blackop-el5-repo-1.0-2.noarch.rpm
sudo rpm -Uv http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
sudo sed -i '/^gpgkey=/a\includepkgs=boost-*,blackop-*,sqlite*,git,perl-Git,swig' /etc/yum.repos.d/blackop.repo
sudo su -c 'echo "exclude=*.i386 *.i586 *.i686" >>/etc/yum.conf' (only on 64-bit host)
sudo sed -i 's/^enabled=.*/enabled=0/g' /etc/yum/pluginconf.d/fastestmirror.conf
sudo yum -y install boost-devel ccache sqlite-devel swig openssl-devel xerces-c-devel libtool automake autoconf rpmdevtools yum-utils \
  emacs-nox gcc-c++ git perl-Error python-sphinx openldap-devel java python-devel python-mako python-twisted-web python-simplejson

git clone git@github.com:bigswitch/snac-nox.git
git clone git@github.com:bigswitch/snac.git snac-nox/src/nox/ext

cd ~/snac-nox
mkdir build
./boot.sh
cd build
../configure --with-python=yes --prefix=/usr --enable-ndebug
make -j4 all
sudo make install


Installing binary rpms:

0. Install CentOS 5.5 (32- or 64-bit)

1. Install yum repo configuration for the EPEL (http://fedoraproject.org/wiki/EPEL)
   and Black Op (http://blackopsoft.com/) repositories:

  $ sudo rpm -Uv http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
  $ sudo rpm -Uv http://blackopsoft.com/el5/RPMS/noarch/blackop-el5-repo-1.0-2.noarch.rpm

2. Configure yum to upgrade only specific rpms from the Black Op repository, ignoring
   others that are incompatible with SNAC:

  $ sudo sed -i '/^gpgkey=/a\includepkgs=boost-*,blackop-*,sqlite*,git,perl-Git,swig' /etc/yum.repos.d/blackop.repo

3. Install the SNAC rpms:

  $ sudo yum --nogpg localinstall openflow-pki-*.rpm snac-*.rpm

4. Start the SNAC nox_core daemon:

  $ sudo service noxcore start

5. Log into the web configuration interface at https://hostname (username admin, password
   admin).


Differences from Debian packaging:

- Files are installed per Red Hat conventions (executables in /usr/bin, libraries and apps in
  /usr/lib*/nox, config files in /etc/nox) rather than in a separate /opt/nox tree.

- Daemon configuration files are /etc/sysconfig/{noxcore,noxext} rather than
  /etc/defaults/{noxcore,noxext}.

- SNAC is built into a single binary rpm (snac-*.rpm) rather than separate packages for
  noxcore and noxext.


Known bugs and missing functionality:

- No init script is provided for the nox-monitor tool.

- The dhcp app does not configure the DHCP daemon properly (config files have different
  names/paths between Debian and Red Hat).

- The notification app does not generate email notifications (Twisted email library is
  not available for CentOS 5).

- The local_config app should write network interface configuration into
  /etc/sysconfig/network-scripts/ifcfg-* but this has not been tested.
