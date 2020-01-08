import logging

import click

from mqtt2homekit.bridge import MQTTBridge

logging.basicConfig(level=logging.DEBUG)


@click.command()
@click.option('--persist', default='bridge.state', help='Persist to file')
@click.option('--broker', default='mqtt://mqtt.lan:1883', help='URL to use for MQTT broker')
@click.option('--name', default='MQTT Bridge', help='Name of MQTT Bridge')
@click.option('--prefix', default='HomeKit', help='MQTT Topic Prefix')
def main(name, persist, broker, prefix):
    MQTTBridge(name, persist_file=persist, mqtt_server=broker, prefix=prefix).driver.start()


if __name__ == '__main__':
    main()
