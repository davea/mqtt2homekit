MQTT to HomeKit
==================

* Register as a HomeKit Bridge.
* Listen for MQTT messages at `HomeKit/#`
* Add services automatically.
* Turn MQTT messages into HomeKit events.
* Turn HomeKit events into MQTT messages.



MQTT Messages.
---------------

The topics must always match the format:

    HomeKit/<accessory_id>/<service_type>/<characteristic>

For example, my DS18B20 temperature sensor would look like:

    HomeKit/28-0516c0fc92ff/TemperatureSensor/CurrentTemperature

It would then send the current temperature whenever it feels the need to this topic.


Where applicable, the device should also subscribe to it's own topics that it cares about.

A garage door opener may listen to:


    HomeKit/GarageDoor001/GarageDoor/+/set



Registering as a HomeKit Bridge
-------------------------------
