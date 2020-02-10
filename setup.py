from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mqtt2homekit',
    description='Two way bridge between HomeKit and MQTT',
    long_description=long_description,
    url='https://hg.sr.ht/~schinckel/mqtt2homekit',
    keywords='mqtt',
    packages=find_packages(),
    install_requires=['paho-mqtt', 'HAP-python[QRCode]'],
)
