/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.log");

dojo.require("nox.webapps.coreui.coreui.base");
dojo.require("nox.webapps.coreui.coreui.UpdateMgr");
dojo.require("nox.webapps.coreui.coreui.UpdateErrorHandler");

var coreui = nox.webapps.coreui.coreui;

var cancel_token = null;

var restore_id = null;

function download() {
    
}

function poll(response) {
    if (response == 'error') {
        dojo.byId("prepare").style.display = 'none';
        dojo.byId("download").style.display = 'none';
        dojo.byId("error").style.display = 'block';
        dojo.byId("dumping").style.display = 'none';

        coreui.getUpdateMgr().cancelUpdate(cancel_token);

    } else if (response == 'complete') {
        dojo.byId("prepare").style.display = 'none';
        dojo.byId("download").style.display = 'block';
        dojo.byId("error").style.display = 'none';
        dojo.byId("dumping").style.display = 'none';

        coreui.getUpdateMgr().cancelUpdate(cancel_token);
    } else if (response == 'dumping') {
        dojo.byId("prepare").style.display = 'none';
        dojo.byId("download").style.display = 'none';
        dojo.byId("error").style.display = 'none';
        dojo.byId("dumping").style.display = 'block';
    }
}

function initiated() {
    cancel_token = coreui.getUpdateMgr().xhrGet({
            url : "/ws.v1/nox/dump/status",
            load: this.poll,
            error: coreui.UpdateErrorHandler.create(),
            timeout: 30000,
            handleAs: "json",
            recur: true
        });
}

function prepare() {
    var put_obj = {
        url: "/ws.v1/nox/dump/status",
        headers: { "content-type" : "application/json" },
        putData: dojo.toJson('initiate'),
        load : dojo.hitch(this, initiated),
        timeout: 1000000, // 1 second
        errorHandlers: this._put_error_handlers
    };

    coreui.getUpdateMgr().rawXhrPut(put_obj);
}

function snapshot() {
    var put_obj = {
        url: "/ws.v1/nox/snapshot",
        headers: { "content-type" : "application/json" },
        putData: dojo.toJson('initiate'),
        handleAs: "json",
        load : dojo.hitch(this, show_snapshot),
        timeout: 1000000, // 1 second
        errorHandlers: this._put_error_handlers
    };

    coreui.getUpdateMgr().rawXhrPut(put_obj);
}

function show_snapshot(response) {
    var table = dojo.byId("snapshots-table"); 
    var cls = "rowclass" + (table.rows.length % 2);  
    var row = table.insertRow(1);
    dojo.addClass(row, cls); 
    var dt = new Date(response.timestamp * 1000);
    row.innerHTML = "<td>" + dt.toLocaleDateString() + "   " + 
          dt.toLocaleTimeString() + "</td>" + 
        '<td><a id="restore_' +response.id +'"> restore now </a></td>'

    dojo.byId("restore_" + response.id).onclick = function() {
        // Before restoring, ask for confirmation
        restore_id = response.id;
        dijit.byId("restore_confirmation_dialog").show();
    };
}

function restore() {
    var put_obj = {
        url: "/ws.v1/nox/snapshot/" + restore_id,
        headers: { "content-type" : "application/json" },
        putData: dojo.toJson('restore'),
        handleAs: "json",
        timeout: 1000000, // 1 second
        errorHandlers: this._put_error_handlers
    };

    coreui.getUpdateMgr().rawXhrPut(put_obj);
}

function show_snapshots(response) {
    for (var i = 0; i < response.length; i++) { 
        show_snapshot(response[i]);
    }
    // hide update spinner 
    nox.webapps.coreui.coreui.getUpdateMgr()._recurring_updates = [];  
}

function init_page() {
    dojo.byId("prepare").style.display = 'block';
    dojo.byId("download").style.display = 'none';
    dojo.byId("error").style.display = 'none';
    dojo.byId("dumping").style.display = 'none';

    coreui.getUpdateMgr().xhrGet({
        url : "/ws.v1/nox/snapshot",
        load: dojo.hitch(this, show_snapshots),
        error: coreui.UpdateErrorHandler.create(),
        timeout: 30000,
        handleAs: "json",
        recur: false
    });
}

dojo.addOnLoad(init_page);
