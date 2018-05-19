from ubinascii import hexlify
from machine import Pin
import time
import ds18x20
import onewire

bus = onewire.OneWire(Pin(2))
bus.scan()

ds = ds18x20.DS18X20(bus)


def read_temperatures():
    roms = ds.scan()
    ds.convert_temp()
    time.sleep_ms(750)
    for rom in roms:
        yield (hexlify(rom), ds.read_temp(rom))


def send(client):
    for sensor_id, temperature in read_temperatures():
        client.publish(
            'HomeKit/{}/TemperatureSensor/CurrentTemperature'. format(sensor_id.decode()),
            str(temperature),
            retain=True,
        )
