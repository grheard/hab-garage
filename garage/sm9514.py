from .logger import logger
from .mqtt import Mqtt, mqtt
from .gpio import Gpio, gpio

from threading import Thread, Event
import time
import binascii


SM_OUTPUT_MAX = 14745
SM_OUTPUT_MIN = 1638

SM_STATUS_OK = 0
SM_STATUS_CMD = 1
SM_STATUS_STALE = 2
SM_STATUS_ERR = 3

SM_STATUS_MASK = 0xC0


class SM9514(Thread):

    def __init__(self,config):
        self.__parse_config(config)

        self.__stop = Event()

        super().__init__(target=self.__run)


    def __parse_config(self,config):
        self.__pmax = None
        self.__pmin = None
        self.__bus = None
        self.__addr = None
        self.__topic = None
        self.__rate = None

        if config is None or type(config) is not dict:
            raise TypeError('passed config is not of type dict')

        if not 'sm9514' in config:
            raise ValueError('"sm9514" object missing from the confiugration')

        if not 'topic' in config['sm9514']:
            raise ValueError('"topic" missing from the configuration')
        self.__topic = config['sm9514']['topic']

        if not 'rate' in config['sm9514']:
            raise ValueError('"rate" missing from the configuration')
        self.__rate = config['sm9514']['rate']

        if not 'press' in config['sm9514']:
            raise ValueError('"press" object missing from the configuration')

        if not 'max' in config['sm9514']['press']:
            raise ValueError('"max" missing from the "press" object in the configuration')
        self.__pmax = config['sm9514']['press']['max']

        if not 'min' in config['sm9514']['press']:
            raise ValueError('"min" missing from the "press" object in the configuration')
        self.__pmin = config['sm9514']['press']['min']

        if not 'i2c' in config['sm9514']:
            raise ValueError('"i2c" object missing from the configuration')

        if not 'bus' in config['sm9514']['i2c']:
            raise ValueError('"bus" missing from the "i2c" object in the configuration')
        self.__bus = config['sm9514']['i2c']['bus']

        if not 'addr' in config['sm9514']['i2c']:
            raise ValueError('"addr" missing from the "i2c" object in the configuration')
        self.__addr = config['sm9514']['i2c']['addr']


    def __run(self):
        logger.info(f'SM9514 started for topic \'{self.__topic}\' on i2c bus {self.__bus} addr {self.__addr}')

        i2ch = Gpio.instance().i2c_open(self.__bus,self.__addr)

        while not self.__stop.is_set():
            valid, counts = self.__sm_read_pressure_counts(gpio,i2ch)
            logger.debug(f'sm_read_pressure_counts -> {valid} {counts}')

            if valid:
                pressure = float("""{0:2.3f}""".format(self.__sm_calculate_pressure(self.__pmax,self.__pmin,counts)))
                logger.info(f'{self.__topic}: {pressure}')
                Mqtt.instance().publish(self.__topic,pressure)
                for _ in range(self.__rate):
                    if self.__stop.wait(1):
                        break

        Gpio.instance().i2c_close(i2ch)


    def __sm_calculate_pressure(self,pmax,pmin,counts) -> float:
        return (((counts - SM_OUTPUT_MIN) * (pmax - pmin)) / (SM_OUTPUT_MAX - SM_OUTPUT_MIN)) + pmin


    def __sm_check_status(self,status) -> int:
        return (status & SM_STATUS_MASK) >> 6


    def __sm_read_pressure_counts(self,gpio,i2ch) -> ():
        read_tries = 3
        while read_tries > 0:
            nbr, data = Gpio.instance().i2c_read_device(i2ch,4)
            logger.debug(f'i2c_read_device -> {binascii.hexlify(data)}')

            if nbr != 4:
                logger.warning('Failed to read sensor.')
                return (False,0)

            status = self.__sm_check_status(data[0])
            logger.debug(f'sm_check_status -> {status}')

            if status == 3:
                logger.warning('Device in error.')
                return (False,0)

            if status == 1:
                logger.warning('Device in command mode.')
                return (False,0)

            if status == 0:
                data[0] &= ~SM_STATUS_MASK
                counts = int.from_bytes(data[0:2],byteorder='big')
                if counts >= SM_OUTPUT_MIN and counts <= SM_OUTPUT_MAX:
                    return (True,counts)

                logger.debug(f'Counts out of range: {counts}')
                break

            if status == 2:
                logger.debug('Conversion in progress.')

            read_tries -= 1
            time.sleep(0.1)

        logger.error('Sensor did not return an answer.')
        return (False,0)


    def stop(self):
        self.__stop.set()
        self.join()
