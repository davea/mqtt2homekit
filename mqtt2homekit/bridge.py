import random
import signal
import time
import logging
from functools import partial

from paho.mqtt import client as mqtt

from pyhap.accessory import Bridge
from pyhap.loader import get_serv_loader
from pyhap.accessory_driver import AccessoryDriver

from urllib.parse import urlparse

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
        self.mqtt_server = urlparse(kwargs.pop('mqtt_server'))
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
        accessory = self.get_accessory(accessory_id)

        if accessory:
            # Does this accessory have this service_type?
            if not accessory.get_service(service_type):
                # We need to add the service, but remove the accessory and then re-add it.
                # Otherwise, HomeKit will get all screwed up, and the bridge won't work anymore.
                self.accessories.pop(accessory.aid)
                accessory.aid = None
                accessory.add_service(get_serv_loader().get_service(service_type))
                self.add_accessory(accessory)
                self.config_changed()
        else:
            # Did not find the accessory: we need to create it.
            accessory = Accessory(display_name(service_type), services=[service_type], accessory_id=accessory_id)
            accessory.set_sentinel(self.run_sentinel, self.aio_stop_event, self.event_loop)
            self.add_accessory(accessory)
            self.config_changed()
        return accessory

    def get_accessory(self, accessory_id):
        for accessory in self.accessories.values():
            if accessory.accessory_id == accessory_id:
                return accessory

    def remove_accessory(self, accessory_id):
        for aid, accessory in self.accessories.items():
            if accessory_id == accessory.accessory_id:
                break
        else:
            return

        self.accessories.pop(aid)
        self.config_changed()

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
        """
        Create, and start, a driver for this accessory.
        """
        self.client = mqtt.Client()
        # We need to cause the driver to be instantiated, but we can't .start(), because that will block.
        self.driver
        self.client.on_connect = lambda client, userdata, flags, rc: client.subscribe('HomeKit/#', 1)
        self.client.message_callback_add('HomeKit/+/+/+', self.handle_mqtt_message)
        self.client.connect(self.mqtt_server.hostname, port=self.mqtt_server.port or 1883, keepalive=30)
        self.client.loop_start()
        self.driver.start()

    def stop(self):
        self.client.loop_stop(force=True)

    def run(self):
        while not self.run_sentinel.wait(ONE_MINUTE):
            self.flag_unseen()
            self.remove_missing()

    def flag_unseen(self):
        """
        Any that we haven't seen in the past hour we want to show in HomeKit as "not connected".

        This should only be those that were done with QoS=0?
        """
        now = time.time()
        for acc in list(self.accessories.values()):
            if acc.__last_seen and now - acc.__last_seen > ONE_MINUTE * 10:
                # Set all characteristics we have ever known about to None.
                print("Look like {} has no data".format(acc.accessory_id))
                if acc._should_flag_unseen:
                    acc.no_response()

    def remove_missing(self):
        """
        Any that we have not seen in 28 days, we want to remove.
        """
        now = time.time()
        for acc in list(self.accessories.values()):
            if acc.__last_seen and now - acc.__last_seen > ONE_DAY * 28:
                self.accessories.pop(acc.aid)
                self.config_changed()

    def handle_mqtt_message(self, client, userdata, message):
        _prefix, accessory_id, service_type, characteristic = message.topic.split('/')

        if not message.payload:
            # Should we only do this if it's the only service?
            # Otherwise we should remove the service, maybe?
            return self.remove_accessory(accessory_id)

        try:
            accessory = self.get_or_create_accessory(accessory_id, service_type)
            value = message.payload.decode('ascii')
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
        # We also assume that data being pushed from HomeKit should "persist" (retain=True),
        # because the user has set a state. Devices that can be controlled out of band of
        # HomeKit should also set retain=True on their messages.
        try:
            characteristic.set_value(value)
            self.client.publish(
                'HomeKit/{accessory_id}/{service}/{characteristic.display_name}'.format(
                    accessory_id=accessory.accessory_id,
                    service=service.display_name,
                    characteristic=characteristic,
                ),
                str(value).encode(),
                qos=2,
                retain=True,
            )
        except Exception as exc:
            LOGGER.error('Exception sending message: {}'.format(exc.args))
