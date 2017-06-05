from __future__ import absolute_import

from .appdata import *

import gettext
import logging

_ = gettext.gettext
gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

DEBUG = False
logger = logging.getLogger(PACKAGE)


def set_logger(verbose=False, full=False):
    if verbose:
        logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    if full:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        logging.getLogger(PACKAGE).addHandler(ch)
    logger.addHandler(ch)
