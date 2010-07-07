## -*- coding: utf-8 -*-
##
## cp_success.mako - captive portal page displayed in main window
##                   after successfull authentication
## 
<div id="heading">
  <div id="successMsg">
    <H1>ログインに成功しました。</H1>
  </div>
% if username:
  <div id="successStatusMsg">
    '${username}'でログイン中です。
  </div>
%endif
</div>

<div id="redirMsg">
%if rurl != '':
  <div>
    <A href="${rurl}">${rurl_disp}</A> へ自動転送されます。
  </div>
  <div>
    自動転送されない場合、<A href="${rurl}">ここ</A> をクリックするか、再送信してください。
  </div>
%else:
    ネットワークにアクセス可能になりました。
%endif
</div>
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
ログインに成功しました。
</%def>\
\
<%def name="meta_tags()" filter="trim">
%if rurl != '':
  <meta http-equiv="refresh" content="2;url=${rurl}">
%endif
</%def>\
