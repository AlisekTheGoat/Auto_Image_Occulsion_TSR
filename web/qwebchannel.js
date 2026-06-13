/****************************************************************************
**
** Copyright (C) 2016 The Qt Company Ltd.
** Copyright (C) 2014 Klarälvdalens Datakonsult AB, a KDAB Group company, info@kdab.com, author Milian Wolff <milian.wolff@kdab.com>
** Contact: https://www.qt.io/contact-us
**
** This file is part of the QtWebChannel module of the Qt Toolkit.
**
** $QT_BEGIN_LICENSE:LGPL$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** GNU Lesser General Public License Usage
** Alternatively, this file may be used under the terms of the GNU Lesser
** General Public License version 3 as published by the Free Software
** Foundation and appearing in the file LICENSE.LGPL3 included in the
** packaging of this file. Please review the following information to
** ensure the GNU Lesser General Public License version 3 requirements
** will be met: https://www.gnu.org/licenses/lgpl-3.0.html.
**
** GNU General Public License Usage
** Alternatively, this file may be used under the terms of the GNU
** General Public License version 2.0 or (at your option) the GNU General
** Public license version 3 or any later version approved by the KDE Free
** Qt Foundation. The licenses are as published by the Free Software
** Foundation and appearing in the file LICENSE.GPL2 and LICENSE.GPL3
** included in the packaging of this file. Please review the following
** information to ensure the GNU General Public License requirements will
** be met: https://www.gnu.org/licenses/gpl-2.0.html and
** https://www.gnu.org/licenses/gpl-3.0.html.
**
** $QT_END_LICENSE$
**
****************************************************************************/

"use strict";

var QWebChannelMessageTypes = {
    Init: 1,
    Idle: 2,
    Debug: 3,
    Reply: 4,
    Signal: 5,
    ConnectToSignal: 6,
    DisconnectFromSignal: 7,
    SetProperty: 8,
    InvokeMethod: 9
};

var QWebChannel = function(transport, initCallback)
{
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel transport object is invalid!");
        return;
    }

    var channel = this;
    this.transport = transport;

    this.send = function(data)
    {
        if (typeof data !== "string") {
            data = JSON.stringify(data);
        }
        channel.transport.send(data);
    };

    this.transport.onmessage = function(message)
    {
        var data = message.data;
        if (typeof data === "undefined") {
            console.error("Error: Message data is undefined");
            return;
        }
        if (typeof data === "string") {
            data = JSON.parse(data);
        }
        channel.handleMessage(data);
    };

    this.execCallbacks = {};
    this.execId = 0;
    this.exec = function(data, callback)
    {
        if (!callback) {
            channel.send(data);
            return;
        }
        var id = channel.execId++;
        channel.execCallbacks[id] = callback;
        data.id = id;
        channel.send(data);
    };

    this.objects = {};

    this.handleMessage = function(message)
    {
        switch (message.type) {
            case QWebChannelMessageTypes.Signal:
                channel.handleSignal(message);
                break;
            case QWebChannelMessageTypes.Reply:
                channel.handleReply(message);
                break;
            case QWebChannelMessageTypes.PropertyUpdate:
            case 8:
                channel.handlePropertyUpdate(message);
                break;
            default:
                console.warn("Unhandled message type: " + message.type);
                break;
        }
    };

    this.handleSignal = function(message)
    {
        var object = channel.objects[message.object];
        if (object) {
            object.signalEmitted(message.signal, message.args);
        } else {
            console.warn("Unhandled signal: " + message.object + "::" + message.signal);
        }
    };

    this.handleReply = function(message)
    {
        if (message.id in channel.execCallbacks) {
            var callback = channel.execCallbacks[message.id];
            delete channel.execCallbacks[message.id];
            callback(message.data);
        }
    };

    this.handlePropertyUpdate = function(message)
    {
        for (var i in message.data) {
            var data = message.data[i];
            var object = channel.objects[data.object];
            if (object) {
                object.propertyUpdate(data.signals, data.properties);
            } else {
                console.warn("Unhandled property update: " + data.object);
            }
        }
    };

    this.debug = function(message)
    {
        channel.send({type: QWebChannelMessageTypes.Debug, data: message});
    };

    this.exec({type: QWebChannelMessageTypes.Init}, function(data) {
        for (var objectName in data) {
            var object = new QObject(objectName, data[objectName], channel);
        }
        for (var objectName in data) {
            var object = channel.objects[objectName];
            object.unwrapProperties();
        }
        if (initCallback) {
            initCallback(channel);
        }
    });
};

function QObject(name, data, webChannel)
{
    this.__id__ = name;
    webChannel.objects[name] = this;
    this.__webChannel__ = webChannel;

    var obj = this;

    for (var i in data.methods) {
        var method = data.methods[i];
        this[method[0]] = (function(methodName) {
            return function() {
                var args = [];
                var callback;
                for (var i = 0; i < arguments.length; ++i) {
                    if (typeof arguments[i] === "function")
                        callback = arguments[i];
                    else
                        args.push(arguments[i]);
                }
                obj.__webChannel__.exec({
                    type: QWebChannelMessageTypes.InvokeMethod,
                    object: obj.__id__,
                    method: methodName,
                    args: args
                }, callback);
            };
        })(method[0]);
    }

    this.__signals__ = {};
    for (var i in data.signals) {
        var signal = data.signals[i];
        this[signal[0]] = (function(signalName) {
            var connections = [];
            var signalObject = {
                connect: function(callback) {
                    if (typeof callback !== "function") {
                        console.error("Bad callback passed to connect().");
                        return;
                    }
                    connections.push(callback);
                    if (connections.length === 1) {
                        obj.__webChannel__.exec({
                            type: QWebChannelMessageTypes.ConnectToSignal,
                            object: obj.__id__,
                            signal: signalName
                        });
                    }
                },
                disconnect: function(callback) {
                    if (typeof callback !== "function") {
                        console.error("Bad callback passed to disconnect().");
                        return;
                    }
                    var index = connections.indexOf(callback);
                    if (index === -1) {
                        console.error("Callback not found in connections of signal " + signalName);
                        return;
                    }
                    connections.splice(index, 1);
                    if (connections.length === 0) {
                        obj.__webChannel__.exec({
                            type: QWebChannelMessageTypes.DisconnectFromSignal,
                            object: obj.__id__,
                            signal: signalName
                        });
                    }
                }
            };
            obj.__signals__[signalName] = connections;
            return signalObject;
        })(signal[0]);
    }

    this.__properties__ = {};
    for (var i in data.properties) {
        var property = data.properties[i];
        var propertyName = property[0];
        var propertyValue = property[1];
        this.__properties__[propertyName] = propertyValue;

        (function(propName) {
            Object.defineProperty(obj, propName, {
                get: function() {
                    return obj.__properties__[propName];
                },
                set: function(value) {
                    if (value === undefined) {
                        console.error("Property value can't be undefined!");
                        return;
                    }
                    obj.__properties__[propName] = value;
                    obj.__webChannel__.exec({
                        type: QWebChannelMessageTypes.SetProperty,
                        object: obj.__id__,
                        property: propName,
                        value: value
                    });
                },
                configurable: true,
                enumerable: true
            });
        })(propertyName);
    }

    this.unwrapProperties = function()
    {
        for (var propName in obj.__properties__) {
            obj.__properties__[propName] = obj.__webChannel__.unwrap(obj.__properties__[propName]);
        }
    };

    this.signalEmitted = function(signalName, args)
    {
        var unwrappedArgs = [];
        for (var i in args) {
            unwrappedArgs.push(obj.__webChannel__.unwrap(args[i]));
        }

        var connections = obj.__signals__[signalName];
        if (connections) {
            for (var i in connections) {
                connections[i].apply(obj, unwrappedArgs);
            }
        }
    };

    this.propertyUpdate = function(signals, properties)
    {
        for (var name in properties) {
            obj.__properties__[name] = properties[name];
        }

        for (var signalName in signals) {
            obj.signalEmitted(signalName, signals[signalName]);
        }
    };
}

QWebChannel.prototype.unwrap = function(data)
{
    if (!data || typeof data !== "object") {
        return data;
    }

    if (data instanceof Array) {
        var result = [];
        for (var i in data) {
            result.push(this.unwrap(data[i]));
        }
        return result;
    }

    if (!data["__id__"]) {
        var result = {};
        for (var key in data) {
            result[key] = this.unwrap(data[key]);
        }
        return result;
    }

    var id = data["__id__"];
    if (this.objects[id]) {
        return this.objects[id];
    }

    return new QObject(id, data, this);
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { QWebChannel: QWebChannel };
}
