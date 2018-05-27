# Connect to WiFi.
from config import config
import mqtt
import wifi
import time
import esp
import update
import machine

sensor = None  # To stop Flake8 errors later

# Try to connect to wifi: if we can't (or we aren't configured), then we want
# to start up our access point radio, and start broadcasting that for config.
wifi.connect(**config.WIFI)
if not wifi.connected():
    wifi.start_ap()
    config.setup()

try:
    client = mqtt.Client(**config.MQTT)
    client.connect()
except mqtt.MQTTException:
    config.setup()

try:
    exec('import sensors.{} as sensor'.format(config.SENSOR))
except ImportError:
    config.setup()

# See if we need to apply any updates to the system.
client.set_callback(update.apply_update)
client.subscribe('HomeKit/device/update')
if client.check_msg():
    # Do we need to do anything to make sure the callback fires before we reset?
    machine.reset()

if getattr(sensor, 'ONE_SHOT', True):
    # If not, then we need to read the sensor data, and send it to the MQTT broker.
    sensor.send(client)
    print('sleeping')
    time.sleep(5)
    print('deep-sleeping')
    esp.deepsleep(config.DEEP_SLEEP)
    time.sleep(5)
else:
    sensor.start(client)