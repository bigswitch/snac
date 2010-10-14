/*
 * Copyright 2008 (C) Nicira
 */
dojo.provide("nox.ext.apps.snackui.snackmonitors.NetEventsMon");
dojo.require("nox.ext.apps.user_event_log.networkevents.NetEvents");

dojo.addOnLoad(function() {
        var log = new nox.ext.apps.user_event_log.networkevents.NetEventsTable( 
                    dojo.byId("netevents-table"), 2000, "max_level=5"); 
});
