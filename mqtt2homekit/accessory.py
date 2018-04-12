from pyhap import accessory
from pyhap.loader import get_serv_loader
from pyhap.accessory import Category

CATEGORIES = {
    'AirPurifier': Category.OTHER,
    'AirQualitySensor': Category.SENSOR,
    'BatteryService': Category.OTHER,
    'CarbonDioxideSensor': Category.SENSOR,
    'CarbonMonoxideSensor': Category.SENSOR,
    'ContactSensor': Category.SENSOR,
    'Door': Category.DOOR,
    'Doorbell': Category.OTHER,
    'Fan': Category.FAN,
    'Fanv2': Category.FAN,
    'Faucet': Category.OTHER,
    'FilterMaintenance': Category.OTHER,
    'GarageDoorOpener': Category.GARAGE_DOOR_OPENER,
    'HeaterCooler': Category.THERMOSTAT,
    'HumidifierDehumidifier': Category.THERMOSTAT,
    'HumiditySensor': Category.SENSOR,
    'IrrigationSystem': Category.OTHER,
    'LeakSensor': Category.SENSOR,
    'LightSensor': Category.SENSOR,
    'Lightbulb': Category.LIGHTBULB,
    'LockManagement': Category.DOOR_LOCK,
    'LockMechanism': Category.DOOR_LOCK,
    'Microphone': Category.OTHER,
    'MotionSensor': Category.SENSOR,
    'OccupancySensor': Category.SENSOR,
    'Outlet': Category.OUTLET,
    'SecuritySystem': Category.ALARM_SYSTEM,
    'ServiceLabel': Category.OTHER,
    'Slat': Category.WINDOW_COVERING,
    'SmokeSensor': Category.SENSOR,
    'Speaker': Category.OTHER,
    'StatelessProgrammableSwitch': Category.PROGRAMMABLE_SWITCH,
    'Switch': Category.SWITCH,
    'TemperatureSensor': Category.SENSOR,
    'Thermostat': Category.THERMOSTAT,
    'Valve': Category.OTHER,
    'Window': Category.WINDOW,
    'WindowCovering': Category.WINDOW_COVERING,
}


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


class Accessory(accessory.Accessory):
    def __init__(self, *args, **kwargs):
        services = kwargs.pop('services')
        accessory_id = kwargs.pop('accessory_id')
        self.category = CATEGORIES.get(services[0], Category.OTHER)
        super().__init__(*args, **kwargs)
        self.set_information_service(
            Name=self.display_name,
            SerialNumber=accessory_id,
            Manufacturer='Matthew Schinckel',
            Model='MQTT Bridged {}'.format(services[0]),
        )
        self.add_service(*(loader.get(service) for service in services))

    def set_information_service(self, **info):
        info_service = loader.get('AccessoryInformation')
        for key in ['Name', 'Manufacturer', 'Model', 'SerialNumber']:
            info_service.get_characteristic(key).set_value(info.get(key, ''))
        self.add_service(info_service)

    def set_characteristic(self, service_type, characteristic_name, value):
        service = self.get_service(service_type)
        characteristic = service.get_characteristic(characteristic_name)
        value = clean_value(characteristic, value)
        characteristic.set_value(value)

    def _set_services(self):
        pass
