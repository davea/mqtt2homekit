import json
import random
import signal
import time
import uuid
import logging

import ed25519

from paho.mqtt import client as mqtt

from pyhap.accessory import Bridge
from pyhap.loader import get_serv_loader
from pyhap.accessory_driver import AccessoryDriver
from pyhap.util import fromhex, tohex

from accessory import Accessory
from utils import display_name


LOGGER = logging.getLogger(__name__)

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
                    "last_seen": getattr(accessory, '__last_seen', time.time()),
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
            acc.__last_seen = accessory.get('last_seen', time.time())
            bridge.add_accessory(acc)


class MQTTBridge(Bridge):
    def __init__(self, *args, **kwargs):
        self.persist_file = kwargs.pop('persist_file')
        self.port = random.randint(50000, 60000)
        self._driver = None
        self._mqtt_settings = kwargs.pop('mqtt_settings', {})
        super().__init__(*args, **kwargs)

    def _set_services(self):
        info_service = get_serv_loader().get("AccessoryInformation")
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
        for service in accessory.services:
            for characteristic in service.characteristics:
                characteristic.setter_callback = lambda value: self.send_mqtt_message(
                    accessory, service, characteristic, value)

    @property
    def known_accessories(self):
        return {accessory.accessory_id: accessory for accessory in self.accessories.values()}

    def get_or_create_accessory(self, accessory_id, service_type):
        if accessory_id not in self.known_accessories:
            # Need to add this accessory to our registry.
            # If this is not a valid accessory main service, we should just exit now...
            accessory = Accessory(display_name(service_type), services=[service_type], accessory_id=accessory_id)
            accessory.set_sentinel(self.run_sentinel)
            self.add_accessory(accessory)
            self.config_changed()
            self.persist()
        accessory = self.known_accessories[accessory_id]

        if not accessory.get_service(service_type):
            service = get_serv_loader().get(service_type)
            self.accessories.pop(accessory.aid)
            accessory.aid = None
            accessory.add_service(service)
            self.add_accessory(accessory)
            self.config_changed()
            self.persist()

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
        self.client.on_connect = lambda client, userdata, flags, rc: client.subscribe('HomeKit/#', 1)
        self.client.message_callback_add('HomeKit/+/+/+', self.handle_mqtt_message)
        self.driver.start()
        self.config_changed()
        self.client.connect(mqtt_server, mqtt_port, mqtt_timeout)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop(force=True)
        self.persist()

    def run(self):
        while not self.run_sentinel.wait(ONE_HOUR):
            self.hide_unseen()

    def persist(self):
        return self.driver.persist()

    def hide_unseen(self, since=ONE_DAY * 28):
        # When should we remove them from known_accessories? After FOUR_WEEKS?
        now = time.time()
        for acc in list(self.accessories.values()):
            if now - acc.__last_seen > since:
                self.accessories.pop(acc.aid)
                self.config_changed()

    def handle_mqtt_message(self, client, userdata, message):
        try:
            _prefix, accessory_id, service_type, characteristic = message.topic.split('/')
            accessory = self.get_or_create_accessory(accessory_id, service_type)
            value = message.payload.decode('ascii')
            LOGGER.debug('SET {accessory_id} {service_type} {characteristic} -> {value}'.format(
                accessory_id=accessory_id,
                service_type=service_type,
                characteristic=characteristic,
                value=value,
            ))
            accessory.set_characteristic(service_type, characteristic, value)
            accessory.__last_seen = time.time()
        except Exception as exc:
            LOGGER.error('Exception handling message {}'.format(exc.args))

    def send_mqtt_message(self, accessory, service, characteristic, value):
        # We always send messages with QoS 2 - this means clients may choose how they want
        # to subscribe.
        # Should this be setting persist=True? I feel like that's up to the actual device.
        try:
            self.client.publish(
                'HomeKit/{accessory_id}/{service}/{characteristic.display_name}'.format(
                    accessory_id=accessory.accessory_id,
                    service=service.display_name,
                    characteristic=characteristic,
                ),
                str(value),
                qos=2,
            )
        except Exception as exc:
            LOGGER.error('Exception sending message: {}'.format(exc.args))
