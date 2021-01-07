import ssl
from threading import Lock
import paho
from paho.mqtt.client import Client
from .logger import logger


class Mqtt(Client):
    __instance = None


    @staticmethod
    def instance():
        if Mqtt.__instance is None:
            raise Exception('Instance has not been created.')

        return Mqtt.__instance


    def __init__(self, config):
        if Mqtt.__instance is not None:
            raise Exception('Singleton instance already created.')

        self.__parse_config(config)

        self.__on_connect_list_lock = Lock()
        self.__on_connect_list = []

        super().__init__(self.__client_id)

        self.enable_logger(logger)

        self.on_connect = self.__on_connect

        Mqtt.__instance = self


    def __parse_config(self, config):
        self.__client_id = None
        self.__host = '127.0.0.1'
        self.__port = 1883
        self.__ca = None
        self.__client_ca = None
        self.__client_key = None

        if config is not None and 'mqtt' in config:
            if 'clientid' in config['mqtt']:
                self.__client_id = config['mqtt']['clientid']
            if 'host' in config['mqtt']:
                self.__host = config['mqtt']['host']
            if 'port' in config['mqtt']:
                self.__port = config['mqtt']['port']
            if 'tls' in config['mqtt']:
                if 'ca' in config['mqtt']['tls']:
                    self.__ca = config['mqtt']['tls']['ca']
                if 'client_ca' in config['mqtt']['tls']:
                    self.__client_ca = config['mqtt']['tls']['client_ca']
                if 'client_key' in config['mqtt']['tls']:
                    self.__client_key = config['mqtt']['tls']['client_key']

    
    def __on_connect(self, client, userdata, flags, rc):
        with self.__on_connect_list_lock:
            for fn in self.__on_connect_list:
                fn(client, userdata, flags, rc)
    

    def connect(self):
        logger.info(f"Connecting to {self.__host} port {self.__port}")
        if not self.__ca is None:
            self.tls_set(ca_certs=self.__ca,certfile=self.__client_ca,keyfile=self.__client_key,tls_version=ssl.PROTOCOL_TLSv1_2)
        self.connect_async(self.__host,port=self.__port)
        self.loop_start()

    def disconnect(self):
        logger.info("Disconnect")
        super().disconnect()
        self.loop_stop()


    def register_on_connect(self,fn):
        with self.__on_connect_list_lock:
            if fn in self.__on_connect_list:
                logger.warning(f'Function {fn} already registered')
                return
            self.__on_connect_list.append(fn)


    def unregister_on_connect(self,fn):
        with self.__on_connect_list_lock:
            try:
                self.__on_connect_list.remove(fn)
            except ValueError as ve:
                logger.warning(ve)


mqtt = paho.mqtt
