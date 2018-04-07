import uuid
from collections import OrderedDict
import json
import random
import signal
import ed25519

from pyhap import accessory, loader
from pyhap.accessory_driver import AccessoryDriver
from pyhap.util import fromhex, tohex

from accessory import Accessory


class BridgeEncoder(object):
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
            "accessories": [
                key.split('/') + [accessory.aid]
                for key, accessory in bridge.known_accessories.items()
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

        for accessory_id, service_type, aid in state.get('accessories', []):
            bridge.known_accessories[
                '{}/{}'.format(accessory_id, service_type)
            ] = Accessory(service_type, service=service_type, aid=aid)


class MQTTBridge(accessory.Bridge):
    def __init__(self, *args, **kwargs):
        self.persist_file = kwargs.pop('persist_file')
        self.port = random.randint(50000, 60000)
        self._driver = None
        super().__init__(*args, **kwargs)
        # We need a way to map accessory_id to aid.
        self.known_accessories = OrderedDict()
        print(self.accessories)
        print(self.known_accessories)

    def _set_services(self):
        info_service = loader.get_serv_loader().get("AccessoryInformation")
        info_service.get_characteristic("Name")\
                    .set_value('MQTT Bridge', False)
        info_service.get_characteristic("Manufacturer")\
                    .set_value("Matthew Schinckel", False)
        info_service.get_characteristic("Model")\
                    .set_value("Bridge", False)
        info_service.get_characteristic("SerialNumber")\
                    .set_value("0001", False)
        self.add_service(info_service)

    def get_or_create_accessory(self, accessory_id, service_type):
        accessory_key = '{}/{}'.format(accessory_id, service_type)
        if accessory_key not in self.known_accessories:
            accessory = Accessory(service_type, service=service_type)
            accessory.set_sentinel(self.run_sentinel)
            self.known_accessories[accessory_key] = accessory
            self.add_accessory(accessory)
            self.config_changed()
            self.driver.persist()
        else:
            accessory = self.known_accessories[accessory_key]
            if accessory.aid not in self.accessories:
                self.add_accessory(accessory)
                self.config_changed()

        return accessory

    def handle_message(self, accessory_id, service_type, characteristic, value):
        accessory = self.get_or_create_accessory(accessory_id, service_type)
        accessory.set_characteristic(characteristic, value)

    @property
    def driver(self):
        if not self._driver:
            self._driver = AccessoryDriver(
                self,
                port=self.port,
                persist_file=self.persist_file,
                encoder=BridgeEncoder()
            )
            signal.signal(signal.SIGINT, self._driver.signal_handler)
            signal.signal(signal.SIGTERM, self._driver.signal_handler)
        return self._driver

    def start(self):
        self.driver.start()
        self.config_changed()
