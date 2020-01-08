import tempfile
from unittest.mock import PropertyMock

import pytest

from mqtt2homekit.bridge import MQTTBridge


@pytest.fixture
def bridge(mocker):
    mocker.patch('pyhap.accessory_driver.AccessoryDriver.update_advertisement')
    bridge = MQTTBridge(
        display_name='Test Bridge',
        persist_file=tempfile.mktemp(),
        mqtt_server=None,
        prefix='__TEST__',
    )
    bridge.client = PropertyMock()
    return bridge