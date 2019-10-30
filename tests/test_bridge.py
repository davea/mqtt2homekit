import os
import tempfile

import pyhap.accessory_driver

from mqtt2homekit.bridge import MQTTBridge


def test_config_changed(mocker):
    mocker.patch('os.path.expanduser')
    mocker.patch('pyhap.accessory_driver.AccessoryDriver.update_advertisement')
    os.path.expanduser.return_value = tempfile.mktemp()
    bridge = MQTTBridge(display_name='Bridge', persist_file='x', mqtt_server=None)
    bridge.config_changed()
    pyhap.accessory_driver.AccessoryDriver.update_advertisement.assert_called_once()


def test_add_and_remove_accessory(mocker):
    mocker.patch('os.path.expanduser')
    mocker.patch('pyhap.accessory_driver.AccessoryDriver.update_advertisement')
    os.path.expanduser.return_value = tempfile.mktemp()
    bridge = MQTTBridge(display_name='Bridge', persist_file='x', mqtt_server=None)
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
