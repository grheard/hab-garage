from .logger import logger
from .mqtt import Mqtt, mqtt

try:
    from w1thermsensor import W1ThermSensor
except Exception as e:
    logger.warning('Cannot load w1thermsensor module')

from threading import Thread, Event
import sys


class W1Therm(Thread):

    def __init__(self,config):
        self.__parse_config(config)

        self.__stop = Event()

        super().__init__(target=self.__run)


    def __parse_config(self,config):
        self.__sensor_id = None
        self.__offset = None
        self.__topic = None
        self.__rate = None

        if config is None or type(config) is not dict:
            raise TypeError('passed config is not of type dict')

        if not 'w1therm' in config:
            raise ValueError('"w1therm" object missing from the confiugration')

        if not 'topic' in config['w1therm']:
            raise ValueError('"topic" missing from the configuration')
        self.__topic = config['w1therm']['topic']

        if not 'rate' in config['w1therm']:
            raise ValueError('"rate" missing from the configuration')
        self.__rate = config['w1therm']['rate']

        if not 'sensor' in config['w1therm']:
            raise ValueError('"sensor" object missing from the configuration')

        if not 'id' in config['w1therm']['sensor']:
            raise ValueError('"id" missing from the "sensor" object in the configuration')
        self.__sensor_id = config['w1therm']['sensor']['id']

        if not 'offset' in config['w1therm']['sensor']:
            raise ValueError('"offset" missing from the "sensor" object in the configuration')
        self.__offset = config['w1therm']['sensor']['offset']


    def __run(self):
        logger.info(f'W1Therm started for topic \'{self.__topic}\' for sensor id {self.__sensor_id}')

        if not 'w1thermsensor' in sys.modules:
            logger.warning('w1thermsensor module did not load, exiting')
            return

        sensor = None
        for _sensor in W1ThermSensor.get_available_sensors():
            if _sensor.id == self.__sensor_id:
                sensor = _sensor
                break
        
        if sensor is None:
            logger.warning(f'Sensor {self.__sensor_id} is not detected, exiting')
            return

        while not self.__stop.is_set():
            temp = """{0:5.1f}""".format(sensor.get_temperature(unit=W1ThermSensor.DEGREES_F) + self.__offset)
            logger.info(f'{self.__sensor_id} {self.__topic} {temp}')
            Mqtt.instance().publish(self.__topic,temp)
            for _ in range(self.__rate):
                if self.__stop.wait(1):
                    break


    def stop(self):
        self.__stop.set()
        self.join()
