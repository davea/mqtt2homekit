import json
import random
import signal
import time
import uuid

import ed25519

from paho.mqtt import client as mqtt

from pyhap import accessory, loader
from pyhap.accessory_driver import AccessoryDriver
from pyhap.util import fromhex, tohex

from accessory import Accessory
from utils import display_name


ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24


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
            # We need to be able to load all of the existing accessories, ensuring
            # they retain their aid, but we don't always want to add them to the
            # bridge, until we see they still exist on the network. So, we need to
            # store the aid here.
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

        # As mentioned above, we don't want to load the accessories into the
        # bridge because if they have been removed from the network, we don't
        # want to show them in HomeKit.
        for accessory_id, service_type, aid in state.get('accessories', []):
            bridge.known_accessories[
                '{}/{}'.format(accessory_id, service_type)
            ] = Accessory(
                display_name(service_type),
                service=service_type,
                aid=aid,
            )


class MQTTBridge(accessory.Bridge):
    def __init__(self, *args, **kwargs):
        self.persist_file = kwargs.pop('persist_file')
        self.port = random.randint(50000, 60000)
        self._driver = None
        self._mqtt_settings = kwargs.pop('mqtt_settings', {})
        super().__init__(*args, **kwargs)
        self.known_accessories = {}

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

    def add_accessory(self, accessory):
        # For every accessory, we also configure a callback for every characteristic.
        # This will allow us to push onto the MQTT when we get notified by HomeKit that
        # something needs to change.
        super().add_accessory(accessory)
        for characteristic in accessory.service.characteristics:
            characteristic.setter_callback = lambda value: self.send_mqtt_message(accessory, characteristic, value)

    def get_accessory_key(self, accessory):
        for key, known in self.known_accessories.items():
            if accessory == known:
                return key

    def get_or_create_accessory(self, accessory_id, service_type):
        accessory_key = '{}/{}'.format(accessory_id, service_type)
        if accessory_key not in self.known_accessories:
            accessory = Accessory(display_name(service_type), service=service_type)
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

    def start(self, mqtt_server='localhost', mqtt_port=1883, mqtt_timeout=60):
        self.client = mqtt.Client()
        self.client.on_connect = lambda client, userdata, flags, rc: client.subscribe('HomeKit/#')
        self.client.message_callback_add('HomeKit/+/+/+', self.handle_mqtt_message)
        self.driver.start()
        self.config_changed()
        self.client.connect(mqtt_server, mqtt_port, mqtt_timeout)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop(force=True)

    def run(self):
        while not self.run_sentinel.wait(ONE_HOUR):
            self.hide_unseen()

    def hide_unseen(self, since=ONE_DAY):
        # When should we remove them from known_accessories? After FOUR_WEEKS?
        now = time.time()
        for aid, acc in list(self.accessories.items()):
            if now - acc.__last_seen > since:
                self.accessories.pop(aid)
                self.config_changed()

    def handle_mqtt_message(self, client, userdata, message):
        _prefix, accessory_id, service_type, characteristic = message.topic.split('/')
        accessory = self.get_or_create_accessory(accessory_id, service_type)
        value = message.payload.decode('ascii')
        accessory.set_characteristic(characteristic, value)
        accessory.__last_seen = time.time()

    def send_mqtt_message(self, accessory, characteristic, value):
        self.client.publish(
            'HomeKit/{0}/{1}/{characteristic.display_name}'.format(
                *self.get_accessory_key(accessory).split('/'),
                characteristic=characteristic,
            ),
            str(value)
        )
