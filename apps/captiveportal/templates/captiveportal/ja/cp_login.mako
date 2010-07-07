## -*- coding: utf-8 -*-
##
## cp_login.mako - captive portal page displayed in main window
##                 before authentication
##
## ---------------------------------------------------------------------------
% if hasattr(session, "server_message"):
<div class="serverMsg">
${session.server_message}
</div>
% endif
\
<div id="heading">
<h1>アクセス認証が必要です</h1>
</div>
\
% if login_failed == True:
<div class="errorMsg">
ログインに失敗しました。入力内容をもう一度ご確認ください。
</div>
% endif
\
<div id="loginMsg">
このネットワークにアクセスするためログインが必要です。
</div>
\
% if p('banner'):
<div id="bannerMsg">
${p('banner')}
</div>
% endif
\
${login_form()}\
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
% if p('org_name') is not None:
${p('org_name')} ネットワークアクセス認証
% else:
ネットワークアクセス認証
% endif
</%def>\
\
<%def name="body_args()" filter="trim">
% if not preview:
onload="redirOnTrue('${r['auth_check']}', '', '${r['root']+'?rurl='+rurl}', '${p('auth_check_interval_sec')*1000}')"
% endif
</%def>\
\
<%def name="head_ext()" filter="trim">
  <script type="text/javascript">
    in_progress_message="ログインしています。お待ちください。";
  </script>
</%def>\
\
## Login form used here and on the access denied pages.
<%def name="login_form()" filter="trim">
<div id="loginForm">
% if preview:
  <form id="login" name="login" action="" onSubmit="return false;" method="post">
% else:
  <form id="login" name="login" action="${r['root']}" method="post" onSubmit="return disableLogin(this);">
% endif
    <table id="loginTable">
      <tr>
        <td align="right">ユーザ名:</td>
        <td><input type="text" name="username" tabindex="1" class="textinput"></td>
      </tr>
      <tr>
        <td align="right">パスワード:</td>
        <td><input type="password" name="password" tabindex="2" class="textinput"></td>
      <tr>
        <td align="center" colspan="2">
        <input name="ログイン" type="submit" tabindex="3" value="ログイン">
        </td>
      </tr>
    </table>
    <input type="hidden" name="rurl" value="${rurl}">
    <input type="hidden" name="proxy_cookie" value="${proxy_cookie}">
  </form>
</div>
</%def>\
\
