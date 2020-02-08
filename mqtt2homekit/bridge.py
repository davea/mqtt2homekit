import logging
import random
import signal
import time
from functools import partial
from urllib.parse import urlparse

from paho.mqtt import client as mqtt
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.loader import get_loader

from .accessory import Accessory
from .encoder import BridgeEncoder
from .utils import display_name

LOGGER = logging.getLogger(__name__)

ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24


def build_driver(bridge, port, persist_file):
    driver = AccessoryDriver(
        port=port,
        persist_file=persist_file,
        encoder=BridgeEncoder(bridge)
    )
    signal.signal(signal.SIGINT, driver.signal_handler)
    signal.signal(signal.SIGTERM, driver.signal_handler)
    return driver


class MQTTBridge(Bridge):
    def __init__(self, display_name, **kwargs):
        self.persist_file = kwargs.pop('persist_file')
        self.mqtt_server = urlparse(kwargs.pop('mqtt_server'))
        self.port = random.randint(50000, 60000)
        self.prefix = kwargs.pop('prefix', 'HomeKit')
        driver = build_driver(self, self.port, self.persist_file)
        # This sets self.driver
        super().__init__(driver, display_name, **kwargs)
        driver.add_accessory(accessory=self)
        # if Path(self.persist_file).exists():
        #     driver.load()

    def add_info_service(self):
        info_service = get_loader().get_service("AccessoryInformation")
        info_service.configure_char("Name", value='MQTT Bridge')
        info_service.configure_char("Manufacturer", value="Matthew Schinckel")
        info_service.configure_char("Model", value="Bridge")
        info_service.configure_char("SerialNumber", value="02b26429-cb8b-47cd-a27a-2feb33996cde")
        info_service.configure_char("FirmwareRevision", value="1")
        self.add_service(info_service)

    def add_accessory(self, accessory):
        # For every accessory, we also configure a callback for every characteristic.
        # This will allow us to push onto the MQTT when we get notified by HomeKit that
        # something needs to change.
        super().add_accessory(accessory)

        def add_characteristic(service, characteristic):
            LOGGER.debug('Set setter_callback for {accessory}: {service}.{characteristic}'.format(
                accessory=accessory,
                service=service,
                characteristic=characteristic,
            ))
            characteristic.setter_callback = partial(self.send_mqtt_message, accessory, service, characteristic)

        accessory.add_characteristic = add_characteristic

        for service in accessory.services:
            if service.display_name == 'AccessoryInformation':
                continue

            for characteristic in service.characteristics:
                accessory.add_characteristic(service, characteristic)

    def config_changed(self):
        self.driver.config_changed()

    def get_or_create_accessory(self, accessory_id, service_type, index=0):
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
            if not accessory.get_service(service_type, index):
                # We need to add the service, but remove the accessory and then re-add it.
                # Otherwise, HomeKit will get all screwed up, and the bridge won't work anymore.
                self.accessories.pop(accessory.aid)
                accessory.aid = None
                accessory.add_service(get_loader().get_service(service_type))
                self.add_accessory(accessory)
                self.config_changed()
        else:
            # Did not find the accessory: we need to create it. Ensure we have
            # (index + 1) instances of the service.
            accessory = Accessory(
                self.driver,
                display_name(service_type),
                services=[service_type] * (index + 1),
                accessory_id=accessory_id,
            )
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

    async def run(self):
        """
        Create, and start, a driver for this accessory.
        """
        self.client = mqtt.Client()
        self.client.on_connect = lambda client, userdata, flags, rc: client.subscribe('{}/#'.format(self.prefix), 1)
        self.client.message_callback_add('{}/+/+/+'.format(self.prefix), self.handle_mqtt_message)
        self.client.message_callback_add('{}/+/+/+/+'.format(self.prefix), self.handle_mqtt_message)
        try:
            self.client.connect(self.mqtt_server.hostname, port=self.mqtt_server.port or 1883, keepalive=30)
        except ConnectionRefusedError:
            LOGGER.critical('Unable to connect to MQTT Broker')
            return
        self.client.loop_start()
        await super().run()

    async def stop(self):
        await super().stop()
        self.client.loop_stop(force=True)
        # Make sure we write our current data.
        self.driver.persist()

    @Accessory.run_at_interval(ONE_MINUTE)
    def check_missing(self):
        self.flag_unseen()
        self.remove_missing()

    def flag_unseen(self):
        """
        Any that we haven't seen in the past hour we want to show in HomeKit as "not connected".

        This should only be those that were done with QoS=0?
        """
        now = time.time()
        for acc in list(self.accessories.values()):
            if acc._last_seen and now - acc._last_seen > ONE_HOUR:
                # Set all characteristics we have ever known about to None.
                LOGGER.info("Look like {accessory_id} has no data for {interval} seconds".format(
                    accessory_id=acc.accessory_id,
                    interval=now - acc._last_seen,
                ))
                if acc._should_flag_unseen:
                    acc.no_response()

    def remove_missing(self):
        """
        Any that we have not seen in 28 days, we want to remove.
        """
        now = time.time()
        changed = False
        for acc in list(self.accessories.values()):
            if acc._last_seen and now - acc._last_seen > ONE_DAY * 28:
                self.accessories.pop(acc.aid)
                changed = True
        if changed:
            self.config_changed()

    def handle_mqtt_message(self, client, userdata, message):
        try:
            _prefix, accessory_id, service_type, characteristic = message.topic.split('/')
            index = 0
        except ValueError:
            _prefix, accessory_id, service_type, index, characteristic = message.topic.split('/')
            index = int(index)

        if service_type == 'AccessoryInformation':
            return

        if not message.payload:
            # Should we only do this if it's the only service?
            # Otherwise we should remove the service, maybe?
            LOGGER.info('REMOVE {accessory_id}: {service_type}.{characteristic}'.format(
                accessory_id=accessory_id,
                service_type=service_type,
                characteristic=characteristic,
            ))
            return self.remove_accessory(accessory_id)
        try:
            accessory = self.get_or_create_accessory(accessory_id, service_type, index)
            accessory._last_seen = time.time()
            value = message.payload.decode('ascii')
            LOGGER.debug('SET {accessory_id}: {service_type}[{index}].{characteristic} -> {value}'.format(
                accessory_id=accessory_id,
                service_type=service_type,
                index=index,
                characteristic=characteristic,
                value=value,
            ))
            # If we have an empty message, then perhaps we need to do nothing...?
            accessory.set_characteristic(service_type, index, characteristic, value)
        except Exception as exc:
            LOGGER.error('Exception handling message {}: {}'.format(exc.__class__.__name__, exc.args))

    def send_mqtt_message(self, accessory, service, characteristic, value):
        # We always send messages with QoS 2 - this means clients may choose how they want
        # to subscribe.
        # We also assume that data being pushed from HomeKit should "persist" (retain=True),
        # because the user has set a state. Devices that can be controlled out of band of
        # HomeKit should also set retain=True on their messages.
        if service == 'AccessoryInformation':
            LOGGER.info(
                'Received AccessoryInformation message: {accessory}: {service}.{characteristic} -> {value}'.format(
                    accessory=accessory,
                    service=service,
                    characteristic=characteristic,
                    value=value,
                )
            )
            return

        if characteristic.display_name == 'Identify':
            LOGGER.info('Identify: {accessory_id}'.format(accessory_id=accessory))
            return

        service_topic_name = service.display_name
        if len(accessory.get_services(service_topic_name)) > 1:
            service_topic_name += '/{}'.format(accessory.get_service_index(service))

        try:
            characteristic.set_value(value)
            topic = '{prefix}/{accessory_id}/{service}/{characteristic.display_name}'.format(
                prefix=self.prefix,
                accessory_id=accessory.accessory_id,
                service=service_topic_name,
                characteristic=characteristic,
            )
            LOGGER.debug(topic)

            if value in (True, False):
                value = int(value)

            self.client.publish(
                topic,
                str(value).encode(),
                qos=2,
                retain=True,
            )
        except Exception as exc:
            LOGGER.error('Exception sending message: {}'.format(exc.args))
