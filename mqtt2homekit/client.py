import logging

import paho.mqtt.client as mqtt


LOGGER = logging.getLogger(__file__)
logging.basicConfig()
LOGGER.setLevel(logging.DEBUG)


class MQTTClient(mqtt.Client):
    def __init__(self, *args, **kwargs):
        self.bridge = kwargs.pop('bridge')
        super().__init__(*args, **kwargs)
        self.message_callback_add('HomeKit/+/+/+', self.on_accessory_message)

    def on_connect(self, client, userdata, flags, rc):
        LOGGER.debug('Connected with result code: {}'.format(rc))
        client.subscribe('HomeKit/#')

    def on_accessory_message(self, client, userdata, message):
        _homkeit, accessory_id, service_type, characteristic = message.topic.split('/')
        LOGGER.debug('Accessory {accessory}:{service}:{characteristic}:{value}'.format(
            accessory=accessory_id,
            service=service_type,
            characteristic=characteristic,
            value=message.payload.decode('ascii')
        ))
        self.bridge.handle_message(accessory_id, service_type, characteristic, message.payload.decode('ascii'))
