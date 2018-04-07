from pyhap import accessory, loader
from pyhap.accessory import Category

CATEGORIES = {
    'GarageDoorOpener': Category.GARAGE_DOOR_OPENER,
    'TemperatureSensor': Category.SENSOR,
    'HumiditySensor': Category.SENSOR
}


COERCE = {
    'int': int,
    'float': float,
    'uint8': int,
    'uint16': int,
    'uint32': int,
    'uint64': int,
    'bool': bool
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
        # TODO: Automatically set up a callback for each characteristic.

    def set_characteristic(self, characteristic_name, value):
        characteristic = self.service.get_characteristic(characteristic_name)
        value = clean_value(characteristic, value)
        characteristic.set_value(value)
