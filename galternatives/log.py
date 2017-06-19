'''
Utils for logger setting. Can be omitted.
'''
from copy import copy
import logging


#The background is set with 40 plus the number of the color, and the foreground with 30
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;{}m"
BOLD_SEQ = "\033[1m"
COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record = copy(record)
        levelname = record.levelname
        if record.levelname in COLORS:
            record.levelname = ''.join((
                COLOR_SEQ.format(30 + COLORS[levelname]), levelname, RESET_SEQ))
        return super(ColoredFormatter, self).format(record)


def set_logger(ns, verbose=False):
    logger = logging.getLogger(ns)
    if verbose:
        logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(ColoredFormatter(
        # log by time
        # '%(asctime)s - %(levelname)s: %(message)s'))
        # gtk style
        # '(%(filename)s:%(process)d): %(funcName)s-%(levelname)s **: %(message)s'))
        # gtk style but lineno
        '(%(filename)s->%(lineno)d): %(funcName)s-%(levelname)s **: %(message)s'))
    logger.addHandler(ch)
