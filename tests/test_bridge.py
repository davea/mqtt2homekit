import pyhap.accessory_driver
from paho.mqtt.client import MQTTMessage

from mqtt2homekit.accessory import Accessory


class Message(MQTTMessage):
    def __init__(self, topic=b'', payload=b''):
        super().__init__(topic=topic)
        self.payload = payload


def test_config_changed(bridge):
    bridge.config_changed()
    pyhap.accessory_driver.AccessoryDriver.update_advertisement.assert_called_once()


def test_add_and_remove_accessory(bridge, mocker):
    # Should create a new one.
    bulb = bridge.get_or_create_accessory('Foo', 'Lightbulb')
    assert bulb
    assert len(bridge.accessories) == 1

    # Should fetch the existing one.
    bulb = bridge.get_or_create_accessory('Foo', 'Lightbulb')
    assert bulb
    assert len(bridge.accessories) == 1

    # Should create a new service: different code path for second service though.
    temp = bridge.get_or_create_accessory('Foo', 'TemperatureSensor')
    assert temp
    assert temp == bulb
    assert len(bridge.accessories) == 1

    bulb2 = bridge.get_or_create_accessory('Foo', 'Lightbulb', index=3)
    assert bulb2
    assert bulb == bulb2
    # Should be 4 bulbs, and the temperature sensor.
    assert len(bulb2.services)
    assert len(bridge.accessories) == 1

    # We can remove an accessory.
    bridge.remove_accessory('Foo')
    assert len(bridge.accessories) == 0

    # Repeated removal (or removal of non existent accessory) continues silently.
    bridge.remove_accessory('Foo')


def test_handle_mqtt_messages(bridge, mocker):
    mocker.patch('mqtt2homekit.accessory.Accessory.set_characteristic')

    bridge.handle_mqtt_message(None, None, Message(topic=b'__TEST__/Foo/Lightbulb/On', payload=b'1'))
    Accessory.set_characteristic.assert_called_once()

    bridge.handle_mqtt_message(None, None, MQTTMessage(topic=b'__TEST__/Foo/AccessoryInformation/Name'))

    bridge.handle_mqtt_message(None, None, MQTTMessage(topic=b'__TEST__/Foo/Lightbulb/On'))
    assert not bridge.accessories


def test_accessory_with_multiple_services(bridge, mocker):
    mocker.patch('mqtt2homekit.accessory.Accessory.set_characteristic')
    bridge.handle_mqtt_message(None, None, Message(topic=b'__TEST__/Foo/Lightbulb/3/On', payload=b'1'))
    Accessory.set_characteristic.assert_called_once()
    assert bridge.accessories
    assert bridge.client
    bulb = bridge.get_or_create_accessory('Foo', 'Lightbulb', index=3)
    assert bulb.get_services('Lightbulb')[3]


def test_setting_characteristics(bridge, mocker):
    bulb = bridge.get_or_create_accessory('Foo', 'Lightbulb')
    on = bulb.get_service('Lightbulb').get_characteristic('On')
    assert on.setter_callback
    on.client_update_value(1)
    bridge.client.publish.assert_called_once_with('__TEST__/Foo/Lightbulb/On', b'1', qos=2, retain=True)


def test_setting_characteristics_multiple_services(bridge, mocker):
    bulb = bridge.get_or_create_accessory('Foo', 'Lightbulb', 3)
    on = bulb.get_service('Lightbulb', 0).get_characteristic('On')
    assert on.setter_callback
    on.client_update_value(1)
    bridge.client.publish.assert_called_once_with('__TEST__/Foo/Lightbulb/0/On', b'1', qos=2, retain=True)


def test_setting_Accessory(bridge):
    name = bridge.get_service('AccessoryInformation').get_characteristic('Name')
    name.client_update_value('Renamed')
