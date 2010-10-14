/* Copyright 2008 (C) Nicira, Inc. */

dojo.provide("nox.ext.apps.snackui.settingsui.ControllerInterfaceStore");

dojo.require("nox.ext.apps.directory.directorymanagerws._PrincipalStore");
dojo.require("nox.ext.apps.snackui.settingsui.ControllerInterface");

dojo.declare("nox.ext.apps.snackui.settingsui.ControllerInterfaceStore", [ nox.ext.apps.directory.directorymanagerws._PrincipalStore ], {

    constructor: function (kwarg) {
        this.itemConstructor = 
            nox.ext.apps.snackui.settingsui.ControllerInterface;
    }

});
// Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.ext.apps.snackui.settingsui.ControllerInterfaceStore,
            dojo.data.util.simpleFetch);
