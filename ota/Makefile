
.PHONY: deploy/% deploy-ota

yaota8266.bin: config.h priv.key pub.key
	cd ../lib/yaota8266; make
	cp ../lib/yaota8266/yaota8266.bin $@

micropython:
	cd ../lib/micropython ; git submodule update --init
	cd ../lib/micropython/lib/axtls ; make

firmware/micropython-stock.bin:
	rm -rf ../lib/micropython/ports/esp8266/build/frozen_mpy/*
	cd ../lib/micropython/ports/esp8266/ ; make clean; make ota
	cp ../lib/micropython/ports/esp8266/build/firmware-ota.bin $@

firmware/%.bin: ../lib/micropython/ports/esp8266/modules/* ../lib/micropython-lib/umqtt-*/mqtt/*.py modules/base/* modules/%/*
	rm -rf build/$(*F)
	mkdir -p build/$(*F)/umqtt/
	cp ../lib/micropython/ports/esp8266/modules/* build/$(*F)/
	cp -R modules/base/* build/$(*F)/
	cp -R modules/$(*F)/* build/$(*F)/
	cp ../lib/micropython-lib/umqtt.simple/umqtt/simple.py build/$(*F)/umqtt/simple.py
	cp ../lib/micropython-lib/umqtt.robust/umqtt/robust.py build/$(*F)/umqtt/robust.py
	cd ../lib/micropython/ports/esp8266/ ; make ota FROZEN_MPY_DIR=$(shell pwd)/build/$(*F)
	cp ../lib/micropython/ports/esp8266/build/firmware-ota.bin $@


deploy-ota: yaota8266.bin
	echo "Writing OTA firmware to esp8266"
	$(MAKE) -f Makefile.deploy START=0x00000 FILE=yaota8266.bin

deploy/sonoff: firmware/sonoff.bin
	echo "Writing sonoff firmware to esp8266"
	$(MAKE) -f Makefile.deploy FILE=$< FLASH_MODE=dout

deploy/%: firmware/%.bin
	echo "Writing %(@F) firmware to esp8266"
	$(MAKE) -f Makefile.deploy FILE=$<
