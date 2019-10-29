from pyhap.accessory_driver import AccessoryDriver

from mqtt2homekit.accessory import clean_value, Accessory
from mqtt2homekit.loader import loader


def test_clean_value_On():
    char = loader.get_char('On')
    assert clean_value(char, '0') == 0
    assert clean_value(char, '1') == 1


def test_clean_value_Brightness():
    char = loader.get_char('Brightness')
    assert clean_value(char, '25') == 25
    assert clean_value(char, 100) == 100


def test_Accesssory_new_char():
    acc = Accessory(
        display_name='Lightbulb One',
        accessory_id='6f863a11-5d20-4034-b4e7-1200c8e6a183',
        services=['Lightbulb'],
        driver=AccessoryDriver()
    )
    acc.set_characteristic('Lightbulb', 'Brightness', '75')


def test_Accessory_no_response():
    acc = Accessory(
        display_name='Lightbulb One',
        accessory_id='4bf907bb-e52c-4b78-8efe-b7e0b050327c',
        services=['Lightbulb'],
        driver=AccessoryDriver()
    )
    acc.set_characteristic('Lightbulb', 'On', '1')
    acc.no_response()
