import logging

from bridge import MQTTBridge

logging.basicConfig(level=logging.DEBUG)


def main():
    bridge = MQTTBridge('MQTT Bridge', persist_file='bridge.state')
    bridge.start('mqtt://mqtt.local:1883')


if __name__ == '__main__':
    main()
