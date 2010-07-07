## -*- coding: utf-8 -*-
##
## auth_logout.mako - captive portal authentication page
##  
% if logout is True:
    You have been logged out.
    ${close_window_form()}
% else:
    You are logged in as <I>${username}.</I>
    % if not is_popup:
        ##A popup window failed to load.  If you have a popup blocker, disable it and click <A HREF="" onClick="return lopu(lo_form)">here</A>.
        ##A popup window failed to load.  If you have a popup blocker, disable it and click <A HREF="" onClick="alert('Not yet supported')">here</A>.
        <br>
        You will be logged out if you navigate away from this page or close this window.
      % if redir_url:
        To view your <A HREF="${redir_url}" target="_blank">orginional destination</A>
        in a new window, click <A HREF="${redir_url}" target="_blank">here</A>.
      % endif
    % endif
    ${logout_form()}
% endif
\
## ---------------------------------------------------------------------------
<%inherit file="auth_base.mako"/>
\
##<%def name="meta_tags()">
##%if redir_url != None:
  ##<meta http-equiv="refresh" content="5;url=${redir_url}"/>
##%endif
##</%def>
\
<%def name="page_title()" filter="trim">${c.org_name} Network Authentication</%def>
\
<%def name="body_args()" filter="trim">
% if is_popup and not logout:
##TODO: always redirect to success
  % if redir_url:
    onload="redirectParent('${redir_url}'); focus()" \
  % else:
    onload="redirectParent('${r.success}'); focus()" \
  % endif
% endif
% if logout is not True:
  ## TODO: This doesn't work
  onunload="document.forms[0].submit();" \
%endif
</%def> \
\
<%def name="logout_form()" filter="trim">
  <form name="lo_form" action="${r.do_logout}" method="post">
    <div id="logout_form">
    ${self.ses_post_form_inputs()}
    <table cellspacing="0" border="0" style="padding: 0px; padding-top: 2px;">
      <tr>
        <td align="center">
          ##XXX: If no JS, closing window relies on inactivity timeout
          Close this window or click below to Log Out.
        </td>
      </tr> <tr>
        <td height="35" align="center" valign="bottom">
          <button name="Log Out" type="submit" tabindex="1">Log Out</button>
        </td>
      </tr>
    </table>
    </div>
  </form>
</%def> \
\
<%def name="close_window_form()" filter="trim">
  ## TODO: Only display logout button if JS is enabled
  ##<script type="text/javascript">
  ##<!-- //
  <form action="0">
    <input type="button" value="Close Window" onclick="window.close()">
  </form>
</%def> \
\
##<%def name="postfooter()" filter="trim">
##  ##if logout, we should refresh and close on login
##  <iframe id="session_refresh"
##    name="session_refresh" style="width:0px; height:0px; border:0px"
##    src="/auth/session_refresh">
##  </iframe>
##</%def> \
