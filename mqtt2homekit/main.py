from bridge import MQTTBridge
from client import MQTTClient


bridge = MQTTBridge('MQTT Bridge', persist_file='bridge.state')
bridge.start()

client = MQTTClient(bridge=bridge)
client.connect('10.0.1.8', 1883, 60)
client.loop_forever()
