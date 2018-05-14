import ujson
try:
    import machine
    import ubinascii
    DEVICE_ID = b'esp8266_' + ubinascii.hexlify(machine.unique_id())
except ImportError:
    import sys
    DEVICE_ID = sys.platform + '_whatever'

DEFAULT_SLEEP_TIME = 60
SLEEP_FACTOR = 1000000
MAX_SLEEP_TIME = 4000
CONFIG_FILE = 'config.json'
DEFAULT_MQTT_SERVER = 'mqtt.lan'

try:
    _config = ujson.load(open(CONFIG_FILE))
except Exception:
    _config = {}


class DictWrapper(object):
    def __init__(self, key, default):
        self.key = key
        self.default = default
        if key not in _config:
            _config[key] = {}

    def __getitem__(self, key):
        if key in _config[self.key]:
            return _config[self.key][key]
        return self.default[key]

    def __setitem__(self, key, value):
        _config[self.key][key] = value

    def keys(self):
        keys = list(_config.get(self.key, {}).keys())
        default_keys = list(self.default.keys())
        return list(set(keys + default_keys))

    def update(self, *args, **kwargs):
        _config[self.key].update(*args, **kwargs)

    @property
    def _value(self):
        return dict(**self)

    def __repr__(self):
        return repr(self._value)


class Config(object):
    @property
    def MQTT(self):
        return DictWrapper('mqtt', {'client_id': DEVICE_ID, 'server': DEFAULT_MQTT_SERVER})

    @MQTT.setter
    def MQTT(self, value):
        _config['mqtt'] = value

    @property
    def WIFI(self):
        return DictWrapper('wifi', {})

    @WIFI.setter
    def WIFI(self, value):
        _config['wifi'] = value

    @property
    def DEEP_SLEEP(self):
        return _config.get('deep_sleep', DEFAULT_SLEEP_TIME) * SLEEP_FACTOR

    @DEEP_SLEEP.setter
    def DEEP_SLEEP(self, value):
        """
        This value must be seconds.
        """
        _config['deep_sleep'] = min(max(1, value), MAX_SLEEP_TIME)

    def __repr__(self):
        return {
            'mqtt': self.MQTT,
            'wifi': self.WIFI,
            'deep_sleep': self.DEEP_SLEEP / SLEEP_FACTOR
        }

    def save(self):
        open(CONFIG_FILE, 'w').write(ujson.dumps(_config))

    def setup(self):
        import wifi
        import machine
        # Start our AP.
        wifi.start_ap()
        # Serve HTTP.
        # Save config.
        self.save()
        # Reboot.
        machine.reset()

config = Config()  # NOQA
