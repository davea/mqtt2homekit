from machine import Pin
import dht

sensor = dht.DHT11(Pin(4))


def read():
    while True:
        try:
            sensor.measure()
        except OSError:
            continue
        else:
            return {
                'temperature': sensor.temperature(),
                'humidity': sensor.humidity()
            }


def send(client):
    result = read()
    client.publish(
        'HomeKit/{}/TemperatureSensor/CurrentTemperature'.format(client.client_id.decode()),
        str(result['temperature']),
        retain=True,
    )
    client.publish(
        'HomeKit/{}/HumiditySensor/CurrentRelativeHumidity'.format(client.client_id.decode()),
        str(result['humidity']),
        retain=True,
    )
