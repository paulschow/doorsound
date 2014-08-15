# Doorsound #
# README #

### What is this repository for? ###

* Doorsound
* Uses bluetooth to tell when someone gets home, then plays a sound when they walk in the door

### How do I get set up? ###

* Get Raspberry Pi
* Clone files
* Pair bluetooth devices
* Use a sqlite db editor to change the macs.db
* Put sounds or song clips in /sounds
* Add their MAC addresses into macs.db with a sound
* Attach reed switch to GPIO pin 14 (see schematic)
* Optinally attach LED(s) to pin 15
* Run bluepinger.py


### Is there a wifi version? ###

* Yes
* [https://github.com/paulschow/wifidoorsound](https://github.com/paulschow/wifidoorsound)
