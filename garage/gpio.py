import pigpio


class Gpio(pigpio.pi):
    __instance = None


    @staticmethod
    def instance():
        if Gpio.__instance is None:
            raise Exception('Instance has not been created.')
        
        return Gpio.__instance


    def __init__(self, config):
        if Gpio.__instance is not None:
            raise Exception('Singleton instance already created.')

        self.__parse_config(config)

        super().__init__(host=self.__host,port=self.__port)

        Gpio.__instance = self


    def __parse_config(self, config):
        self.__host = 'localhost'
        self.__port = 8888
        if config is not None and 'gpio' in config:
            if 'host' in config['gpio']:
                self.__host = config['gpio']['host']
            if 'port' in config['gpio']:
                self.__port = config['gpio']['port']


gpio = pigpio