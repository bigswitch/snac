This directory contains work-in-progress spec files for
SNAC/NOX and the OpenFlow codebase, targeting CentOS/RHEL 5.5.


Notes on compiling SNAC/NOX on CentOS 5.5:

sudo rpm -Uv http://blackopsoft.com/el5/RPMS/noarch/blackop-el5-repo-1.0-2.noarch.rpm
sudo rpm -Uv http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
sudo sed -i '/^gpgkey=/a\includepkgs=boost-*,blackop-*,sqlite*,git,perl-Git,swig' /etc/yum.repos.d/blackop.repo
sudo su -c 'echo "exclude=*.i386 *.i586 *.i686" >>/etc/yum.conf'
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
