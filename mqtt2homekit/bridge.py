import asyncio
import random
import signal
import time
import logging
from functools import partial

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
        self.mqtt_server = kwargs.pop('mqtt_server')
        self.port = random.randint(50000, 60000)
        self._driver = None
        super().__init__(*args, **kwargs)

    def _set_services(self):
        info_service = get_serv_loader().get_service("AccessoryInformation")
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
                characteristic.setter_callback = partial(self.send_mqtt_message, accessory, service, characteristic)

    def get_or_create_accessory(self, accessory_id, service_type):
        """
        Dynamically find or add an accessory with the provided id and service_type.

        If we already have an accessory with this id, and a different type, then add
        a new service to that accessory.

        Either of these conditions should result in the bridge updating HomeKit, and
        also persisting data to the disk: any other situation should just return
        the relevant accessory.
        """
        for accessory in self.accessories.values():
            if accessory_id == accessory.accessory_id:
                # Does this accessory have this service_type?
                if not accessory.get_service(service_type):
                    # We need to add the service, but remove the accessory and then re-add it.
                    # Otherwise, HomeKit will get all screwed up, and the bridge won't work anymore.
                    self.accessories.pop(accessory.aid)
                    accessory.aid = None
                    accessory.add_service(get_serv_loader().get_service(service_type))
                    self.add_accessory(accessory)
                    self.config_changed()
                return accessory

        # Did not find the accessory: we need to create it.
        accessory = Accessory(display_name(service_type), services=[service_type], accessory_id=accessory_id)
        accessory.set_sentinel(self.run_sentinel, self.aio_stop_event, self.event_loop)
        self.add_accessory(accessory)
        self.config_changed()
        return accessory

    def remove_accessory(self, accessory_id):
        for aid, accessory in self.accessories.items():
            if accessory_id == accessory.accessory_id:
                break
        else:
            return

        self.accessories.pop(aid)
        self.config_changed()

    @asyncio.coroutine
    def start_mqtt_client(self):
        try:
            self.client = MQTTClient()
            yield from self.client.connect(self.mqtt_server)
            yield from self.client.subscribe([('HomeKit/+/+/+', QOS_1)])
            while True:
                message = yield from self.client.deliver_message()
                self.handle_mqtt_message(message)
        except ClientException as ce:
            LOGGER.error('Client exception: %s' % ce)
        finally:
            # disconnect() when not connected is explicitly ignored.
            yield from self.client.disconnect()

    def start(self):
        """
        Create, and start, a driver for this accessory.
        """
        driver = AccessoryDriver(
            self,
            port=self.port,
            persist_file=self.persist_file,
            encoder=BridgeEncoder()
        )
        signal.signal(signal.SIGINT, driver.signal_handler)
        signal.signal(signal.SIGTERM, driver.signal_handler)
        driver.start()

    def stop(self):
        asyncio.get_event_loop().stop()

    def run(self):
        self.loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.start_mqtt_client())
        self.loop.run_forever()

    @Bridge.run_at_interval(ONE_HOUR)
    def remove_missing(self, since=ONE_DAY * 28):
        now = time.time()
        for acc in list(self.accessories.values()):
            if now - acc.__last_seen > since:
                self.accessories.pop(acc.aid)
                self.config_changed()

    def handle_mqtt_message(self, message):
        _prefix, accessory_id, service_type, characteristic = message.topic.split('/')

        if not message.data:
            # Should we only do this if it's the only service?
            # Otherwise we should remove the service, maybe?
            return self.remove_accessory(accessory_id)

        try:
            accessory = self.get_or_create_accessory(accessory_id, service_type)
            value = message.data.decode()
            LOGGER.debug('SET {accessory_id} {service_type} {characteristic} -> {value}'.format(
                accessory_id=accessory_id,
                service_type=service_type,
                characteristic=characteristic,
                value=value,
            ))
            # If we have an empty message, then perhaps we need to do nothing...?
            accessory.set_characteristic(service_type, characteristic, value)
            accessory.__last_seen = time.time()
        except Exception as exc:
            LOGGER.error('Exception handling message {}'.format(exc.args))

    def send_mqtt_message(self, accessory, service, characteristic, value):
        # We always send messages with QoS 2 - this means clients may choose how they want
        # to subscribe.
        # Should this be setting persist=True? I feel like that's up to the actual device.
        try:
            asyncio.run_coroutine_threadsafe(self.client.publish(
                'HomeKit/{accessory_id}/{service}/{characteristic.display_name}'.format(
                    accessory_id=accessory.accessory_id,
                    service=service.display_name,
                    characteristic=characteristic,
                ),
                str(value).encode(),
                qos=2,
            ), self.loop)
        except Exception as exc:
            LOGGER.error('Exception sending message: {}'.format(exc.args))
