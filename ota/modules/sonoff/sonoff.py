from machine import Pin, Signal, unique_id
from umqtt.robust import MQTTClient
from ubinascii import hexlify

DEVICE_ID = b'sonoff_' + hexlify(unique_id())

MQTT_TOPIC = b'HomeKit/' + DEVICE_ID + '/Switch/On'

_relay = None
_led = None
button = Signal(Pin(0, Pin.IN))


def relay(value):
    global _relay
    global _led
    if _relay is None:
        _relay = Signal(Pin(12, mode=Pin.OUT, value=value))
        _led = Signal(Pin(13, mode=Pin.OUT, value=not value), invert=True)
    else:
        _relay(value)
        _led(value)


def mqtt_update(topic, msg):
    print((topic, msg))
    if topic == MQTT_TOPIC:
        if msg == b'1':
            relay(True)
        elif msg == b'0':
            relay(False)


def main():
    client = MQTTClient(DEVICE_ID, server='mqtt.lan')
    client.set_callback(mqtt_update)
    client.connect()
    client.subscribe(MQTT_TOPIC)

    try:
        while 1:
            client.wait_msg()
    finally:
        client.disconnect()
        # machine.reset()
