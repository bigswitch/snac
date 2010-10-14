/*
 Copyright 2008 (C) Nicira, Inc.

 This file is part of NOX.

 NOX is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 NOX is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */

dojo.provide("nox.ext.apps.coreui.coreui.UpdateErrorHandler");

dojo.require("nox.ext.apps.coreui.coreui.base");

dojo.require("dojo.i18n");
dojo.requireLocalization("nox.ext.apps.coreui.coreui", "UpdateErrors");

(function() {
    var msgs = null;

    var ueh = nox.ext.apps.coreui.coreui.UpdateErrorHandler;
    var errorShown = false;

    ueh.onError = function(error_text,args){};

    ueh.showError = function (error_text,args) {
        ueh.onError(error_text,args);
        errorShown = true;
    };

    var send_to_login_page = function (error, ioArgs) {
                            var loc = document.location;
                            document.location="/login?last_page=" +
                            encodeURIComponent(loc.pathname + loc.search)
                         }; 

    ueh.defaultHandlers = {
        0: function (error, ioArgs) {
            ueh.showError("HTTP connection to " + 
                document.location.host +" failed.",  
                { header_msg : "Server is Unreachable:", 
                  hide_dismiss : true });
        },
        400: function (response, ioArgs) { 
            ueh.showError(response.responseText,    
                { header_msg : "Request Error:" }); 
        }, 
        401: send_to_login_page,
        403: send_to_login_page, // Opera is dumb, converts 401 to 403
        404: function (error, ioArgs) { 
            ueh.showError("The current page/resource does not exist or is inactive", 
                { header_msg : "Page Not Found:"
                }); 
        },
        409: function (response, ioArgs) { 
            ueh.showError(response.responseText,    
                { header_msg : "Server Conflict:" }); 
        }, 
        500: function (response, ioArgs) { 
            ueh.showError(response.responseText,    
                { header_msg : "Server Error:" }); 
        }, 
        "user-dismissed-error": function (error, ioArgs) {
            // This means the user dismissed a retry dialog presented by a
            // previous error.  In almost all cases this should just return
            // false and do nothing else.
            return false;
        },
        timeout: function (error, ioArgs) {
            ueh.showError("Server at "+ document.location.host +" is taking too " + 
                "long to respond.",  
                { header_msg : "Server Timeout:",
                  hide_dismiss : true });
        },
        cancel: function (error, ioArgs) {
            // This should only ever happen deliberately, so ignore it.
            return;
        }
    };

    ueh.get_error_type = function(error) { 
        var err = null;
        if (error.dojoType != null) 
            err = error.dojoType;
        else if (error.status != null) 
            err = error.status;
        return err; 
    };

    ueh.handler = function() {
        var error = arguments[0];
        var err = ueh.get_error_type(error); 
        if(err == null) { 
            console_log("unidentified error, arguments: ", arguments);
            ueh.showError(error.toString(), 
                { header_msg : "Browser Error:", 
                  hide_retry : true }); 
            return true;
        }

        if (this.customHandlers[err] != null) { 
            this.customHandlers[err].apply(this.scope, arguments);
        } else if (ueh.defaultHandlers[err] != null) {
            ueh.defaultHandlers[err].apply(this, arguments);
        } else { 
            console_log("unhandled_error: ", err.toString());
            ueh.showError(err.toString(), 
                { header_msg : "Browser Error:", 
                  hide_retry : true }); 
            return true;
        } 

        if (errorShown) {
            errorShown = false;
            return true;
        }
        return false;
    }

    ueh.create = function (scope, customHandlers) {
        // summary: Create an error handler for xhr requests
        // description:
        //     Most xhr error handlers need to dispatch on the type of
        //     error to determine what to do.  Determining that type
        //     is a little bit complex.  This creates a function that
        //     handles the dispatch automatically. The user only
        //     has to supply handlers for the errors they expect/care
        //     about.  All other errors get a default that tells the
        //     user something unexpected happened.
        //
        // scope:
        //     Scope in which custom error handlers should run.
        // customHandlers:
        //     An object containing properties naming errors mapped
        //     to the corresponding error handler function.  If a
        //     specified error occurs, the handler function will be
        //     called with at least two arguments, the error object
        //     and request object from the xhr error callback.  In
        //     some cases it may be called with additional arguments.
        if (msgs == null)
            msgs = dojo.i18n.getLocalization("nox.ext.apps.coreui.coreui", "UpdateErrors");
        var context = {
            scope: scope,
            defaultHandlers: ueh.defaultHandlers,
            customHandlers: (customHandlers != null) ? customHandlers : {}
        };
        return function () {
            return ueh.handler.apply(context, arguments);
        }
    };

    ueh.kwCreate = function (kwarg) {
        if (kwarg.errorHandlers != undefined)
            return ueh.create(kwarg.scope, kwarg.errorHandlers);
        else if (kwarg.onError != undefined)
            return dojo.hitch(kwarg.scope, kwarg.onError);
        else
            return ueh.create(kwarg.scope, {});
    };

})();
