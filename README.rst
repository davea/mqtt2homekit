MQTT to HomeKit
==================

|build-status|

.. |build-status| image:: https://builds.sr.ht/~schinckel/mqtt2homekit.svg
                  :height: 20pt
                  :alt: Build status
                  :target: https://builds.sr.ht/~schinckel/mqtt2homekit?

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
    $ pipenv run mqtt2homekit/main.py --broker mqtt://mqtt.lan

Adjusting your broker url accordingly.


MQTT Messages.
---------------

The topics must always match the format::

    HomeKit/<accessory_id>/<service_type>/<characteristic>

Or, if there are multiple services of the same type in an accessory::

	HomeKit/<accessory_id>/<service_type>/<index>/<characteristic>

For example, my DS18B20 temperature sensor would look like::

    HomeKit/28-0516c0fc92ff/TemperatureSensor/CurrentTemperature

It would then send the current temperature whenever it wants to, to this topic.


Where applicable, the device should also subscribe to it's own topics that it cares about.

A switch could subscribe to::

    HomeKit/Sonoff-112154/Switch/On

This is the topic to which the state change would be sent to when HomeKit triggers an On/Off event.

Because HomeKit sometimes sends `True` or `False`, and sometimes sends `1` or `0`, we normalise this to the integer value that corresponds to the boolean value.

If there are multiple services of the same type, then the topics need to reflect that::

	HomeKit/Sonoff-112154/Switch/0/On
	HomeKit/Sonoff-112154/Switch/1/On

and so on.


Command line options.
---------------------

You may supply arguments to configure the bridge:

	* ``--persist``: the filename of the state file that contains the data for this bridge. Default: ``bridge.state``
	* ``--broker``: the URL to use for the MQTT broker. Default: ``mqtt://mqtt.lan``
	* ``--name``: the name to give this bridge. Default: ``MQTT Bridge``
	* ``--prefix``: the topic prefix to use instead of the default ``HomeKit``.

You must change the name when running a second bridge on the same device, and you should probably change the prefix if you are running multiple bridges that share the same broker.

Removing accessories.
---------------------

When an empty message is received, it will remove the accessory.

(Maybe it should remove the service, unless this is the only service).


Bridging behaviour.
-------------------

When the bridge receives an MQTT message that matches ``{prefix}/+/+/+``, it looks to see if it has a matching accessory (first wildcard) already in the registry. If it does not, then it creates a new Accessory with a single service of the ``<service_type>`` (second wildcard). It if does, and the accessory does not have the provided service, then a new service of this type is added. Then, the characteristic (last wildcard) is set to the value of the message body.

If messages matching ``{prefix}/+/+/{index}/+`` are detected, then the bridge assumes this is a multi-service accessory, which at least ``index + 1`` services of the specified type, and adds the missing ones if required.

When a new service is added to an accessory, it is removed from the bridge and re-added: this was required to prevent the bridge from becoming inaccessible to HomeKit.


When HomeKit sends the brige a message, it is turned into an MQTT message according to the ``<accessory_id>``, ``<service_type>`` and ``<characteristic>`` (and the optional ``<index>``, if there are multiple services of this type in the accessory), with the value that was set being used for the message body.

All MQTT messages that are sent by the bridge are QoS=2, so that clients may select the QoS they want.
