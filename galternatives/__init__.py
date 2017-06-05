from __future__ import absolute_import

import gettext
import logging


PACKAGE = 'galternatives'
VERSION = '0.13.5'

_ = gettext.gettext
gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

DEBUG = False
logger = logging.getLogger(PACKAGE)
