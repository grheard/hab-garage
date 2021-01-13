import argparse
import json
import os
import signal
import sys
import time
import threading

from .logger import logger, parse_logger_config


def __parse_command_line_arguments() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs=1, default='', help='Configuration json in string or file form')
    args = parser.parse_args()

    if args.config:
        config = __parse_config(args.config[0])
        if config is None:
            print('--config could not be reconciled. See log for details.')
            parser.print_help()
            sys.exit(1)
        return config


def __parse_config(input) -> dict:
    try:
        # Try to parse a json object directly
        config = json.loads(input)
        logger.info("configuration successfully parsed from the command line.")
        return config
    except json.JSONDecodeError:
        logger.info(f"'{input}' is not JSON, it will be attempted as a file.")

    # Try loading it as a file
    if not os.path.isfile(input):
        logger.error(f"'{input}' is neither a JSON object or a file.")
        return None

    try:
        file = open(input)
    except OSError:
        logger.error(f"'{input}' cannot be opened.")
        return None

    try:
        config = json.load(file)
        logger.info(f"'{input}' successfully parsed.")
        return config
    except json.JSONDecodeError:
        logger.error(f"'{input}' does not contain a valid JSON object.")
        return None


config = __parse_command_line_arguments()

# Parse the logger configuration ahead of any other import
# in case a module also modifies the logger
parse_logger_config(config)


from .mqtt import Mqtt
from .gpio import Gpio
from .sm9514 import SM9514
from .garagedoor import GarageDoor
from .w1therm import W1Therm


class Main():
    def __init__(self):
        self.__stop = threading.Event()

    def start(self):
        Mqtt(config)
        Gpio(config)

        sensors = self.__parse_sensor_config(config)
        for sensor in sensors:
            sensor["instance"].start()

        Mqtt.instance().connect()

        while not self.__stop.wait(1):
            # Check to ensure sensors stay alive.
            for sensor in sensors:
                if not sensor["instance"].is_alive():
                    logger.warning(f'Sensor "{sensor}" has failed, recreating.')
                    self.__recreate_sensor_instance(sensor)

        for sensor in sensors:
            sensor["instance"].stop()
            del sensor["instance"]

        Mqtt.instance().disconnect()


    def stop(self):
        self.__stop.set()


    def __parse_sensor_config(self,config) -> dict:
        _sensors = []

        if config is None or type(config) is not dict:
            raise TypeError('passed config is not a dict')

        if not "sensors" in config:
            raise ValueError('"sensors" missing from config')

        if type(config['sensors']) is not list:
            raise TypeError('"sensors" is not a list')

        for item in config['sensors']:
            if len(item) != 1:
                raise ValueError('Only 1 sensor must be defined in each "sensors" object')

            if type(item) is not dict:
                raise TypeError('Invalid (not a dict) type found in "sensors"')

            for key, value in item.items():
                if type(key) is not str:
                    raise TypeError('Invalid (not a str) type found as a key in "sensors"')
                if type(value) is not dict:
                    raise TypeError(f'Invalid (not a dict) type found as a value for "{key}" in "sensors"')

                instance = self.__create_sensor_instance(item)
                
                if instance is None:
                    logger.warning(f'Unknown sensor type "{key}" found in "sensors"')
                else:
                    _item = item.copy()
                    _item["instance"] = instance
                    _sensors.append(_item)

        return _sensors


    def __create_sensor_instance(self,config) -> object:
        instance = None

        if "sm9514" in config:
            instance = SM9514(config)
        elif "garagedoor" in config:
            instance = GarageDoor(config)
        elif "w1therm" in config:
            instance = W1Therm(config)

        return instance


    def __recreate_sensor_instance(self,item):
        del item["instance"]
        item["instance"] = None

        instance = self.__create_sensor_instance(item)
        if instance is None:
            logger.error(f'Could not recreate sensor {item}')
        else:
            item["instance"] = instance
            instance.start()


def __signal_handler(signal, frame):
    try:
        logger.info(f"Caught signal {signal}")
        gmain.stop()
    except:
        sys.exit(0)


def main():
    global gmain

    logger.info("Setting up.")

    signal.signal(signal.SIGINT, __signal_handler)

    gmain = Main()

    logger.info("Start.")

    gmain.start()

    logger.info("End.")
