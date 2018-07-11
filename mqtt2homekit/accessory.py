from pyhap import accessory, const
from pyhap.loader import get_serv_loader


CATEGORIES = {
    'AirPurifier': const.CATEGORY_OTHER,
    'AirQualitySensor': const.CATEGORY_SENSOR,
    'BatteryService': const.CATEGORY_OTHER,
    'CarbonDioxideSensor': const.CATEGORY_SENSOR,
    'CarbonMonoxideSensor': const.CATEGORY_SENSOR,
    'ContactSensor': const.CATEGORY_SENSOR,
    'Door': const.CATEGORY_DOOR,
    'Doorbell': const.CATEGORY_OTHER,
    'Fan': const.CATEGORY_FAN,
    'Fanv2': const.CATEGORY_FAN,
    'Faucet': const.CATEGORY_OTHER,
    'FilterMaintenance': const.CATEGORY_OTHER,
    'GarageDoorOpener': const.CATEGORY_GARAGE_DOOR_OPENER,
    'HeaterCooler': const.CATEGORY_THERMOSTAT,
    'HumidifierDehumidifier': const.CATEGORY_THERMOSTAT,
    'HumiditySensor': const.CATEGORY_SENSOR,
    'IrrigationSystem': const.CATEGORY_OTHER,
    'LeakSensor': const.CATEGORY_SENSOR,
    'LightSensor': const.CATEGORY_SENSOR,
    'Lightbulb': const.CATEGORY_LIGHTBULB,
    'LockManagement': const.CATEGORY_DOOR_LOCK,
    'LockMechanism': const.CATEGORY_DOOR_LOCK,
    'Microphone': const.CATEGORY_OTHER,
    'MotionSensor': const.CATEGORY_SENSOR,
    'OccupancySensor': const.CATEGORY_SENSOR,
    'Outlet': const.CATEGORY_OUTLET,
    'SecuritySystem': const.CATEGORY_ALARM_SYSTEM,
    'ServiceLabel': const.CATEGORY_OTHER,
    'Slat': const.CATEGORY_WINDOW_COVERING,
    'SmokeSensor': const.CATEGORY_SENSOR,
    'Speaker': const.CATEGORY_OTHER,
    'StatelessProgrammableSwitch': const.CATEGORY_PROGRAMMABLE_SWITCH,
    'Switch': const.CATEGORY_SWITCH,
    'TemperatureSensor': const.CATEGORY_SENSOR,
    'Thermostat': const.CATEGORY_THERMOSTAT,
    'Valve': const.CATEGORY_OTHER,
    'Window': const.CATEGORY_WINDOW,
    'WindowCovering': const.CATEGORY_WINDOW_COVERING,
}

# These items should trigger a Not Responding state if we haven't seen them
# recently - that is, they should be pushing data to us frequently.
FLAG_UNSEEN = (
    'AirQualitySensor',
    'CarbonDioxideSensor',
    'CarbonMonoxideSensor',
    'HumiditySensor',
    'LightSensor',  # ? - Or is this boolean?
    'TemperatureSensor',
)

COERCE = {
    'int': int,
    'float': float,
    'uint8': int,
    'uint16': int,
    'uint32': int,
    'uint64': int,
    'bool': int
}

loader = get_serv_loader()


def clean_value(characteristic, value):
    if characteristic.properties['Format'] in COERCE:
        return COERCE[characteristic.properties['Format']](value)
    return value


class Accessory(accessory.AsyncAccessory):
    def __init__(self, *args, **kwargs):
        services = kwargs.pop('services')
        self.accessory_id = kwargs.pop('accessory_id')
        self.category = CATEGORIES.get(services[0], const.CATEGORY_OTHER)
        super().__init__(*args, **kwargs)
        self.set_information_service(
            Name=self.display_name,
            SerialNumber=self.accessory_id,
            Manufacturer='Matthew Schinckel',
            Model='MQTT Bridged {}'.format(services[0]),
        )
        self.add_service(*(loader.get_service(service) for service in services))
        self._should_flag_unseen = services[0] in FLAG_UNSEEN
        self._last_seen = None

    def set_information_service(self, **info):
        info_service = loader.get_service('AccessoryInformation')
        for key in ['Name', 'Manufacturer', 'Model', 'SerialNumber']:
            info_service.get_characteristic(key).set_value(info.get(key, ''))
        self.add_service(info_service)

    def set_characteristic(self, service_type, characteristic_name, value):
        service = self.get_service(service_type)
        characteristic = service.get_characteristic(characteristic_name)
        value = clean_value(characteristic, value)
        characteristic.set_value(value)
        characteristic.notify()

    def _set_services(self):
        pass

    def no_response(self):
        for service in self.services[1:]:
            for characteristic in service.characteristics:
                characteristic.value = None
