## -*- coding: utf-8 -*-
##
## auth_success.mako - captive portal auth page displayed in main window
##                     after successfull authentication
## 
%if username:
<p>${username}でログイン中です。</p>
%else:
<h3>ログインに成功しました。</h3>
%endif
<table>
  <tr>
    <td width="540"align="center">
%if redir_url != None:
    <A href="${redir_url}"> へ自動転送されます。
    自動転送されない場合、<A href="${redir_url}">ここ</A> をクリックするか、再送信してください。
    </td>
  </tr>
%else:
    ネットワークにアクセス可能になりました。
%endif
    </td>
  </tr>
</table>

## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
<%def name="page_title()">Log in Successful</%def>

<%def name="meta_tags()">
%if redir_url != None:
  <meta http-equiv="refresh" content="3;url=${redir_url}"/>
%endif
</%def>

