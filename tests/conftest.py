import tempfile

import pytest

from mqtt2homekit.bridge import MQTTBridge


@pytest.fixture
def bridge(mocker):
    mocker.patch('pyhap.accessory_driver.AccessoryDriver.update_advertisement')
    return MQTTBridge(
        display_name='Test Bridge',
        persist_file=tempfile.mktemp(),
        mqtt_server=None
    )
