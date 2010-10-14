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

dojo.provide("nox.ext.apps.coreui.coreui._UpdatingItem");

dojo.require("nox.ext.apps.coreui.coreui.base");
dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");

dojo.declare("nox.ext.apps.coreui.coreui._UpdatingItem", [], {
    // summary: Base class for objects that can update themselves.
    // description:
    //    This class provides some support for objects representing
    //    data as key/value pairs in a dictionary to automatically
    //    update that data.  It is mostly intended to be used for
    //    items that will be used in _UpdatingStore subclasses,
    //    but can be used for standalone objects as well.

    coreui: nox.ext.apps.coreui.coreui,

    // identityAttributes: a list of attribute names used to form
    // the identity of the item.  As combined by getIdentity(),
    // they *must* be unique for all values the store can hold.
    identityAttributes: [],

    // labelAttributes: a list of attribute names used to form
    // the label for an item.
    labelAttributes: [],


    constructor: function (/* Object */ kwarg) {
        // summary: Constructor
        //
        // keywordParameters: {initialData: object}
        //     Initial data key/value pairs for the object.
        // keywordParameters: {store: object}
        //     A store with which to associate the object.
        // keywordParameters: {initialGeneration: number}
        //     Initial generation.  The item keeps a generation count,
        //     which is incremented every time update() is called.
        //     this lets you set a non-zero generation number.
        // keywordParameters: {updateList: array}
        //     List of types of data to update when the
        //     update method is called.  The available update
        //     types are available as the keys of the updateTypes
        //     property.  Note that the updateList is processed in the
        //     order the desired updateTypes are specified.  There are
        //     some cases where there are dependencies between the
        //     update types.  See the documentation for individual
        //     updateType load/save functions for further information.

        // Establish default values
        this.initialized = false;
        this.initialData = {};
        this.store = null;
        this.generation = 0;
        this.updateList = [];
        this.timeout = 30000;
        this.localChanges = [];

        // updateTypes: an object mapping an update type name to a
        // an object containing two properties, "load" and "save", each
        // of which are functions to perform the corresponding update.
        // These functions are called in the context of the current
        // object with no arguments.  If they require asynchronous
        // processing they should return a deferred and call the callback
        // with no parameters when complete.  They should use the errhandler
        // property of the last object in the this._inProgressUpdates array.
        // There is a method defined to simplify writing such updates,
        // called _xhrGetMixin().
        this.updateTypes = {};

        // derivedAttributes: an object mapping an attribute name
        // to another object with the properties defining functions
        // that implement operations on the attributes.  All functions
        // are run with the current scope set to this object.  If the
        // set and unset functions modify other data fields in the item
        // they should do so through the setValue,setValues, and
        // unsetAttribute methods so that the changes on the underlying
        // data are recorded and propagated.  The possible functions are:
        //
        //      get: Function to get the value of the attribute
        //           Called with no arguments.
        //      set: Function to set the value of the attribute.
        //           Called with the new value as the only argument.
        //      isAvailable: Function to determine whether the attribute is
        //           available.  Called with no arguments. This is required
        //           because it may be the case that a derived attribute can
        //           only be generated if specific updateTypes are in the
        //           updateList and no sane default value can be provided.
        //           If this is not present, the default is to assume the
        //           attribute is always available.
        //      hasChanged: Function to determine whether the value of the
        //           attribute has changed during an update.  The only
        //           argument is a list of changes to simple data
        //           attributes made during the update.  Each item on the
        //           list is an object with the properties attribute,
        //           oldValue, and newValue.
        this.derivedAttributes = {};

        this.updatemgr = this.coreui.getUpdateMgr();

        // Allow kwarg to override defaults
        dojo.mixin(this, kwarg);

        if (this.initialGeneration != undefined)
            this.generation = this.initialGeneration;

        // Misc other initialization
        this._data = {};
        this._derivedData = {};
        this._queuedUpdates = [];
        this._inProgressUpdates = null;
        this._pendingUpdateTypes = [];
        this._queuedSaves = [];
        this._inProgressSaves = null;
        this._pendingUpdateTypeSaveCnt = 0;
        this._conflictList = [];
        this._onLoadCallbacks = [];
        this._flags = [];

        this._updateBasicData(this.initialData);
        this.initialized = true;
    },

    update: function (/* object */ kwarg) {
        // summary: Update with the latest data from the server.
        // description:
        //     Updates data for the item.  More than one request may
        //     be required to update the item.  If an error occurs
        //     processing will continue without the requested data, so
        //     multiple calls to the error handlers may occur and
        //     onComplete may still be called after one or more errors
        //     occur.  In those cases some of the data in the item may
        //     be missing or out of date, but as a whole the item should
        //     continue to be usable.
        //
        //     Only one update of the item can be in process at a time.
        //     If update is called multiple times while an update is in
        //     progress, the requests will be queued until the update
        //     completes.  At that time, a new update will be started
        //     to handle *all* the queued updates.  The onComplete()
        //     call of all queued updates will be called when the
        //     second update completes.  Any errors that occur during
        //     the update will be handled by the error handlers
        //     supplied in the most recent update call.  Similarly, any
        //     conflicts that occur during the second update will be
        //     handled by the conflict handler for the most recent
        //     update call.
        //
        // keywordParamater: {newData, object}
        //     New set of key/value pair data to update item data.
        //     This is optional, however if an updateList was not
        //     provided when the object was created or the updateList
        //     is empty, this is the only way of updating data from
        //     the object as if it came from the server.  Client-side
        //     changes to the object should use the setValue, setValues,
        //     and unsetAttribute methods to modify the item instead
        //     of passing data here.
        // keywordParameters: {scope, object}
        //     Scope in which to call the onComplete function.
        // keywordParameters: {onComplete, function}
        //     Some update types may be asynchronous, so this this
        //     function is called when all specified updates are
        //     complete.  Some update types may encounter errors due
        //     to problems with background xhr requests, etc.  This
        //     function will still be called when all updates have
        //     been attempted.  Errors will be handled according to
        //     the errorHandlers specified when the instance was
        //     created.
        // keywordParameters: {errorHandlers: object}
        //     Object containing error handlers named by the error they
        //     handle, as passed to the factory function
        //     nox.ext.apps.coreui.coreui.UpdateErrorHandler.create().
        //     Unlike for a simple xhr requests, the handlers provided
        //     take four parameters.  The first two are the same as
        //     for standard errors, the error object and request object.
        //     The remaining two arguments are context sensitive and may
        //     be undefined.  The first is the item on which the error
        //     occured and the second is the updateType being retrieved
        //     when the error occured.
        // keywordParameters: {onError: function}
        //     Function called when an error occurs.  Called with the
        //     same arguments as the handlers specified in errorHandlers.
        //     If the errorHandlers parameter is specified, any
        //     value provided for onError will be overriden by the
        //     error handler created from the errorHandlers object.
        //     If neither errorHandlers nor onError are provided, a
        //     default error handler will be used.
        // keywordParameters: {conflictHandler: function}
        //     If a locally updated item is dirty at the time of
        //     an update the store will keep local changes for attributes
        //     that have not changed on the server and update attributes
        //     that changed on the server but not locally.  Attributes
        //     that have changed in both places will be left with the
        //     local value but the changes will be accumulated in a
        //     conflict list, which is passed to this function before
        //     the update completes.
        //
        //     The objects on the conflict list
        //     should be updated with a "resolution" property containing
        //     the value to be substituted.  If the "resolution" value
        //     is the same as the server value, all record of local
        //     edits to the value will be removed.  If it is the same as
        //     the local value no change will be made.  If it is neither
        //     the local nor the server value, the value will be updated
        //     as another local edit.  If no resolution property is set
        //     the local value will be retained.
        //
        //     The update will not be considered complete (and thus no
        //     further updates will be able to be done) until this
        //     function returns the resolution list.  To prevent stalling
        //     Javascript, if the resolution requires asynchronous
        //     input (such as feedback from the user) a deferred should be
        //     returned that will ultimately call the callback with the
        //     resolution list.


        // implementation:
        //     The basic strategy is to keep a object with
        //     name/value pairs representing the attributes. This is
        //     stored in this._data.  There are two ways data in this
        //     object can be updated.  One is to pass another object of
        //     name/value pairs into the update function in the newData
        //     parameter. The other is through the functions defined in
        //     updateTypes.  These functions are called if the
        //     updateList contains their name.  They are expected to
        //     update the data in this._data, typically by incorporating
        //     changes from an xhr request to the server.  Because
        //     of this, they typically return a deferred which will
        //     be called when the data has been obtained and the data
        //     updated.
        //
        //     Layered on top of this is a bunch of complexity to
        //     handle a couple of different situations.  Most complex
        //     is dealing with editing of the data on the client side
        //     and potential conflicts with data in an update from the
        //     server.  This is why the various conflict extension
        //     points exist and the reason for the conflictHandler
        //     parameter.
        //
        //     The second layer of complexity is due to the desire to
        //     be able to determine derived attributes from the basic
        //     data being updated as described above by having a
        //     function massage the data in the item and return the
        //     value for the derived attribute.  Most of the complexity
        //     comes from having to deal with change notification for
        //     the derived attributes.  When the underlying data changes
        //     the derived attributes need to be checked to see if they
        //     have changed and if they have the onChange notification
        //     for them needs to be propagated as well.
        if (this.hasFlag("deleted"))
            return;  /* Deleted items never update */

        if (kwarg == undefined)
            kwarg = {};
        kwarg.errhandler = this.coreui.UpdateErrorHandler.kwCreate(kwarg);
        if (kwarg.conflictHandler == null)
            kwarg.conflictHandler = this._defaultConflictHandler;

        this._queuedUpdates.push(kwarg);
        if (this._inProgressUpdates != null)
            return;
        this._startUpdate();
    },

    _startUpdate: function () {
        this._inProgressUpdates = this._queuedUpdates;
        this._queuedUpdates = [];

        this.generation++;
        if (this.initialized) {
            this.onUpdateStart(this);
        }

        this._conflictList = [];
        dojo.forEach(this._inProgressUpdates, function (a) {
            if (a.onComplete != undefined)
                this._onLoadCallbacks.push({
                    scope: a.scope,
                    onItem: a.onComplete
                });
            if (a.newData != undefined)
                this._updateBasicData(a.newData);
        }, this);
        this._pendingUpdateTypes = dojo.clone(this.updateList);
        this._startNextUpdate();
    },

    _startNextUpdate: function () {
        if (this._pendingUpdateTypes.length > 0) {
            var ut = this._pendingUpdateTypes.shift();
            var fn = this.updateTypes[ut].load;
            if (fn == undefined)
                throw new Error("Unknown update type: ", ut);
            var d = fn.call(this);
            if (d == null) {
                this._startNextUpdate();
            } else {
                d.addCallback(dojo.hitch(this, this._startNextUpdate));
            }
        } else {
            var kw = this._inProgressUpdates[this._inProgressUpdates.length-1];
            if (this._conflictList.length > 0) {
                var d = kw.conflictHandler.call(kw.scope, this._conflictList);
                if (d instanceof dojo.Deferred) {
                    d.addCallback(this._handleResolvedConflicts);
                } else {
                    this._handleResolvedConflicts(d);
                }
            } else {
                this._finishUpdate();
            }
        }
    },

    _defaultConflictHandler: function (l) {
        return l;   // Default behavior sticks with old value.
    },

    _updateBasicData: function (newData) {
        // summary: Update the basic data for the item w/o recording changes
        // description:
        //    This function sets new values in the simple data for the
        //    item without recording the changes as having happened locally.
        //    It is intended for use by the functions implementing update
        //    types, and not externally.
        //
        // newData: object with key/value pairs to set in the basic data.
        var changeList = [];
        for (var a in newData) {
            var localChanges = dojo.filter(this.localChanges, function (c) {
                return c.attribute == a;
            });
            var nLocalChanges = localChanges.length
            if (nLocalChanges > 0
                && localChanges[nLocalChanges - 1].newValue != newData[a]) {
                if (localChanges[0].oldValue != newData[a]) {
                    // This is a real change on the server side.  If the
                    // value didn't change on the server, we assume the
                    // user is just still in the process of editing and
                    // neither flag a conflict nor overwrite the user's
                    // edited value with the older value from the server.
                    var localValue = localChanges[nLocalChanges-1].newValue;
                    this.onConflictDetected(i, a, localValue, newData[a]);
                    this._conflictList.push({
                        attribute: a,
                        oldValue: localValue,
                        newValue: newData[a]
                    });
                }
            } else {
                var change = this._updateBasicAttribute(a, newData[a]);
                if (change != null) {
                    changeList.push(change);
                    if (this.initialized)
                        this.onChange(this, change.attribute, change.oldValue, change.newValue);
                }
            }
        }
        this._handleDerivedChanges(changeList);
    },

    _updateBasicAttribute: function (attribute, value) {
        var oldValue = this._data[attribute];
        if (oldValue == value)
            return null;
        this._data[attribute] = value;
        return {
            "attribute": attribute,
            "oldValue": oldValue,
            "newValue": value
        };
    },

    _handleDerivedChanges: function (changeList) {
        for (var a in this.derivedAttributes) {
            var da = this.derivedAttributes[a];
            if ((da.isAvailable == undefined
                 || da.isAvailable.call(this))
                && (da.hasChanged == undefined
                    || da.hasChanged.call(this, changeList))) {
                var oldValue = this._derivedData[a];
                var newValue = this._getAttribute(a);
                if (oldValue != newValue) {
                    this._derivedData[a] = newValue;
                    if (this.initialized)
                        this.onChange(this, a, oldValue, newValue);
                }
            }
        }
    },

    _handleResolvedConflicts: function (resolvedConflictList) {
        dojo.forEach(resolvedConflictList, function (c) {
            if (c.resolution == undefined || c.resolution == c.oldValue) {
                // c.resolution says stick w/locally modified value.
            } else if (c.resolution == c.newValue) {
                // c.resolution says update to the new server value.
                this.localChanges=dojo.filter(this.localChanges, function (l) {
                    return l.attribute != c.attribute;
                });
                this._updateBasicAttribute(c.attribute, c.resolution);
                this._handleDerivedChanges([ {
                    attribute: c.attribute,
                    oldValue: c.oldValue,
                    newValue: c.resolution
                } ]);
            } else {
                // c.resolution is neither old nor new, make another edit
                var change = this.setAttribute(c.attribute, c.resolution);
                if (change != null) {
                    this.localChanges.push(change);
                    this.onChange(this, change.attribute, change.oldValue, change.newValue);
                    this._handleDerivedChanges([ change ]);
                }
            }
            this.onConflictResolved(this, c.attribute, c.resolution)
        }, this);
        this._conflictList = [];
        this._finishUpdate();
    },

    _finishUpdate: function () {
        this._doLoadCallbacks();
        this.onUpdateComplete(this);
        this._inProgressUpdates = null;
        if (this._queuedUpdates.length > 0)
            this._startUpdate();
    },

    _doLoadCallbacks: function () {
        dojo.forEach(this._onLoadCallbacks, function (c) {
            c.onItem.call(c.scope == undefined ? dojo.global : c.scope, this);
        }, this);
        this._onLoadCallbacks = [];
    },

    basicDataChanged: function (attributeList, changeList) {
        // summary: Simple test of basic attributes for changes
        // description:
        //    This implements the most common method of determining whether
        //    a derived attribute has changed, but verifying whether on or
        //    more underlying basic data attributes have changed.  It
        //    checks to see if any attribute in attributeList is included
        //    in changeList.  It will be typically used in the hasChanged
        //    attribute of derivedAttribute taking advantage of the fact
        //    that trailing dojo.hitch arguments become initial arguments
        //    of the called function to provide the attributeList.
        return dojo.some(changeList, function (c) {
            dojo.some(attributeList, function (a) {
                return a == c.attribute;
            });
        });
    },

    isLoaded: function () {
        // summary: Indicates whether most recent update has completed.
        return (this.initialized && this._pendingUpdateTypes.length == 0 && this._conflictList.length == 0 && this._inProgressUpdates != null)
    },

    load: function (kwarg) {
        // summary: Request an item not yet loaded to be loaded.
        // TBD: - Complete documentation of load function.

        // implementation:
        //    Since the only time an item is not considered loaded
        //    is during initialization or while an update is in progress,
        //    both of which are ongoing, this doesn't really force any
        //    work on the item.  The real use for it is to register to
        //    be informed when the data is completely updated.
        //
        //    Any error handler provided in the onError property of the
        //    argument will never be called because error handling
        //    provided to update().  The onItem function will always be
        //    called when the update is complete, regardless of whether
        //    any errors occured.
        this._onLoadCallbacks.push(kwarg);
        if (this.isLoaded()) {
            this._doLoadCallbacks();
        }
    },

    _xhrGetMixin: function (updateType, url, prepareFn) {
        // summary: Mix-in properties from an object retrieved at given url
        // description:
        //     This is intended for use by subclasses implementing new
        //     updateTypes.  If the update can be done by issuing an xhrGet
        //     to a URL, getting back a json-encoded object, optionally
        //     mucking with that object a bit, and then mixing the resulting
        //     properties into the data for the item, this method can do
        //     all the work for you.
        //
        // url:
        //     The URL from which to obtain data.
        // prepareFn:
        //     A function to modify the returned data into an object that
        //     can be mixed into the data for the item.  If this is not
        //     specified, it is assumed the server returned an object that
        //     can be mixed into the data directly.
        var d = new dojo.Deferred();
        this.updatemgr.xhrGet({
            url: url,
            load: dojo.hitch(this, function (response, ioArgs) {
                if (prepareFn != null)
                    response = prepareFn.call(this, response);
                this._updateBasicData(response);
                d.callback();
            }),
            error: dojo.hitch(this, function (err, ioArgs) {
                var kw = this._inProgressUpdates[this._inProgressUpdates.length-1];
                var v = kw.errhandler.call(null, err, ioArgs, this, updateType);
                if (! v) {
                    // Only consider the update complete (call the callback)
                    // if the user has not been informed that the errored
                    // request can be retried.  If it can be retried, then
                    // one of the callbacks will be called again after the
                    // retry or when the retry dialog is dismissed.
                    d.callback();
                }
                return v;
            }),
            timeout: this.timeout,
            handleAs: "json"
        });
        return d;
    },
   
    // this function operates similarly to _xhrGetMixin above, except instead of 
    // performing an XHR, it does an asynchronous fetch on a store. 
    _storeQueryMixin: function(updateType, attributeName, store, query, prepareFn) { 
        var d = new dojo.Deferred();
        
        // we can't call fetch until after we update the store
        var after_update = dojo.hitch(this, function() {      
          store.fetch({
            query: query,
            onComplete: dojo.hitch(this, function (items, response) {
                if (prepareFn != null)
                    items = prepareFn.call(this, items);
                var data = {}; 
                data[attributeName] = items; 
                this._updateBasicData(data); 
                d.callback();
            })
        });
        }); 
        store.update({ 
                onComplete: after_update,
                onError: dojo.hitch(this, function (error, request) {
                    var kw = this._inProgressUpdates[this._inProgressUpdates.length-1];
                    var v = kw.errhandler.call(null, error, request, this, updateType);
                    if (! v) {
                      // Only consider the update complete (call the callback)
                      // if the user has not been informed that the errored
                      // request can be retried.  If it can be retried, then
                      // one of the callbacks will be called again after the
                      // retry or when the retry dialog is dismissed.
                      d.callback();
                  }
                  return v;
                })
        }); 
        return d;
    }, 


    getValue: function (attribute, defaultValue) {
        // summmary: Return a single-valued attribute value.
        v = this._getAttribute(attribute);
        if (v == undefined)
            return defaultValue;

        return dojo.isArray(v) ? v[0] : v;
    },

    getValues: function (attribute) {
        // summary: Return a multi-valued attribute value.
        v = this._getAttribute(attribute);
        if (v == undefined)
            return [];

        return dojo.isArray(v) ? v : [ v ];
    },

    _getAttribute: function (attribute) {
        var v = undefined;
        var da = this.derivedAttributes[attribute];
        if (da != null) {
            if (da.get != null) {
                v = da.get.call(this);
                this._derivedData[attribute] = v;
            } else {
                throw new Error("No get function for derived attribute: " + attribute);
            }
        } else {
            v = this._data[attribute];
        }
        return v
    },

    setValue: function (attribute, value) {
        // summary: Set a single-valued attribute
        this.setAttribute(attribute, dojo.isArray(value) ? value[0] : value);
    },

    setValues: function (attribute, values) {
        // summary: Set a multi-valued attribute
        this.setAttribute(attribute, dojo.isArray(values) ? values : [ values ]);
    },

    unsetAttribute: function (attribute) {
        // summary: Completely remove an attribute
        this.setAttribute(attribute, undefined);
    },

    setAttribute: function (attribute, value) {
        // implementation:
        //     If the attribute is being set is a derivedAttribute, no
        //     changes are recorded immediately.  It is assumed that the
        //     derived attribute will update the underlying data attributes
        //     and the processing for the notification on those changes
        //     will notify about the derived value change as well.  This is
        //     the reason it is critical that the derivedAttribute functions
        //     do their modifications using setValue, setValues, and
        //     unsetAttribute, or setAttribute.
        var da = this.derivedAttributes[attribute];
        if (da != null) {
            if (da.set == null )
                throw new Error("No set function for derived attribute: " + attribute);
            else
                da.set.call(this, value);
        } else {
            var change = this._updateBasicAttribute(attribute, value);
            if (change != null) {
                this.localChanges.push(change);
                this.onChange(this, change.attribute, change.oldValue, change.newValue);
                this._handleDerivedChanges([ change ]);
            }
        }
    },

    revert: function () {
        // summary: Revert any local changes

        // implementation:
        //     First we collect changes (because the same attribute may
        //     have changed more then once) and then we apply only the
        //     true original values using _setValue so that notifications
        //     are made about the changes.
        var originalData = {}
        dojo.forEach(this.localChanges.reverse(), function (i) {
            originalData[i.attribute] = i.oldValue;
        }, this);
        for (var a in originalData) {
            var v = originalData[a]
            if (dojo.isArray(v) && v.length > 0 && v[0] == undefined)
                // Special case for unsetAttribute
                this.setAttribute(a, v[0]);
            this.setAttribute(a, v);
        }
        this.localChanges = [];
    },

    acceptLocalChanges: function () {
        // summary: Drop tracking of all current local changes
        // description:
        //     This is roughly the opposite of revert().  If called, the
        //     caller is saying that the client side changes are now in
        //     sync with the server and no longer need to be tracked.
        //     Typically this is used by a store after it has saved
        //     modified entries and knows they are up-to-date.  It can
        //     be used directly by the item's save() method or in other
        //     cases as well however.
        //
        //     Note that this does nothing about flags, even though flags
        //     can also cause an item to be considered dirty.  This is
        //     because an individual item usually doesn't know what to
        //     do about flags set externally.  It is the responsibility
        //     of the external caller of acceptLocalChanges to determine
        //     whether the current flags are meaningful or not and
        //     clear them appropriately if the item should really be
        //     considered to be "clean".
        this.localChanges = [];
    },

    getAttributes: function () {
        // summary: Return the supported attributes.
        attrlist = [];
        for (var a in this._data) {
            attrlist.push(a);
        }
        for (a in this.derivedAttributes) {
            if (this.derivedAttributes[a].isAvailable != undefined) {
                if (this.derivedAttributes[a].isAvailable.call(this)) {
                    attrlist.push(a);
                }
            } else {
                attrlist.push(a);
            }
        }
        return attrlist;
    },

    hasAttribute: function (attribute) {
        // summary: Indicates whether the given attribute is available.
        return ((this._data[attribute] != undefined)
                || (this.derivedAttributes[a] != undefined
                    && this.derivedAttributes[a].isAvailable.call(this)))
    },

    containsValue: function (attribute, value) {
        // summary:  whether an attribute has a specific value.
        return dojo.some(this.getValues(attribute), function (i) {
            return i == value;
        });
    },

    getIdentity: function () {
        // summary: Get identity value that is unique for every item in store.
        if (this.identityAttributes.length == 0)
            throw new Error("This item does not support identities");
        return dojo.map(this.identityAttributes, "return this._data[item];", this).join(":");
    },

    getIdentityAttributes: function () {
        // summary: Get attributes used to form identity
        if (this.identityAttributes.length == 0)
            throw new Error("This item does not support identities");
        return this.identityAttributes;
    },

    getLabel: function () {
        // summary: Get display label to use for object.
        if (this.labelAttributes.length == 0)
            throw new Error("This item does not support labels");
        return dojo.map(this.labelAttributes, "return this._data[item];", this).join(":");
    },

    getLabelAttributes: function () {
        // summary: Get attributes used to form the label.
        if (this.labelAttributes.length == 0)
            throw new Error("This item does not support labels");
        return this.labelAttributes;
    },

    isDirty: function () {
        // summary: Indicate if item has changed since last update from server
        return this.localChanges.length != 0;
    },

    flags: function () {
        return this._flags;
    },

    hasFlag: function (flagname) {
        return dojo.some(this._flags, function (i) {return i == flagname;});
    },

    setFlag: function (flagname) {
        if (! this.hasFlag(flagname))
            this._flags.push(flagname);
    },

    unsetFlag: function (flagname) {
        this._flags = dojo.filter(this._flags, function (i) {return i != flagname;});
    },

    isValid: function () {
        // summary: Indicates whether data in the object is valid.
        // implementation:
        //    Default is to assume the item is always valid.  If the
        //    a particular item has restrictions, it must redefine this
        //    method.
        return true;
    },

    createOnServer: function (kwarg) {
        throw new Error("This item does not know how to create itself on the server.");
    },

    deleteOnServer: function (kwarg) {
        throw new Error("This item does not know how to delete itself from the server.");
    },

    save: function (kwarg) {
        // summary: Save any modified contents of this item to the server.
        // description:
        //     Saving uses the updateTypes definitions.  Uses the save
        //     method registered for each updateType on the updateList.
        //     Note this will only save anything at least one update type
        //     is in use.  If no updateTypes are in use (or defined), save
        //     will not do anything.  If an updateType doesn't define any
        //     save function, then it will be skipped.
        //
        //     Only one save of the item can be in process at a time.
        //     If save is called multiple times while a save is in
        //     progress, the requests will be queued until the save
        //     completes.  At that time, a new save will be started
        //     to handle *all* the queued saves.  The onComplete()
        //     call of all queued saves will be called when the
        //     second save completes.  Any errors that occur during
        //     the save will be handled by the error handlers
        //     supplied in the most recent save call.
        //
        // keywordParameter: {scope: object}
        //     Scope in which to make callbacks
        // keywordParameter: {onComplete: function}
        //     Function called when update is complete
        // keywordParameters: {errorHandlers: object}
        //     Object containing error handlers named by the error they
        //     handle, as passed to the factory function
        //     nox.ext.apps.coreui.coreui.UpdateErrorHandler.create().
        //     Unlike for a simple xhr requests, the handlers provided
        //     take four parameters.  The first two are the same as
        //     for standard errors, the error object and request object.
        //     The remaining two arguments are context sensitive and may
        //     be undefined.  The first is the item on which the error
        //     occured and the second is the updateType being retrieved
        //     when the error occured.
        // keywordParameter: {onError: function}
        //     Function called when an error occurs.  Called with the
        //     same parameters that the xhr error function is called
        //     with.

        // implementation:
        //    Each updateType may define a save function that saves data
        //    associated with that updateType to the server.  If no such
        //    function is defined it is assumed that there is no meaningful
        //    way to save the associated data.
        //
        //    The function must either complete the save immediately and
        //    return null or return a deferred the callback of which will
        //    be called when the update is complete.  This code assumes
        //    that updateType save function will deal with all errors so
        //    (typically using the errhandler property of the last element
        //    of this._inProgressSaves) so it will never call the errback.
        if (kwarg == undefined)
            kwarg = {};
        kwarg.errhandler = this.coreui.UpdateErrorHandler.kwCreate(kwarg);

        this._queuedSaves.push(kwarg);
        if (this._inProgressSaves != null)
            return;
        this._startSave();
    },

    _startSave: function () {
        this._inProgresSaves = this._queuedSaves;
        this._queuedSaves = [];

        this._pendingUpdateTypeSaveCnt = this.updateList.length;
        dojo.forEach(this.updateList, function (ut) {
            try {
                var fn = this.updateTypes[ut].save;
            } catch (e) {
                fn = null;
            }
            if (fn == null) {
                this._pendingUpdateTypeSaveCnt--;
                return;
            }
            var d = fn.call(this);
            if (d == null) {
                this._pendingUpdateTypeSaveCnt--;
                return;
            }
            d.addCallback(dojo.hitch(this, "_handleSaveComplete"));
        }, this);
        if (this._pendingUpdateTypeSaveCnt == 0)
            this._finishSave();
    },

    _handleSaveComplete: function (callback, err) {
        if (--this._pendingUpdateTypeSaveCnt == 0)
            this._finishSave();
    },

    _finishSave: function () {
        // TBD: - This effectively accepts all changes even if there
        // TBD:   were errors that could not be resolved which the
        // TBD:   user dismissed.  Need to consider further enhancements
        // TBD:   to the error handlers so can record what was and was
        // TBD:   not successful.
        this.acceptLocalChanges();
        dojo.forEach(this._inProgressSaves, function (kw) {
            if (kw.onComplete != undefined)
                kw.onComplete.call(kw.scope);
        }, this);
        this._inProgressSaves = null;
    },

    _xhrPutData: function (updateType, url, prepareFn) {
        var d = new dojo.Deferred();
        if (prepareFn != undefined)
            data = prepareFn(this);
        this.updatemgr.rawXhrPut({
            url: url,
            headers: { "content-type": "application/json" },
            putData: dojo.toJson(this._data),
            load: dojo.hitch(this, function (response, ioArgs) {
                d.callback();
            }),
            error: dojo.hitch(this, function (err, ioArgs) {
                var kw = this._inProgressSaves[this._inProgressSaves.length-1];
                var v = kw.errhandler.call(null, err, ioArgs, this, updateType);
                if (! v) {
                    // Only consider the save complete (call the callback)
                    // if the user has not been informed that the errored
                    // request can be retried.  If it can be retried, then
                    // one of the callbacks will be called again after the
                    // retry or when the retry dialog is dismissed.
                    d.callback();
                }
                return v;
            }),
            timeout: this.timeout,
            handleAs: "json"
        });
        return d;
    },

    onUpdateStart: function (item) {
        // summary: Called when an update from the server is started.
    },

    onChange: function (item, attribute, oldValue, newValue ) {
        // summary: Called when an attribute value changes
    },

    onConflictDetected: function (item, attribute, localValue, serverValue) {
        // summary: Called when a conflict is detected between local & server
        // description:
        //     This function is called when a conflict between a locally
        //     modified value and the server value is detected during
        //     an update.  It is not responsibile for resolving the
        //     conflict but simply notifies that the conflict has
        //     occurred.  Resolution is done using the conflictHandler
        //     passed to update().
    },

    onConflictResolved: function (item, attribute, finalValue) {
        // summary: Called when a conflict between local and server is resolved
    },

    onUpdateComplete: function (item) {
        // summary: Called when an update from the server is complete.
    },

    installDebugLogging: function () {
        dojo.connect(this, "onUpdateStart", this, function (i) {
            console_log("Item: ", i, " update started.");
        });
        dojo.connect(this, "onChange", this, function (i, a, o, n) {
            console_log("Item: ", i, " attribute: ", a, " changed from: ", o, " to: ", n);
        });
        dojo.connect(this, "onConflictDetected", this, function (i, a, l, s) {
            console_log("Item: ", i, " conflict detected in attribute: ", a, " local value: ", l, " server value: ", s);
        });
        dojo.connect(this, "onConflictResolved", this, function (i, a, f) {
            console_log("Item: ", i, " conflict resolved in attribute: ", a, " final value: ", f);
        });
        dojo.connect(this, "onUpdateComplete", this, function (i) {
            console_log("Item: ", i, " updated completed.");
        });
    }
});
