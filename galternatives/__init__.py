from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement, print_function, unicode_literals

from .appdata import *

import logging

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


set_logger(True, True)
