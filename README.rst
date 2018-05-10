MQTT to HomeKit
==================

Transparently bridge an MQTT topic tree to HomeKit.

* Register as a HomeKit Bridge.
* Listen for MQTT messages at `HomeKit/#`
* Add accessories/services automatically.
* Turn MQTT messages into HomeKit events.
* Turn HomeKit events into MQTT messages.


Usage.
------

From your shell, execute::

    $ pipenv install
    $ pipenv run mqtt2homekit/main.py

As long as your MQTT broker is on the same machine as this bridge is running, then everything should work correctly. Otherwise, you'll need to change that hostname.


MQTT Messages.
---------------

The topics must always match the format::

    HomeKit/<accessory_id>/<service_type>/<characteristic>

For example, my DS18B20 temperature sensor would look like::

    HomeKit/28-0516c0fc92ff/TemperatureSensor/CurrentTemperature

It would then send the current temperature whenever it wants to, to this topic.


Where applicable, the device should also subscribe to it's own topics that it cares about.

A switch could subscribe to::

    HomeKit/Sonoff-112154/Switch/On

This is the topic to which the state change would be sent to when HomeKit triggers an On/Off event.


Removing accessories.
---------------------

When an empty message is received, it will remove the accessory.

(Maybe it should remove the service, unless this is the only service).


Bridging behaviour.
-------------------

When the bridge receives an MQTT message that matches ``HomeKit/+/+/+``, it looks to see if it has a matching accessory (first wildcard) already in the registry. If it does not, then it creates a new Accessory with a single service of the ``<service_type>`` (second wildcard). It if does, and the accessory does not have the provided service, then a new service of this type is added. Then, the characteristic (last wildcard) is set to the value of the message body.

When a new service is added to an accessory, it is removed from the bridge and re-added: this was required to prevent the bridge from becoming inaccessible to HomeKit.


When HomeKit sends the brige a message, it is turned into an MQTT message according to the ``<accessory_id>``, ``<service_type>`` and ``<characteristic>``, with the value that was set being used for the message body.

All MQTT messages that are sent by the bridge are QoS=2, so that clients may select the QoS they want.
