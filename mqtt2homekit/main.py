from bridge import MQTTBridge


bridge = MQTTBridge('MQTT Bridge', persist_file='bridge.state')
bridge.start(mqtt_server='localhost', mqtt_port=1883, mqtt_timeout=60)
