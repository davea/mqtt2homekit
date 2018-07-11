import json
import time
import uuid

import ed25519

from pyhap.util import fromhex, tohex

from accessory import Accessory


class BridgeEncoder(object):
    """
    It's not really possible to override the functionality of the
    pyhap.encoder.AccessoryEncoder, so we need to duplicate the
    functionality, and then add on to it.

    https://github.com/ikalchev/HAP-python/issues/80
    """
    def persist(self, fp, bridge):
        paired_clients = {
            str(client): tohex(key)
            for client, key in bridge.paired_clients.items()
        }
        config_state = {
            "mac": bridge.mac,
            "config_version": bridge.config_version,
            "paired_clients": paired_clients,
            "private_key": tohex(bridge.private_key.to_seed()),
            "public_key":  tohex(bridge.public_key.to_bytes()),
            # We need to be able to load all of the existing accessories, with aid and last access time.
            "accessories": [
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
                }
                for aid, accessory in bridge.accessories.items() if aid != 1
            ]
        }
        json.dump(config_state, fp)

    def load_into(self, fp, bridge):
        state = json.load(fp)
        bridge.mac = state["mac"]
        bridge.config_version = state["config_version"] + 1
        bridge.paired_clients = {
            uuid.UUID(client): fromhex(key)
            for client, key in state["paired_clients"].items()
        }
        bridge.private_key = ed25519.SigningKey(fromhex(state["private_key"]))
        bridge.public_key = ed25519.VerifyingKey(fromhex(state["public_key"]))

        for accessory in state.get('accessories', []):
            acc = Accessory(
                accessory['name'],
                aid=accessory['aid'],
                services=accessory['services'],
                accessory_id=accessory['accessory_id'],
            )
            acc._last_seen = accessory.get('last_seen', time.time())
            bridge.add_accessory(acc)
            # Mark the accessory as no response, so it will have to trigger it's own update.
            acc.no_response()
