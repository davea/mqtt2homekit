import logging

from bridge import MQTTBridge

logging.basicConfig(level=logging.DEBUG)


def main():
    bridge = MQTTBridge('MQTT Bridge', persist_file='bridge.state')
    bridge.start(mqtt_server='localhost', mqtt_port=1883, mqtt_timeout=60)


if __name__ == '__main__':
    main()
