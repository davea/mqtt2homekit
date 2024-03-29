import json
import logging
import time
from io import StringIO

from pyhap.encoder import AccessoryEncoder

from .accessory import Accessory
from .loader import loader

LOGGER = logging.getLogger(__name__)


class BridgeEncoder(AccessoryEncoder):
    """
    We want to override the functionality of the standard encoder, and add the accessories
    we know about to the state file.
    """
    def __init__(self, bridge):
        self.bridge = bridge

    def persist(self, fp, state):
        bridge = self.bridge
        _fp = StringIO()
        super().persist(_fp, state)
        state = json.loads(_fp.getvalue())
        state['accessories'] = [
            {
                "accessory_id": accessory.accessory_id,
                "name": accessory.display_name,
                "services": [
                    service.display_name
                    for service in accessory.services
                    if service.display_name != 'AccessoryInformation'
                ],
                "aid": accessory.aid,
                "last_seen": getattr(accessory, '_last_seen', time.time()),
                "optional_characteristics": {
                    service.display_name: [
                        characteristic.display_name
                        for characteristic in service.characteristics
                        if characteristic.display_name not in [
                            char.display_name
                            for char in loader.get_service(service.display_name).characteristics
                        ]
                    ]
                    for service in accessory.services
                    if service.display_name != 'AccessoryInformation'
                }
            }
            for aid, accessory in bridge.accessories.items() if aid != 1
        ]
        json.dump(state, fp, indent=2)

    def load_into(self, fp, state):
        bridge = self.bridge
        super().load_into(fp, state)

        fp.seek(0)
        loaded = json.load(fp)

        for accessory in loaded.get('accessories', []):
            acc = Accessory(
                bridge.driver,
                accessory['name'],
                aid=accessory['aid'],
                services=accessory['services'],
                accessory_id=accessory['accessory_id'],
                optional_characteristics=accessory.get('optional_characteristics', {})
            )
            acc._last_seen = accessory.get('last_seen', time.time())
            bridge.add_accessory(acc)
            # Mark the accessory as no response, so it will have to trigger it's own update.
            # acc.no_response()
