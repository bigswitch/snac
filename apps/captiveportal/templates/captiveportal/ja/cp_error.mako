## -*- coding: utf-8 -*-
##
## cp_error.mako - captive portal page displayed when an
##                 unexpected error occurs
##  
<div id="error">
  <div class="errorMsg">
    ネットワークエラーが発生しました。ネットワーク管理者にお問い合わせください。
  </div>
</div>
\
## ---------------------------------------------------------------------------
<%inherit file="cp_base.mako"/>
\
<%def name="page_title()" filter="trim">
ネットワークエラー
</%def>\
