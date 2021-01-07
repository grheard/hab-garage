import sys
import signal

from .logger import logger
from .main import Main


def __signal_handler(signal, frame):
    try:
        logger.info(f"Caught signal {signal}")
        gmain.stop()
    except:
        sys.exit(0)


def init():
    global gmain

    logger.info("Setting up.")

    signal.signal(signal.SIGINT, __signal_handler)

    gmain = Main()

    logger.info("Start.")

    gmain.start()

    logger.info("End.")


if __name__ == '__main__':
    init()
