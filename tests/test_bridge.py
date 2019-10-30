import tempfile

from paho.mqtt.client import MQTTMessage
import pyhap.accessory_driver
import pytest

from mqtt2homekit.accessory import Accessory
from mqtt2homekit.bridge import MQTTBridge


@pytest.fixture
def bridge(mocker):
    mocker.patch('pyhap.accessory_driver.AccessoryDriver.update_advertisement')
    return MQTTBridge(
        display_name='Test Bridge',
        persist_file=tempfile.mktemp(),
        mqtt_server=None
    )


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

    # Should create a new one: different code path for second accessory though.
    temp = bridge.get_or_create_accessory('Foo', 'TemperatureSensor')
    assert temp
    assert len(bridge.accessories) == 1

    # We can remove an accessory.
    bridge.remove_accessory('Foo')
    assert len(bridge.accessories) == 0

    # Repeated removal (or removal of non existent accessory) continues silently.
    bridge.remove_accessory('Foo')


def test_handle_mqtt_messages(bridge, mocker):
    mocker.patch('mqtt2homekit.accessory.Accessory.set_characteristic')

    bridge.handle_mqtt_message(None, None, Message(topic=b'Homekit/Foo/Lightbulb/On', payload=b'1'))
    Accessory.set_characteristic.assert_called_once()

    bridge.handle_mqtt_message(None, None, MQTTMessage(topic=b'Homekit/Foo/AccessoryInformation/Name'))

    bridge.handle_mqtt_message(None, None, MQTTMessage(topic=b'Homekit/Foo/Lightbulb/On'))
    assert not bridge.accessories
