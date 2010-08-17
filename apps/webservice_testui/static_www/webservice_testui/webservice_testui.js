dojo.require("nox.webapps.coreui.coreui.base");

var coreui = nox.webapps.coreui.coreui

function set_response_headers(str) {
    var widget = dijit.byId("response_headers");
    widget.setValue(str)
}

function set_response_body(content_type, content) {
    var widget = dijit.byId("response_body");
    var t = content
    if (content_type == "application/json") {
        // This is a lot of effort for the computer but makes it easy for
        // me to get a pretty-printed version of whatever json is sent
        // from the server.
        dojo.toJsonIndentStr="  ";
        j = dojo.fromJson(t);
        t = dojo.toJson(j, true);
    }
    if (content_type != "text/html") {
        t = "<pre>" + t.replace(/[<>&]/g, function(s) {
            if (s == "<")
                return "&lt;";
            else if (s == ">")
                return "&gt;";
            else if (s == "&")
                return "&amp;";
            else
                return s;
        }) + "</pre>";
    } else {
        // Remove page header.
        t = t.replace(/^.*<body>([\s\S]*)<\/body>/i, "$1");
        // Remove style information
        t = t.replace(/<style(>|\s[^>]*>)[\s\S]*?<\/style>/ig, "");
    }
    widget.setContent(t);
}

function clear_response_data() {
    set_response_headers("");
    set_response_body("text/plain", "");
}

function request_ok(response, ioArgs) {
    var msg = ioArgs.xhr.status + " " + ioArgs.xhr.statusText
    coreui.base.update_status_msg(msg, "successmsg");
    set_response_headers(ioArgs.xhr.getAllResponseHeaders());
    set_response_body(ioArgs.xhr.getResponseHeader("content-type"), ioArgs.xhr.responseText);
    coreui.base.update_status_msg("Request completed successfully.", "successmsg");
}

function request_err(response, ioArgs) {
    var msg = ioArgs.xhr.status + " " + ioArgs.xhr.statusText
    coreui.base.update_status_msg(msg, "errormsg");
    set_response_headers(ioArgs.xhr.getAllResponseHeaders());
    set_response_body(ioArgs.xhr.getResponseHeader("content-type"), ioArgs.xhr.responseText);
}

function submit_request() {
    coreui.base.update_status_msg("Preparing request...", "normalmsg");
    clear_response_data();
    var req = dijit.byId("request_method_and_path").getValue();
    var m = req.match(/^\s*(\S+)\s+(\S.*)$/);
    if (m == null) {
        coreui.base.update_status_msg("Valid request method & uri not found.  Request aborted.", "errormsg");
        return
    }
    var method = m[1].toUpperCase();
    var path = m[2];
    var content_type = dijit.byId("request_content_type").getValue();
    var msgbody = dijit.byId("request_body").getValue();
    coreui.base.update_status_msg("Submitted request, waiting for response...", "normalmsg");
    if (method == "PUT") {
        dojo.rawXhrPut({
            url: path,
            headers: { "content-type": content_type },
            putData: msgbody,
            timeout: 5000,
            load: request_ok,
            error: request_err
        });
    } else if (method == "POST") {
        dojo.rawXhrPost({
            url: path,
            headers: { "content-type": content_type },
            postData: msgbody,
            timeout: 5000,
            load: request_ok,
            error: request_err
        });
    } else {
        dojo.xhr(method, {
            url: path,
            timeout: 5000,
            load: request_ok,
            error: request_err
        }, false);
    }
}

function attach_keypress_handler() {
    var enter_widgets = [ dojo.byId("request_method_and_path"),
                          dojo.byId("request_content_type") ]
    for (n in  enter_widgets) {
        dojo.connect(enter_widgets[n], "onkeypress", function(evt) {
            if (evt.keyCode == dojo.keys.ENTER)
                submit_request();
        });
    }
}
