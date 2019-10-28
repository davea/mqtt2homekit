import json
from pathlib import Path
from pyhap.loader import get_loader

loader = get_loader()

path = Path(__file__).parent / 'contrib'


def merge(existing, new):
    for key, value in new.items():
        if key in existing:
            # Check the UUID matches. If not, throw an exception?
            assert existing[key]['UUID'] == value['UUID']
            for char in value.get('OptionalCharacteristics'):
                if char not in existing[key]['OptionalCharacteristics']:
                    print("Added char: {} to {}".format(char, key))
                    existing[key]['OptionalCharacteristics'].append(char)
            for char in value.get('RequiredCharacteristics'):
                if char not in existing[key]['RequiredCharacteristics']:
                    print("Added char: {} to {}".format(char, key))
                    existing[key]['RequiredCharacteristics'].append(char)
        else:
            existing[key] = value


for char_file in path.glob('characteristics.*.json'):
    characteristics = json.load(char_file.open())
    merge(loader.char_types, characteristics)


for serv_file in path.glob('services.*.json'):
    services = json.load(serv_file.open())
    merge(loader.serv_types, services)
