'''
Set formatter for logger.

This file should only be imported in the main function. It can be safely
removed.
'''
from copy import copy
import logging


# The background is set with 40 plus the number of the color, and the foreground
# with 30
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# These are the sequences need to get colored output
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
        '''
        Format the record using the underlying formatter, but display the
        level name in color.

        The function does not change the original record.
        '''
        record = copy(record)
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = ''.join((
                COLOR_SEQ.format(30 + COLORS[levelname]), levelname, RESET_SEQ))
        return super(ColoredFormatter, self).format(record)


def set_logger(ns, verbose=False):
    '''
    Set console output for logger of giver namespace.

    Args:
        ns (str): Namespace of the logger.
        verbose (bool, optional): Whether to set logger level to debug.
            Default is false.

    '''
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
