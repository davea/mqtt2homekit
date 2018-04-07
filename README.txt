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

    $ pipenv install
    $ pipenv run mqtt2homekit/main.py

As long as your MQTT broker is on the same machine as this bridge is running, then everything
should work correctly. Otherwise, you'll need to change that hostname.


MQTT Messages.
---------------

The topics must always match the format:

    HomeKit/<accessory_id>/<service_type>/<characteristic>

For example, my DS18B20 temperature sensor would look like:

    HomeKit/28-0516c0fc92ff/TemperatureSensor/CurrentTemperature

It would then send the current temperature whenever it wants to, to this topic.


Where applicable, the device should also subscribe to it's own topics that it cares about.

A switch could subscribe to:

    HomeKit/Sonoff-112154/Switch/On

This is the topic to which the state change would be sent to when HomeKit triggers an On/Off event.
