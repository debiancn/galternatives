#!/usr/bin/env python
from __future__ import absolute_import

from . import logger, _, DEBUG, PACKAGE

import logging
import os
import gtk
import sys


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


def no_gksu():
    dialog = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE)
    dialog.set_markup(_('<b>This program should be run as root and /usr/bin/gksu is not available.</b>\n\n'
                        'I am unable to request the password myself without gksu. Unless you have '
                        'modified your system to explicitly allow your normal user to modify '
                        'the alternatives system, GAlternatives will not work.'))
    dialog.run()
    dialog.destroy()


if os.getuid():
    # not root
    if os.access('/usr/bin/gksu', os.X_OK):
        sys.exit(os.system('/usr/bin/gksu -t "{}" -m "{}" -u root {}'.format(
            _('Running Alternatives Configurator...'),
            _('<b>I need your root password to run\n'
              'the Alternatives Configurator.</b>'),
            sys.argv[0])))
    else:
        no_gksu()

if len(sys.argv) >= 2 and sys.argv[1] == '--debug':
    DEBUG = True
    set_logger(True, True)
else:
    set_logger()

from .gui import GAlternatives

galternatives = GAlternatives()
logger.debug(_('Testing galternatives...'))
gtk.main()
