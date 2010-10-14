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

dojo.provide("nox.ext.apps.coreui.coreui.UpdateMgr")
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");

var corui = nox.ext.apps.coreui.coreui; 

dojo.declare("nox.ext.apps.coreui.coreui.UpdateMgr", [], {

    dojo_xhr_functions: {
        "GET" : dojo.xhrGet,
        "PUT" : dojo.rawXhrPut,
        "POST" : dojo.rawXhrPost,
        "DELETE" : dojo.xhrDelete
    },

    constructor: function () {
        this.recurrence_period = 10;
        this._suspended = false;
        this._period_remaining = null;
        this._current_timeout = null;
        this._pending_updates = [];
        this._current_update = null;
        this._pending_processing = [];
        this._recurring_updates = [];
        this._mousemove_timeout = null;
        this._retry_pending = false;
        // These closures are required to get around the fact that timeouts
        // happen only in the scope of the Window object...
        // TBD: replace closures in class with dojo.hitch() ???
        var o = this;
        this._countdown_timeout_handler = function () {
            o._handle_countdown_timeout();
        };
        this._processing_timeout_handler = function () {
            o._handle_processing_timeout();
        };
        this._suspend_timeout_handler = function() {
            o._make_request();
            o._setup_timeout();
        };
        this._mousemove_timeout_handler = function () {
            o._mousemove_timeout = null;
            o.resume();
        };
        this._suspend_on_mousemove_handler = function () {
            o.suspend();
            if (o._mousemove_timeout != null)
                clearTimeout(o._mousemove_timeout);
            o._mousemove_timeout = setTimeout(o._mousemove_timeout_handler, 500);
        };
    },

    _call_user_fn: function (args) {
        if (typeof(args.fn) != "function")
            throw Error("Call update method must provide function to call in the fn parameter");
        if (typeof(args.purpose) != "string")
            throw Error("Call update method must provide string describing reason for call in the purpose parameter"); 
        var data = args.data;
        var scope = args.scope;
        if (scope == null)
            scope = dojo.global;
        var response = args.fn.call(scope, data);
        args.load.call(this, response, args)
    },

    _make_request: function () {
        if (this._current_update != null
            || this._pending_updates.length == 0) {
            return;
        }
        if (this._current_timeout != null) {
            clearTimeout(this._current_timeout);
            this._current_timeout = null;
        }
        if (this._suspended == true) {
            return;
        }
        this._period_remaining = null;
        this._current_update = this._pending_updates.shift();
        with (this._current_update) {
            if (request_method != "USERFN") {
                if (args.url_fn != null) {
                    args.url = args.url_fn();
                }
                this.onMakeRequest(request_method, args.url);
            } else {
                this.onUserFunctionCall(args.purpose);
            }
            this._current_update.request = xhr_fn.call(this, args);
        }
    },

    _handle_countdown_timeout: function() {
        if (this._current_timeout == null || this._period_remaining == null) {
            // TBD: Why does this sometimes happen?
            return;
        }
        this._current_timeout = null;
        this.onCountdownTick(--this._period_remaining);
        if (this._period_remaining == 0) {
            this._period_remaining = null;
            for (var i = 0; i < this._recurring_updates.length; i++) {
                this._pending_updates.push(this._recurring_updates[i]);
            }
            this._make_request();
        }
        this._setup_timeout();
    },

    _handle_processing_timeout: function() {
        var min_progress = 100;
        this._current_timeout = null;
        if (this._suspended == false) {
            var l = this._pending_processing;
            this._pending_processing = [];
            for (var i = 0; i < l.length; i++) {
                var c = l[i].work.next_fn(l[i].work.state);
                if (c != null) {
                    if (c.progress == null
                        || c.progress < 0 || c.progress > 100) {
                        throw Error("Long-running processing didn't set progress correctly");
                        l[i].work = c;
                        this._pending_processing.push(l[i]);
                    } else if (c.progress < 100) {
                        l[i].work = c;
                        this._pending_processing.push(l[i]);
                    }
                    min_progress = Math.min(min_progress, c.progress);
                }
            }
            if (this._current_update == null
                && this._pending_updates.length == 0) {
                this.onResponseProcessingTick(this._pending_processing, min_progress);
            }
        }
        this._setup_timeout();
    },

    _setup_timeout: function () {
        if (this._current_timeout != null) {
            /* Safety check: this does happen occasionally */
            clearTimeout(this._current_timeout);
            this._current_timeout = null;
            this._period_remaining = null;
        }
        if (this._pending_processing.length > 0) {
            /* Need to continue response processing */
            this._current_timeout = setTimeout(this._processing_timeout_handler, 1);
        } else if (this._current_update != null) {
            /* No timeout is required, we are waiting for a callback from
             * an in-progress request.
             */
            return;
        } else if (this._pending_updates.length > 0) {
            /* No outstanding response processing but waiting to unsuspsend
             * to continue work already queued.
             */
            if (! this._suspended) {
                this._make_request();
                return;
            }
            this._current_timeout = setTimeout(this._suspend_timeout_handler, 100);
        } else if (this._recurring_updates.length > 0) {
            /* Doing countdown */
            if (this._period_remaining == null) {
                this.onCountdownStart(this.recurrence_period);
                this._period_remaining = this.recurrence_period;
            }
            this._current_timeout = setTimeout(this._countdown_timeout_handler, 1000);
        } else {
            /* There is nothing left to do, processing is complete. */
            this.onUpdateComplete();
        }
    },

    _initial_response_processing: function (state) {
        if (state.cb_fn != null)
            return state.cb_fn.call(null, state.response, state.ioArgs);
        return null;
    },

    _check_response_processing_start: function () {
        if (this._pending_processing.length > 0) {
            if (this._current_update == null
                && this._pending_updates.length == 0)
                this.onResponseProcessingStart(this._pending_processing);
            this._handle_processing_timeout();
        }
    },

    _handle_response_callback: function (response, ioArgs, cb_fn) {
        this._pending_processing.push({
            update: this._current_update,
            work: {
                progress: 0,
                next_fn: this._initial_response_processing,
                state: {
                    "cb_fn": cb_fn,
                    "response": response,
                    "ioArgs": ioArgs
                }
            }
        });
        this._current_update = null;
        this._make_request();
        this._check_response_processing_start();
    },

    _handle_error_callback: function (response, ioArgs, err_fn) {
        if (! err_fn.call(null, response, ioArgs)) {
            // Retry is not neccessary, continue with other pending requests
            // We push a dummy work entry on _pending_processing so that
            // the existing code can be used to create the appropriate calls
            // to extension points.
            this._pending_processing.push({
                update: this._current_update,
                work: {
                    progress: 0,
                    next_fn: function (state) { return null },
                    state: {}
                }
            });
            this._current_update = null;
            this._make_request();
            this._check_response_processing_start();
        } else {
            // Retry might be attempted, leaving pending requests queued.
            this._retry_pending = true;
        }
    },

    _wrap_callbacks: function (args) {
        var o = this;
        var loadCB = args.load;
        args.load = function (rsp, ioArgs) {
            o._handle_response_callback(rsp, ioArgs, loadCB);
        };
        var errorCB = args.error;
        args.error = function (rsp, ioArgs) {
            o._handle_error_callback(rsp, ioArgs, errorCB);
        };
        return args;
    },

    retry_failed_request: function () {
        /* Retry a request that failed with an error
         *
         * This is only possible if the error handling function that
         * was run when the error occured returned true to indicate that
         * a retry was neccessary. It will be ignored in other
         * circumstances. */
        if (! this._retry_pending)
            return;
        this._retry_pending = false;
        this._pending_updates.unshift(this._current_update);
        this._current_update = null;
        this._make_request();
        this._check_response_processing_start();
    },

    skip_failed_request: function () {
        /* Skip a request that failed with an error
         *
         * This is only possible if the error handling function that
         * was run when the error occured returned true to indicate that
         * a retry was neccessary. It will be ignored in other
         * circumstances.
         *
         * In this case, the error handler for the request will be called
         * again with the error type set to "user-dismissed-error".
         **/
        if (! this._retry_pending)
            return;
        if (this._current_update.args.error != undefined) { 
            this._current_update.args.error.call(null, 
                  { status: "user-dismissed-error" }, 
                  this._current_update.args);
        }
        this._retry_pending = false;
        this._current_update = null;
        this._setup_timeout();
    },

    xhr: function (request_method, args) {
        /* Register a request to be made.
         *
         * The request_method argument is one of the strings that
         * indicate the type of request to be made:
         *
         *       GET: dojo.xhrGet()
         *       PUT: dojo.rawXhrPut()
         *      POST: dojo.rawXhrPost()
         *    DELETE: dojo.xhrDelete()
         *
         * Args is an argument object.  It can have all the properties
         * used by the requested dojo xhr method (it will be passed to it)
         * as well as:
         *
         *        recur: If present and true, request will be resent
         *               periodically.
         *       url_fn: Function to determine URL instead of using
         *               the url property.  The url property will be
         *               overwritten with the result returned by
         *               this function.  If this is not present, the
         *               url property will be used as is.
         *
         * The passed in dojo xhr load and error callback function
         * properties are wrapped to handle sequencing requests to the
         * server and providing feedback.  The wrappers also provide some
         * new functionality to assist with long-running processing.
         * The passed in version of the functions can return an object
         * with the following properties:
         *
         *      next_fn: Function to call to continue processing
         *        state: Whatever state next_fn needs to continue
         *               processing.  It will be called with this
         *               as its' sole argument.
         *     progress: Percentage of processing completed so far.
         *
         * As long as progress is less than 100, UpdateMgr will
         * delay a short period to allow for browser updates, etc.
         * and then call next_fn(state) to continue processing.
         *
         * In addition to the xhr methods described above, an additional
         * special purpose method with type "USERFN" was added as well.  In
         * this method, the only meaningful properties of the argument
         * object are:
         *
         *           fn: The function to call
         *        scope: Scope in which the user function should run
         *         data: Optional user supplied data to supply as the only
         *               argument to fn.  If this is not specified, null
         *               will be passed.
         *         load: An optional function to be called with the result
         *               of the user function.  It has the same arguments
         *               and supported functionality as the xhr load
         *               argument where the response argument is replaced
         *               by the data returned by the function call.  This
         *               will most likely only be used if large amounts of
         *               background processing managed by the UpdateMgr
         *               long-running processing functionality is required
         *               as otherwise all processing can be done in the
         *               called function itself.  This is important because
         *               the user function runs synchronously (as opposed
         *               to the all the other methods) and thus will "hang"
         *               the browser if it does large amounts of work.
         *
         * An object that should be opaque to the user is returned from
         * this function.  This object can be passed into the
         * cancelUpdate() function to step pending and recurring updates
         * for this specific request.
         */
        if (this._pending_updates.length == 0
            && this._pending_processing.length == 0
            && this._recurring_updates.length == 0
            && this._current_update == null)
            this.onUpdateStart();
        var method = request_method.toUpperCase();
        if  (method == "USERFN") {
            var fn = this._call_user_fn;
        } else {
            fn = this.dojo_xhr_functions[method];
            if (args.errorHandlers != null)
                args.error = coreui.UpdateErrorHandler.create(null, args.errorHandlers);
            if (args.error == null) {
                console_log("FIXME: caller didn't install error handler for request: ", 
                                        request_method, " ", args);
                args.error = coreui.UpdateErrorHandler.create();
            }
        }
        if (fn == null)
            throw Error("Unknown update method");
        var update = {
            "request_method": request_method.toUpperCase(),
            "xhr_fn": fn,
            "args": this._wrap_callbacks(args),
            "cancel": dojo.hitch(this, function () {
                this.cancelUpdate(update);
            })
        }
        if (args.recur != null && args.recur == true)
            this._recurring_updates.push(update);
        this._pending_updates.push(update);
        this._make_request();
        return update;
    },

    xhrGet: function (args) {
        /* Convenience wrapper of xhr() to issue get request */
        return this.xhr("GET", args);
    },

    rawXhrPut: function (args) {
        /* Convenience wrapper of xhr() to issue put request */
        return this.xhr("PUT", args);
    },

    rawXhrPost: function (args) {
        /* Convenience wrapper of xhr() to issue post request */
        return this.xhr("POST", args);
    },

    xhrDelete: function (args) {
        /* Convenience wrapper of xhr() to issue delete request */
        return this.xhr("DELETE", args);
    },

    userFnCall: function (args) {
        return this.xhr("USERFN", args);
    },

    cancelUpdate: function (update_handle) {
        /* Cancel a pending and/or recurring update by the handle returned
           when the update was scheduled. */
        this._pending_updates = dojo.filter(this._pending_updates, function (i) {
            return i != update_handle;
        });
        this._recurring_updates = dojo.filter(this._recurring_updates, function (i) {
            return i != update_handle;
        });
    },

    cancelRecurring: function () {
        /* Cancel all recurring updates. */
        this._recurring_updates = [];
    },

    cancelPending: function () {
        /* Stop all pending updates. */
        if (this._current_update != null) {
            this._current_update.request.cancel();
            this._current_update = null;
        }
        this._pending_updates = [];
    },

    cancelProcessing: function () {
        /* Stop all outstanding response processing. */
        this._pending_processing = [];
    },

    cancelAll: function () {
        /* Cancel all everything. */
        this.cancelRecurring();
        this.cancelPending();
        this.cancelProcessing();
    },

    suspend: function () {
        /* Suspend all updates and response processing. */
        if (this._suspended == false) {
            this._suspended = true;
            this.onSuspend();
        }
    },

    resume: function () {
        /* Continue all processing after it was suspended. */
        if (this._suspended == true) {
            this._suspended = false;
            this.onResume();
        }
    },

    suspendDuringMousemoveOn: function (/* DOM elem */ e) {
        dojo.connect(e, "mousemove", this, "_suspend_on_mousemove_handler");
    },

    updateNow: function () {
        /* Skip any remaining countdown and force an update now. */
        if (this._period_remaining == null) {
              if(this._pending_updates.length > 0) {
                return;
            }
        }
        if (this._current_timeout != null)
            clearTimeout(this._current_timeout);
        this._period_remaining = 1;
        this._current_timeout = 0;
        this._handle_countdown_timeout();
    },

    onUpdateStart: function () {
        /* Function called before updates start. */
    },

    onUpdateComplete: function () {
        /* Function called when update is complete.  An update is
         * complete only when there are no pending recurring updates
         * and all current updates have been completed.
         */
    },

    onMakeRequest: function (/*string*/ method,  /*string*/ uri) {
        /* Function called before each request to the server. */
    },

    onUserFunctionCall: function (/*string*/ purpose) {
    },

    onResponseProcessingStart: function (/* list */ in_progress_responses) {
        /* Function called when response to all requests have been received
         * and processing of responses is pending.
         */
    },

    onResponseProcessingTick: function(/* list */ in_progress_responses, /* number (range 0-100) */ min_progress) {
        /* Function called each time long-running processing is started */
    },

    onCountdownStart: function (/*int*/ period) {
        /* Function called on start of countdown to next recurring update. */
    },

    onCountdownTick: function (/*int*/ remaining_period) {
        /* Function called during countdown to next recurring update. */
    },

    onSuspend: function () {
        /* Function called when processing is suspended. */
    },

    onResume: function() {
        /* Function called when proccessing resumes after being suspended. */
    },

    installDebugLogging: function () {
        dojo.connect(this, "onUpdateStart", function () {
            console_log("UpdateMgr: Starting update");
        });
        dojo.connect(this, "onUpdateComplete", function () {
            console_log("UpdateMgr: Update compeleted");
        });
        dojo.connect(this, "onMakeRequest", function (method, uri) {
            console_log("UpdateMgr: Making request: ", method, " ", uri);
        });
        dojo.connect(this, "onUserFunctionCall", function (purpose) {
            console_log("UpdateMgr: calling user function for ", purpose);
        });
        dojo.connect(this, "onResponseProcessingStart", function (in_progress_responses) {
            console_log("UpdateMgr: Starting response processing on:", in_progress_responses);
        });
        dojo.connect(this, "onResponseProcessingTick", function (in_progress_responses, min_progress) {
            console_log("UpdateMgr: Continuing response processing on: ", in_progress_responses);
            console_log("UpdateMgr: minimum progress of processing jobs is: ", min_progress);
        });
        dojo.connect(this, "onCountdownStart", function (period) {
            console_log("UpdateMgr: Starting update delay countdown of ", period, " seconds");
        });
        dojo.connect(this, "onCountdownTick", function (remaining_period) {
            console_log("UpdateMgr: Counting down delay, ", remaining_period, " seconds remaining.");
        });
        dojo.connect(this, "onSuspend", function () {
            console_log("UpdateMgr: updates suspended");
        });
        dojo.connect(this, "onResume", function () {
            console_log("UpdateMgr: updates resumed");
        });
    }

});

(function () {
    var updatemgr = null;
    nox.ext.apps.coreui.coreui.getUpdateMgr = function () {
        if (updatemgr == null) {
            updatemgr = new nox.ext.apps.coreui.coreui.UpdateMgr();
        }
        return updatemgr;
    }
})();

