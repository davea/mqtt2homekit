import logging

from bridge import MQTTBridge

logging.basicConfig(level=logging.INFO)


def main():
    MQTTBridge('MQTT Bridge', persist_file='bridge.state', mqtt_server='mqtt://mqtt.local:1883').start()


if __name__ == '__main__':
    main()
