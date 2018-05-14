import network
import time


station = network.WLAN(network.STA_IF)
access_point = network.WLAN(network.AP_IF)


def connect(ssid=None, psk=None, wait=30):
    access_point.active(False)
    station.active(True)

    if not station.isconnected():
        station.connect(ssid, psk)
        for i in range(wait):
            if station.isconnected():
                break
            print('waiting for network')
            time.sleep(1)

    print('network config:', station.ifconfig())


def start_ap():
    access_point.active(True)
    print('starting access point')
