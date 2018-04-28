import asyncio
import random
import signal
import time
import logging


from hbmqtt.client import MQTTClient, ClientException, QOS_1

from pyhap.accessory import Bridge
from pyhap.loader import get_serv_loader
from pyhap.accessory_driver import AccessoryDriver

from accessory import Accessory
from encoder import BridgeEncoder
from utils import display_name


LOGGER = logging.getLogger(__name__)

ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24


class MQTTBridge(Bridge):
    def __init__(self, *args, **kwargs):
        self.persist_file = kwargs.pop('persist_file')
        self.port = random.randint(50000, 60000)
        self._driver = None
        super().__init__(*args, **kwargs)

    def _set_services(self):
        info_service = get_serv_loader().get("AccessoryInformation")
        info_service.get_characteristic("Name").set_value('MQTT Bridge', False)
        info_service.get_characteristic("Manufacturer").set_value("Matthew Schinckel", False)
        info_service.get_characteristic("Model").set_value("Bridge", False)
        info_service.get_characteristic("SerialNumber").set_value("0001", False)
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

    @asyncio.coroutine
    def start_mqtt_client(self, uri):
        try:
            self.client = MQTTClient()
            yield from self.client.connect(uri)
            print(self.client._handler)
            yield from self.client.subscribe([('HomeKit/+/+/+', QOS_1)])
            while True:
                message = yield from self.client.deliver_message()
                yield from self.handle_mqtt_message(message)
        except ClientException as ce:
            LOGGER.error('Client exception: %s' % ce)
        finally:
            # disconnect() when not connected is explicitly ignored.
            yield from self.client.disconnect()
            self.driver.stop()

    def start(self, uri):
        self.driver.start()
        self.config_changed()
        asyncio.get_event_loop().run_until_complete(self.start_mqtt_client(uri))

    def stop(self):
        asyncio.get_event_loop().stop()
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

    @asyncio.coroutine
    def handle_mqtt_message(self, message):
        try:
            _prefix, accessory_id, service_type, characteristic = message.topic.split('/')
            accessory = self.get_or_create_accessory(accessory_id, service_type)
            value = message.data.decode()
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
