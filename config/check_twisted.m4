dnl --
dnl CHECK_TWISTED
dnl
dnl Enable use of Twisted python 
dnl --
AC_DEFUN([CHECK_TWISTED], [
  AC_ARG_WITH([python],
              [AC_HELP_STRING([--with-python=/path/to/python.binary],
                              [Specify python binary (must be v2.4 or greater and must have twisted installed)])],
               [path="$withval"], [path="no"])dnl
  if test "$path" = "yes"; then
    AC_PYTHON_DEVEL([>='2.4'])
  elif test -n "$path" & test "$path" != "no"; then
    PYTHON="$path"
    AC_PYTHON_DEVEL([>='2.4'])

    AC_MSG_CHECKING([whether twisted python is installed])
    `$PYTHON -c "import twisted" 2> /dev/null`
    RETVAL=$?
    if (( $RETVAL != 0 )); then
        AC_MSG_RESULT([no])
        AC_ERROR([twisted not installed])
    else
        AC_MSG_RESULT([yes])
    fi

  fi

  if test -n "$PYTHON"; then
    AC_DEFINE(TWISTED_ENABLED,1,[
Provide macro indicating that twisted python was enabled
])
  fi
  AM_CONDITIONAL(PY_ENABLED, test -n "$PYTHON")
])
