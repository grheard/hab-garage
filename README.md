# hab-garage
A raspberry pi instrument for automation in the garage.

## Hardware

### Features
- Implemented using an Rpi Zero W.
- Support for 2 garage doors.
  - Utilizes low voltage switch closure to detect door states.
- Support for monitoring radon abatement.
  - Utilizes a SM9514 differential pressure sensor.
- Support for temperature monitoring.
  - Utilizes a DS18B20 temperature sensor(s).

### Schematic

The schematic was created using [KiCAD](https://www.kicad.org/) and can be found in the schematic folder.


## Software

### Features
- Writen in python.
  - Requires python 3.6 or higher.
- Simple pluggable framework.
- Flexible configuration support (examples is the config directory)