import json
from io import StringIO
import tempfile
from unittest.mock import MagicMock

from mqtt2homekit.bridge import MQTTBridge
from mqtt2homekit.encoder import BridgeEncoder


def test_load_optional_characteristic():
    persist_file = tempfile.mktemp()
    open(persist_file, 'w').write(open('tests/bridge_1.state').read())
    bridge = MQTTBridge(display_name='Bridge', persist_file=persist_file, mqtt_server=None)
    lightbulb = bridge.accessories[2].get_service('Lightbulb')
    assert lightbulb.characteristics[1].display_name == 'Brightness'


def test_persist(mocker):
    mocker.patch('pyhap.encoder.AccessoryEncoder.persist')
    mocker.patch('json.loads')
    json.loads.return_value = {
        'mac': '12:34:56:78:ab:cd',
        'config_version': 1,
        'paired_clients': [],
        'private_key': 'b0167fb8-96ab-435b-b347-ee669cc410b8',
        'public_key': '66504ec7-2a93-4e9a-a51b-cd007ae1792a',
    }
    bridge = MagicMock()
    stream = StringIO()
    BridgeEncoder(bridge=bridge).persist(stream, bridge.state)
    mocker.stopall()
    data = json.loads(stream.getvalue())
    assert data['accessories'] == []
