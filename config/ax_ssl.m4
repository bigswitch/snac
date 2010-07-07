AC_DEFUN([CHECK_SSL], [
AC_CHECK_HEADER([openssl/md5.h],
     ,
    AC_ERROR([openssl/md5.h not found. NOX requires OpenSSL])
)
AC_CHECK_LIB(ssl, MD5_Init,
             [SSL_LIBS="-lssl"; AC_SUBST(SSL_LIBS) break],
             [AC_ERROR([openssl/md5.h not found. NOX requires OpenSSL])])
])
