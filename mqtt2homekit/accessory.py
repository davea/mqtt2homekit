from pyhap import accessory, loader
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


def clean_value(characteristic, value):
    if characteristic.properties['Format'] in COERCE:
        return COERCE[characteristic.properties['Format']](value)
    return value


class Accessory(accessory.Accessory):
    def __init__(self, *args, **kwargs):
        service = kwargs.pop('service')
        super().__init__(*args, **kwargs)
        self.service = loader.get_serv_loader().get(service)
        self.add_service(self.service)
        self.category = CATEGORIES.get(service, Category.OTHER)

    def set_characteristic(self, characteristic_name, value):
        characteristic = self.service.get_characteristic(characteristic_name)
        value = clean_value(characteristic, value)
        characteristic.set_value(value)
