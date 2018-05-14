# Connect to WiFi.
from config import config
import mqtt
import sensor
import wifi
import time
import esp
import update
import machine

wifi.connect(**config.WIFI)

if not wifi.connected():
    config.setup()

try:
    client = mqtt.Client(**config.MQTT)
    client.connect()
except mqtt.MQTTException:
    config.setup()

# See if we need to apply any updates to the system.
client.set_callback(update.apply_update)
client.subscribe('updates/{}'.format(sensor.SENSOR_ID))
if client.check_msg():
    machine.reset()

# If not, then we need to read the sensor data, and send it to the MQTT broker.
sensor.send(client)
print('sleeping')
time.sleep(5)
print('deep-sleeping')
esp.deepsleep(config.DEEP_SLEEP)
time.sleep(5)
