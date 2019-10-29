from mqtt2homekit.bridge import MQTTBridge


def test_load_optional_characteristic():
    bridge = MQTTBridge(display_name='Bridge', persist_file='tests/bridge_1.state', mqtt_server=None)
    assert len(bridge.accessories) == 1
    lightbulb = bridge.accessories[2].get_service('Lightbulb')
    assert lightbulb.characteristics[1].display_name == 'Brightness'
