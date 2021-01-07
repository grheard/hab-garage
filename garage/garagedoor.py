from .logger import logger
from .mqtt import Mqtt, mqtt
from .gpio import Gpio, gpio

from threading import Thread, Event, Timer
import time


door_state_str = ['unknown','closing','closed','opening','open','stopped']


DOOR_STATE_UNKNOWN = 0
DOOR_STATE_CLOSING = 1
DOOR_STATE_CLOSED = 2
DOOR_STATE_OPENING = 3
DOOR_STATE_OPEN = 4
DOOR_STATE_STOPPED = 5


class GarageDoor(Thread):

    def __init__(self,config):
        self.__parse_config(config)

        self.__stop = Event()

        self.__act_timer = None

        super().__init__(target=self.__run)


    def __parse_config(self,config):
        self.__top = None
        self.__bot = None
        self.__act = None
        self.__topic = None
        self.__rate = None

        if config is None or type(config) is not dict:
            raise TypeError('passed config is not of type dict')

        if not 'garagedoor' in config:
            raise ValueError('"garagedoor" object missing from the confiugration')

        if not 'topic' in config['garagedoor']:
            raise ValueError('"topic" missing from the configuration')
        self.__topic = config['garagedoor']['topic']
        self.__act_topic = self.__topic + '/actuate'

        if not 'rate' in config['garagedoor']:
            raise ValueError('"rate" missing from the configuration')
        self.__rate = config['garagedoor']['rate']

        if not 'gpio' in config['garagedoor']:
            raise ValueError('"gpio" object missing from the configuration')

        if not 'top' in config['garagedoor']['gpio']:
            raise ValueError('"top" missing from the "gpio" object in the configuration')
        self.__top = config['garagedoor']['gpio']['top']

        if not 'bot' in config['garagedoor']['gpio']:
            raise ValueError('"bot" missing from the "gpio" object in the configuration')
        self.__bot = config['garagedoor']['gpio']['bot']

        if not 'act' in config['garagedoor']['gpio']:
            raise ValueError('"act" missing from the "gpio" object in the configuration')
        self.__act = config['garagedoor']['gpio']['act']


    def __actuator_on(self):
        Gpio.instance().write(self.__act,1)
        self.__act_timer = Timer(1,self.__actuator_off)
        self.__act_timer.start()


    def __actuator_off(self):
        Gpio.instance().write(self.__act,0)
        self.__act_timer = None


    def __subscribe(self):
        Mqtt.instance().subscribe(self.__act_topic,qos=2)
        Mqtt.instance().message_callback_add(self.__act_topic,self.__on_message)


    def __on_message(self,client,userdata,message):
        if self.__act_timer is not None:
            logger.debug('Received actuation while actuating')
            return

        self.__actuator_on()


    def __on_connect(self,client, userdata, flags, rc):
        if rc == mqtt.client.CONNACK_ACCEPTED:
            self.__subscribe()


    def __run(self):
        logger.info(f'garagedoor started for topic \'{self.__topic}\'')

        Gpio.instance().set_mode(self.__top,gpio.INPUT)
        Gpio.instance().set_mode(self.__bot,gpio.INPUT)
        Gpio.instance().write(self.__act,0)
        Gpio.instance().set_mode(self.__act,gpio.OUTPUT)

        Mqtt.instance().register_on_connect(self.__on_connect)
        
        if Mqtt.instance().is_connected():
            self.__subscribe()

        doorTime = 0
        reportTime = time.monotonic()
        doorState = DOOR_STATE_UNKNOWN
        while not self.__stop.is_set():

            gpioTop = Gpio.instance().read(self.__top)
            gpioBottom = Gpio.instance().read(self.__bot)

            if not gpioTop and gpioBottom:
                newDoorState = DOOR_STATE_OPEN
            
            elif gpioTop and not gpioBottom:
                newDoorState = DOOR_STATE_CLOSED
            
            elif gpioTop and gpioBottom:
                if doorState == DOOR_STATE_OPEN:
                    newDoorState = DOOR_STATE_CLOSING
                    doorTime = time.monotonic()
            
                elif doorState == DOOR_STATE_CLOSED:
                    newDoorState = DOOR_STATE_OPENING
                    doorTime = time.monotonic()
            
                elif time.monotonic() - doorTime > 30.0:
                    newDoorState = DOOR_STATE_STOPPED

            if not Mqtt.instance().is_connected():
                doorState = DOOR_STATE_UNKNOWN
            elif doorState != newDoorState or time.monotonic() - reportTime > self.__rate:
                reportTime = time.monotonic()
                doorState = newDoorState
                logger.info(f'{self.__topic} {door_state_str[doorState]}')
                Mqtt.instance().publish(self.__topic,door_state_str[doorState],qos=1)

            self.__stop.wait(0.5)


    def stop(self):
        self.__stop.set()
        self.join()
