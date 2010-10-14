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

dojo.provide("nox.ext.apps.coreui.coreui._UpdatingStore");

dojo.require("nox.ext.apps.coreui.coreui.UpdateMgr");
dojo.require("nox.ext.apps.coreui.coreui.UpdateErrorHandler");
dojo.require("nox.ext.apps.coreui.coreui._UpdatingItem");
dojo.require("dojo.data.util.simpleFetch");
dojo.require("dojo.data.util.filter");

dojo.declare("nox.ext.apps.coreui.coreui._UpdatingStore", [ ], {
    // summary: Store that can automatically update its contents
    // description:
    //     TBD: - Add full description of the _UpdatingStore class.

    // implementation:
    //     The store keeps information in javascript _UpdatingItem
    //     classes/subclasses with minor indexing and the surrounding
    //     code to provide access.  It attempts to offload much of the
    //     work to the _UpdatingItem, so many of the standard store
    //     methods that operate on items are just forwarded to
    //     instances of that class.

    coreui: nox.ext.apps.coreui.coreui,

    url: null,
    timeout: 30000,
    autoUpdate: null,
    // flag used to queue fetch requests that happen when we are
    // handling a server response, since this._items is invalid during
    // that time. 
    _handling_server_response: false, 

    constructor: function (kwarg) {
        // summary: Constructor
        //
        // keywordParameters: {url: string}
        //     The URL from which the store should obtain the items that
        //     are included in the store.
        // keywordParameters: {timeout: number}
        //     Number of milliseconds before xhr requests should timeout.
        // keywordParameters: {itemConstructor: function}
        //     Constructor for the item object to be included in the store.
        //     Must be a subclass of nox.ext.apps.coreui.coreui._UpdatingItem;
        // keywordParameters: {itemParameters: object}
        //     Additional parameters to mix into parameters for object
        //     construction.  See the possible parameters in _UpdatingItem
        //     or its subclasses.  Note that if you specify anything for
        //     initialData, store, or initialGeneration, it will be
        //     ignored because this code sets those itself.
        // keywordParameters: {autoUpdate: object}
        //     If null, or not present, updates must be done manually, by
        //     calling the update() function.  If present, it should be
        //     an object containing the same properties as are accepted by
        //     the update() function.  These will be used for each
        //     auto-update.

        this.itemConstructor = nox.ext.apps.coreui.coreui._UpdatingItem;
        this.itemParameters = {};

        if (kwarg == null)
            kwarg = {}; // Use all defaults. Probably not what you want though.
        dojo.mixin(this, kwarg);

        this.updatemgr = this.coreui.getUpdateMgr();

        this._internals_init();
        if (this.autoUpdate != null)
            this._updateItemsFromServer(this.autoUpdate);
        else
            this.initialized = true;
    },

    _internals_init: function() {
        this.generation = 0;
        this._items = [];
        this._oldItems = null;
        this._localItems = 0;
        this.initialized = false;
        this._pendingFetches = [];
        this._queuedUpdates = [];
        this._inProgressUpdates = null;
        this._pendingItemUpdates = 0;
        this._queuedSaves = [];
        this._queueAllSaves = false;
        this._inProgressSaves = null;
        this._pendingItemSaves = 0;
        this._update = null;
        this._byId = {};
        this._changingIdentity = false;
    },

    /* Call before disposing of object.
     *
     * This is required to remove the update from the update queue. */
    destroy: function () {
        if (this._update != null)
            this._update.cancel();
        dojo.forEach(this._items, function (i) {
            // Remove all existing items for anybody watching them...
            this._deleteItem(i);
        }, this);
        this._internals_init();
    },

    // TBD: - Need to replace update_url by having the query change the url
    // TBD:   as it is currently a very nasty hack when working with the
    // TBD:   newly restructured stores.
    update_url: function(url) {
        this.destroy();
        this.url = url;
        this.initialized = true;
        if (this.autoUpdate != null)
            this._updateItemsFromServer(this.autoUpdate);
        else
            this.initialized = true;
    },

    update: function (kwarg) {
        // summary: Force an immediate update of the store.
        // description:
        //     Updates the store.  The behavior depends on whether the
        //     store was created with autoUpdate enabled or not.  If
        //     autoUpdate was enabled, then this just forces the next
        //     scheduled update to occur immediately.  Any keyword
        //     parameters supplied in the call are ignored and the
        //     parameters supplied in the autoUpdate configuration are
        //     used.  If autoUpdate is disabled, then this starts a
        //     new update and the parameters specified below are used.
        //
        //     More than one request may be required to update the
        //     store.  If an error occurs on the initial request (to
        //     the url defined for the store) then the update
        //     will effectively be aborted.  If an error occurs in
        //     one of the underlying item updates, processing will continue
        //     without the requested data, so multiple error calls
        //     to the error handlers may occur and onComplete may still
        //     be called after one or more errors occur.  In those
        //     cases, some of the items in the store may be missing
        //     updated data, but as a whole the store should be okay.
        //     The error handlers can determine whether the error is
        //     for the url request or an item update by checking
        //     whether the item parameter of the error handler is
        //     undefined (see below).
        //
        //     Only a single update can be in progress at one time.
        //     If update is called again while previous update is still
        //     in progress the update request will be queued until
        //     the previous update completes triggering another
        //     immediate update.  If more than one update are queued,
        //     the onComplete of all updates will be called but the
        //     only the error handlers of the most recent call are used.
        //
        // keywordParameters: {scope: object}
        //     Scope in which to make onComplete and error callbacks
        // keywordParameters: {onComplete: function}
        //     Function called when update is complete.
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
        if (this.autoUpdate != null && this.initialized) {
            this.updatemgr.updateNow();
        } else {
            this._updateItemsFromServer(kwarg);
        }
    },

    _updateItemsFromServer: function(kwarg) {
        if (kwarg == undefined)
            kwarg = {};
        kwarg.errhandler = this.coreui.UpdateErrorHandler.kwCreate(kwarg);

        this._queuedUpdates.push(kwarg);
        if (this._inProgressUpdates != null)
            return;

        this._startUpdate();
    },

    _startUpdate: function () {
        this._inProgressUpdates = this._queuedUpdates;
        this._queuedUpdates = [];

        this._update = this.updatemgr.xhrGet({
            url: this.url,
            load: dojo.hitch(this, "_handleServerResponse"),
            error: this._inProgressUpdates.slice(-1)[0].errhandler,
            timeout: this.timeout,
            handleAs: "json",
            recur: this.autoUpdate != null
        });
    },

    _handleServerResponse: function (response, ioArgs) {
        var oldItems = this._items;
        this._items = [];
        this._handlingServerResponse = true;
        var itemsData = this._unpackData(response);
        this._pendingItemUpdates = itemsData.length;
        dojo.forEach(itemsData, function (d) {
            var i = this._findOrCreateItem(d);
            i.update({
                newData: d,
                scope: this,
                onComplete: this._updateCompleteHandler,
                onError: this._inProgressUpdates.slice(-1)[0].errhandler
                // NOTE: UpdatingItems always call onComplete.  They may
                // call onError one or more times before this.
            });
        }, this);
        this.generation++;
        this._removeDeletedItems(oldItems);

        this._handlingServerResponse = false;
        if (itemsData.length == 0)
            this._finishUpdate();

        // we must handle any fetches that were queued 
        // during the time we were handling the server response
        this._handlePendingFetches();
    },

    _unpackData: function(response) {
        // summary: extract data for items from server response
        // description:
        //     A list of data for the items in the store should be
        //     returned from this function.  The list should contain
        //     objects with key/value pairs representing information
        //     in the item.
        return response;
    },

    _findOrCreateItem: function (itemData) {
        // implementation:
        //    The onChange property below overrides the onChange
        //    implementation of the original object to notify the
        //    store of all changes.  This way the store does not
        //    have to dojo.connect() to the onChange of each and
        //    every item in the store and we don't have to have
        //    separate subclasses for use in a store or not.
        var kwarg = {};
        dojo.mixin(kwarg, this.itemParameters);
        dojo.mixin(kwarg, {
            store: this,
            initialData: itemData,
            initialGeneration: this.generation,
            onChange: dojo.hitch(this, this._itemChangeHandler)
        });
        var i = new this.itemConstructor(kwarg);
        var id = i.getIdentity();
        var o = this.fetchItemByIdentity(id);
        if (o != null && o.hasFlag("new")) {
            // Item was created locally and on server independently.
            o.unsetFlag("new");
        }
        return (o != null) ? this._insertItem(o, -1) : this._addItem(i, -1);
    },

    _itemChangeHandler: function (item, attribute, oldValue, newValue) {
        if (! this._changingIdentity)
            this.onSet(item, attribute, oldValue, newValue);
    },

    _insertItem: function (item, position) {
        // summary: reinsert an existing item into the items list.
        if (position >= 0)
            var i = Math.min(position, this._items.length);
        else
            i = Math.max(this._items.length + (position + 1), 0);
        this._items.splice(i, 0, item);
        return item;
    },

    _addItem: function (item, position) {
        // summary: add an item to the store
        //
        // item:
        //     The item to be inserted
        // position:
        //     Where the items should be inserted within the existing
        //     items.  It musth be a number.  Numbers < 0 indicate from
        //     the end of the string, so -1 is at the end of the array,
        //     -2 is before the last element, and so on.  Items that
        //     exceed the lenght of the array in either direction result
        //     in placement at the last element visited.
        var id = item.getIdentity();
        if (this._byId[id] != undefined) {
            if (! this._byId[id].hasFlag("deleted")) {
                // We're leaving the old version of the item on
                // this._items in the deleted state.  It should be
                // properly cleaned up on the next update from the
                // server and not cause any harm until then since it
                // isn't referenced from the index.
                throw new Error("Item already exists with id: ", id);
            }
        }
        this._byId[id] = item;
        this._insertItem(item, position);
        if (this.initialized)
            this.onNew(item, null);
        return item;
    },

    _updateCompleteHandler: function (item) {
        if (--this._pendingItemUpdates == 0)
            this._finishUpdate();
    },

    // compare the items we had before the update to 
    // the list of items we just received.  Any item 
    // not in the new list either
    // 1) Is new and hasn't been pushed to the server yet
    // 2) Is modified and changes haven't been pushed to server yet
    // 3) Has been deleted on the server, and should be removed
    //    from our local store as well. 
    _removeDeletedItems: function (oldItems) {
        this._localItems = 0;
        dojo.forEach(oldItems, function (i) {
            if (i.generation < this.generation) {
                var deleted = i.hasFlag("deleted");
                if (i.hasFlag("new") && ! deleted) {
                    // New items not on server go at head of list
                    this._localItems++;
                    this._items.unshift(i);
                } else if (i.isDirty() && ! deleted) {
                    // Dirty items not on server go at head of list too
                    this._localItems++;
                    this._items.unshift(i);
                } else {
                    if (! deleted)
                        this._deleteItem(i);
                    i.store = null;  // Break any possible circular reference.
                    delete this._byId[i.getIdentity()];
                }
            }
        }, this);
    },

    _deleteItem: function (item) {
        if (item.hasFlag("deleted")) {
            return;
        }
        item.setFlag("deleted");
        if (this.initialized) {
            this.onDelete(item);
        }

    },

    _finishUpdate: function () {
        if (this.initialized == false) {
            this.initialized = true;
            this._handlePendingFetches();
        }
        dojo.forEach(this._inProgressUpdates, function (kw) {
            if (kw.onComplete != null)
                kw.onComplete.call(kw.scope);
        }, this);
        if (this.autoUpdate == null) {// If autoupdate, always use first set
            this._inProgressUpdates = null;
            if (this._queuedUpdates.length > 0)
                this._startUpdate();
        } else {
            if (this._queuedUpdates.length > 0) {
                this._queuedUpdates = [];
            }
        }
    },

    getFeatures: function () {
        return {
            'dojo.data.api.Identity': true,
            'dojo.data.api.Read': true,
            'dojo.data.api.Write' : true,
            'dojo.data.api.Notification': true
        };
    },


    /* Identity API */

    getIdentity: function (item) {
        return item.getIdentity();
    },

    getIdentityAttributes: function (item) {
        return item.getIdentityAttributes();
    },

    fetchItemByIdentity: function (kwarg) {
        /* If argument is a string, returns synchronously. */
        if (typeof kwarg == "string") {
            return this._byId[kwarg];
        } else {
            var item = this._byId[kwarg.identity]
            kwarg.onItem.call(kwarg.scope, item);
        }
    },

    /* Read API */

    getValue: function (item, attribute, defaultValue) {
        return item.getValue(attribute, defaultValue);
    },

    getValues: function (item, attribute) {
        return item.getValues(attribute);
    },

    getAttributes: function (item) {
        return item.getAttributes();
    },

    hasAttribute: function (item, attribute) {
        return item.hasAttribute(attribute);
    },

    containsValue: function (item, attribute, value) {
        return item.containsValue(attribute, value);
    },

    isItem: function (item) {
        return item.store == this;
    },

    isItemLoaded: function (item) {
        return item.isLoaded();
    },

    loadItem: function (kwarg) {
        kwarg.item.load(kwarg);
    },

    _item_matches_query: function (item, query, query_re) {
        if (item.hasFlag("deleted"))
            return false;
        if (this.preQuery && !this.preQuery(item)) { return false; }

        for (var k in query) {
            var found = false;
            var ev = query[k];
            var re = query_re[k];
            var values = this.getValues(item, k);
            for (var i = 0; i < values.length && ! found; i++) {
                var v = values[i];
                if (typeof(v) == "string" && re != null)
                    found = v.match(re);
                else if (typeof(ev) == "function")
                    found = ev(v);
                else 
                    found = v == ev;
            }
            if (! found)
                return false;
        }
        return true;
    },

    _handlePendingFetches: function () {
        for (var i = 0; i < this._pendingFetches.length; i++)
            this._pendingFetches[i].call(this);
        this._pendingFetches = [];
    },

    _fetchItems: function (request, result_cb, error_cb) {
    var ignoreCase = request.queryOptions ? request.queryOptions.ignoreCase : false; 
        var query_re = {}
        var query = request["query"];
        if (query != null) {
            for (var k in query) {
                var v = query[k]
                if (typeof(v) == "string")
                    query_re[k] = dojo.data.util.filter.patternToRegExp(v, ignoreCase);
            }
        }

        var f = function () {
            var items = [];
            for (var i = 0; i < this._items.length; i++) {
                var item = this._items[i];
                if (! this._item_matches_query(item, query, query_re))
                    continue;
                items.push(item)
            }
            result_cb(items, request);
        };

        if (this.initialized && !this._handlingServerResponse) {
            f.call(this);
        } else {
            this._pendingFetches.push(f);
        }
    },

    close: function () {
        // Nothing to do here right now.
    },

    getLabel: function (item) {
        return item.getLabel();
    },

    getLabelAttributes: function (item) {
        return item.getLabelAttributes();
    },

    _clearItems: function () {
        // summary: clear items currently in the store.
        // description:
        //    This method is intended for use by error handlers.  If
        //    the error means the store no longer knows what is on the
        //    server the error handler can call this to clear the
        //    existing data out of the store without triggering any
        //    of the local editing handling.  This will remove any
        //    display of the items in widgets until a successful update
        //    which will result in onNew notifications for items still
        //    on the server.  NOTE: to prevent loss of work for the
        //    user, this method does retain any items that have been
        //    locally edited.
        var oldItems = this._items;
        this._items = [];
        dojo.forEach(oldItems, function (i) {
            if (i.hasFlag("new") || i.hasFlag("deleted") || i.isDirty()) {
                this._items.push(i);
            } else {
                i.store != null;  // Break any circular references
                delete this._byId[i.getIdentity()];
                if (this.initialized)
                    this.onDelete(i);
            }
        }, this);
    },

    /* Write API */
    newItem: function (kwarg, parent) {
        var i = new this.itemConstructor({
            store: this,
            initialData: kwarg,
            initialGeneration: this.generation,
            onChange: dojo.hitch(this, this._itemChangeHandler)
        });
        i.setFlag("new");
        this._addItem(i, 0);
    },

    deleteItem: function (item) {
        this._deleteItem(item, true);
    },

    setValue: function (item, attribute, value) {
        this._prepareForAnyIdentityChange(item, attribute);
        item.setValue(attribute, value);
        this._completeAnyIdentityChange(item);
    },

    setValues: function (item, attribute, values) {
        this._prepareForAnyIdentityChange(item, attribute);
        item.setValues(attribute, values);
        this._completeAnyIdentityChange(item);
    },

    _prepareForAnyIdentityChange: function (item, attribute) {
        if (dojo.some(item.getIdentityAttributes(), function (a) {return a == attribute;})) {
            this._changingIdentity = true;
            this.queueAllSaves();
            delete this._byId[item.getIdentity()];
            this.onDelete.call(dojo.global, item);
        }
    },

    _completeAnyIdentityChange: function (item) {
        if (this._changingIdentity) {
            this._byId[item.getIdentity()] = item;
            this.onNew.call(dojo.global, item);
            this._changingIdentity = false;
            this.releaseQueuedSaves();
        }
    },

    unsetAttribute: function (item, attribute, values) {
        item.unsetAttribute(attribute);
    },

    isDirty: function (item) {
        return item.isDirty();
    },

    save: function (kwarg) {
        // summary: save any modified contents in the store to the server
        // description:
        //    Only a single save can be in progress at a time.  If save is
        //    called again while a previous one is in progress, the new
        //    request will be queued until the previous one completes.
        //    A single followup save will be initiated at that time.  All
        //    queued save requests will have their onComplete callback
        //    called when this second save completes.  If there are any
        //    errors during the save, the error handlers from the most
        //    recent save request will be used.
        //
        // keywordParameters: {scope: object}
        //     Scope in which to make callbacks
        // keywordParameters: {onComplete: function}
        //     Function called when save is complete
        // keywordParameters: {errorHandlers: object}
        //     Object containing error handlers named by the error they
        //     handle, as passed to the factory function
        //     nox.ext.apps.coreui.coreui.UpdateErrorHandler.create().
        //     Unlike for a simple xhr requests, the handlers provided
        //     take four parameters.  The first two are the same as
        //     for standard errors, the error object and request object.
        //     The remaining two arguments are context sensitive and may
        //     be undefined.  The first is the item on which the error
        //     occured and the second is the updateType being saved
        //     when the error occured.
        // keywordParameters: {onError: function}
        //     Function called when an error occurs.  Called with the
        //     same parameters as described for the errorHandlers
        //     parameter.  If an errorHandlers object is defined,
        //     any onError function specified will be ignored.

        // implementation:
        //    The default implementation here attempts to cover the most
        //    common cases.  It has two strategies for attempting the
        //    save depending on the value returned by _packData.  If
        //    _packData returns an array, it is JSON encoded
        //    and PUT to the server URL from which the store retreived
        //    data.  It is the responsibility of the packData method to
        //    determine what to do with invalid data, if any, etc.
        //
        //    The _packData method can indicate the update should be
        //    aborted (due to invalid/inconsistent data, or whatever
        //    other reason) by returning the string "abort".
        //
        //    If null is returned, the store assumes each item must
        //    be saved individually and the items understand how to
        //    update the server about themselves through their
        //    createOnServer(), deleteOnServer(), and save() methods,
        //    which the store will call for each modified item to
        //    update the server.  In this case, before calling
        //    createOnServer() or save(), the store will ensure the
        //    item has valid data by calling isValid().  Any items
        //    which don't have valid data will not be saved to the
        //    server.  Note that in this case, even if an error
        //    handler is called, the onComplete will still be called
        //    when all items have been saved.
        if (kwarg == undefined)
            kwarg = {};
        kwarg.errhandler = this.coreui.UpdateErrorHandler.kwCreate(kwarg);

        this._queuedSaves.push(kwarg);
        if (this._inProgressSaves != null || this._queueAllSaves) {
            return;
        }

        this._startSave();
    },

    queueAllSaves: function () {
        // summary: Force all saves to be queued until released
        // description:
        //     To release any queued saves, call releaseQueuedSaves().
        this._queueAllSaves = true;
    },

    releaseQueuedSaves: function () {
        if (this._queueAllSaves == false)
            return;
        this._queueAllSaves = false;
        if (this._inProgressSaves == null && this._queuedSaves.length > 0)
            this._startSave();
    },

    _startSave: function () {
        this._inProgressSaves = this._queuedSaves;
        this._queuedSaves = [];

        var data = this._packData();
        if (data == "abort") {
            return;
        }
        if (data != null) {
            this.updatemgr.rawXhrPut({
                url: this.url,
                headers: { "content-type": "application/json" },
                putData: dojo.toJson(data),
                timeout: this.timeout,
                load: dojo.hitch(this, function (response, ioArgs) {
                    this._finishSave();
                }, this),
                error: this._inProgressSaves.slice(-1)[0].errhandler
            });
        } else {
            this._pendingItemSaves = this._items.length;
            dojo.forEach(this._items, function (i) {
                // NOTE: UpdatingItems always call onComplete.  They may
                // call onError one or more times before this.
                var kw = {
                    scope: this,
                    onComplete: dojo.hitch(this, "_itemSaveComplete"),
                    onError: this._inProgressSaves.slice(-1)[0].errhandler
                }
                if (i.hasFlag("new")) {
                    i.createOnServer(kw);
                } else if (i.hasFlag("deleted")) {
                    i.deleteOnServer(kw);
                } else if (i.isDirty()) {
                    i.save(kw);
                } else {
                    this._itemSaveComplete();
                }
            }, this);
        }
    },
    _packData: function () {
        // summary: Default _packData implementation
        // description:
        //    The default implementation returns null indicating the
        //    items in the store need to be saved individually.
        return null;
    },

    _packDataList: function (kwarg) {
        // summary: Helper method for implementors of _packData
        // keywordParameter: { name : string }
        //    Optional name of field with which to associate data list.
        //    If this is null, a raw list will be returned.  If it is
        //    specified, the list will be retruned as a property of an
        //    object with property 'name'.
        // keywordParameters: { otherData : object }
        //    Optional object containing additional data to be
        //    mixed into the object returned with the packed data.
        //    This is only used if name != null.
        // keywordParameter: { packFn: function }
        //    Optional function to call to extract data from the item.
        //    It must return an object with the data to be saved to
        //    to the server as the properties.  If it is not specified
        //    the default is to send all the basic data properties.
        // keywordParameters: { abortOnInvalid: boolean }
        //    Instead of attempting to save all valid items, abort the
        //    entire save request if an item is found to be invalid.
        //
        // description:
        //    This method attempts to make it easy for store authors
        //    to implement a _packData() method that bundles up all items
        //    in a single list to be posted to the server.  It provides
        //    enough flexibility in the look of the returned data that
        //    most potential use cases should be satisified.  Invalid items
        //    are not included in the list sent to the server.  The
        //    default handling in acceptLocalChanges() will keep these
        //    items locally even after the server is successfully updated
        //    so they can be made valid.
        var foundInvalid = false;
        var itemData = [];
        dojo.forEach(this._items, function (i) {
            if (! i.hasFlag("deleted")) {
                if (i.isValid()) {
                    if (kwarg.packFn == null)
                        itemData.push(i._data);
                    else
                        itemData.push(kwarg.packFn(i));
                } else {
                    foundInvalid = true;
                }
            }
        }, this);
        if (foundInvalid && kwarg.abortOnInvalid)
            return "abort";
        if (kwarg.name == null)
            return itemData;
        else {
            var o = {};
            o[kwarg.name] = itemData;
            return dojo.mixin(o, kwarg.otherData);
        }
    },

    _itemSaveComplete: function (body, request) {
        if (--this._pendingItemSaves == 0) {
            this._finishSave();
        }
    },

    _finishSave: function () {
        // TBD: - This effectively accepts all changes even if there
        // TBD:   were errors that could not be resolved which the
        // TBD:   user dismissed.  Need to consider further enhancements
        // TBD:   to the error handlers so can record what was and was
        // TBD:   not successful.
        this.acceptLocalChanges();
        dojo.forEach(this._inProgressSaves, function (kw) {
        if (kw.onComplete != null)
            kw.onComplete.call(kw.scope);
        }, this);
        this._inProgressSaves = null;
        if (this._queuedSaves.length > 0)
            this._startSave();
    },

    acceptLocalChanges: function () {
        // summary: Accept that all local changes are now on the server
        // description:
        //    Called to indicate that all local changes have been made
        //    successfully on the server, usually as the success
        //    callback of an xhr request.
        var oldItems = this._items;
        this._items = [];
        dojo.forEach(oldItems, function (item) {
            if (item.hasFlag("deleted")) {
                item.store = null; // Break any possible circular reference.
                delete this._byId[item.getIdentity()];
                return;
            }
            if (item.isValid()) {
                // Invalid items that weren't deleted should never be sent
                // to the server or if they were should have generated an
                // error, not success.  So, we only accept change for valid
                // items.
                if (item.hasFlag("new")) {
                    item.unsetFlag("new");
                }
                item.acceptLocalChanges();
            }

            item.generation = this.generation;
            this._items.push(item);
        }, this);
    },

    revert: function () {
        dojo.forEach(this._items, function (i) {
            if (i.isDirty())
                i.revert();
            if (i.hasFlag("new") && ! i.hasFlag("deleted")) {
                i.unsetFlag("new");
                this._deleteItem(i, false);
            } else if (i.hasFlag("deleted")) {
                i.unsetFlag("deleted");
                this.onNew(i, null);  // Let everyone know item is back.
            }
        }, this);
    },

    /* Notification API */

    onSet: function (item, attribute, oldValue, newValue) {
    },

    onNew: function (newItem, parentInfo) {
    },

    onDelete: function (deletedItem) {
    },

    /* NOX extended API */

    isValid: function (item) {
        return item.isValid();
    },

    itemCount: function () {
        return this._items.length;
    },

    cloneItem: function (item) {
        // summary: Return a clone of an item in the store
        // description:
        //    The clone returned is *not* part of the store, but it
        //    contains the same underlying data.
        return new this.itemConstructor({
            initialData: item._data
        });
    },

    /* Misc. */

    installDebugLogging: function () {
        dojo.connect(this, "onSet", function (item, attribute, oldValue, newValue) {
            console_log("Item ", item, " attribute ", attribute, " changed from ", oldValue, " to ", newValue);
        });
        dojo.connect(this, "onNew", function (newItem, parentInfo) {
            console_log("Item ", newItem, " added with parent ", parentInfo);
        });
        dojo.connect(this, "onDelete", function (deletedItem) {
            console_log("Item ", deletedItem, " deleted");
        });
    }
});
// Mix in the simple fetch implementation to this class.
// TBD: Why can't this just be inherited?
dojo.extend(nox.ext.apps.coreui.coreui._UpdatingStore,dojo.data.util.simpleFetch);
