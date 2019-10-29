import logging

from .bridge import MQTTBridge

logging.basicConfig(level=logging.DEBUG)


def main():
    MQTTBridge('MQTT Bridge', persist_file='bridge.state', mqtt_server='mqtt://mqtt.lan:1883').driver.start()


if __name__ == '__main__':
    main()
