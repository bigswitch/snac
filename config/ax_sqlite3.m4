AC_DEFUN([CHECK_SQLITE3], [
AC_CHECK_HEADER([sqlite3.h],
     ,
    AC_ERROR([libsqlite3 is not installed])
)
    SQLITE3_LIB="-lsqlite3"
    AC_SUBST(SQLITE3_LIB)
])
