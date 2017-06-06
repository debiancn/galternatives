#!/usr/bin/env python
from __future__ import absolute_import

from . import logger, _, DEBUG, PACKAGE

import logging
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import sys
# https://stackoverflow.com/questions/16410852/keyboard-interrupt-with-with-python-gtk
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


def gtk_message(hint, message_type=Gtk.MessageType.WARNING):
    dialog = Gtk.MessageDialog(
        None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
        message_type, Gtk.ButtonsType.OK_CANCEL)
    dialog.set_markup(hint)
    if dialog.run() != Gtk.ResponseType.OK:
        exit(1)
    dialog.destroy()


def no_gksu():
    return gtk_message(_(
        '<b>This program should be run as root and /usr/bin/gksu is not available.</b>\n\n'
        'I am unable to request the password myself without gksu. Unless you have '
        'modified your system to explicitly allow your normal user to modify '
        'the alternatives system, GAlternatives will not work.'))


def set_logger(verbose=False, full=False):
    logger = logging.getLogger(PACKAGE)
    if verbose:
        logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    if full:
        formatter = logging.Formatter(
            # log by time
            # '%(asctime)s - %(levelname)s: %(message)s')
            # gtk style
            # '(%(pathname)s:%(process)d): %(funcName)s-%(levelname)s **: %(message)s')
            # gtk style but lineno
            '(%(pathname)s->%(lineno)d): %(funcName)s-%(levelname)s **: %(message)s')
        ch.setFormatter(formatter)
    logger.addHandler(ch)


if Gtk.get_minor_version() < 14:
    gtk_message(_(
        '<b>This program required Gtk+ 3.14 or higher.</b>\n\n'
        'The program can only detect Gtk+ {}.{}. If you continue, the program '
        'may or may not work properly, and potential damage could be happened. '
        'Strongly recommend update your Gtk+ libaray before continue.').format(
            Gtk.get_major_version(), Gtk.get_minor_version()),
        Gtk.MessageType.ERROR)

if len(sys.argv) >= 2 and sys.argv[1] in ['--debug', '-d']:
    DEBUG = True
    set_logger(True, True)
else:
    set_logger()

if os.getuid():
    # not root
    if os.access('/usr/bin/gksu', os.X_OK):
        sys.exit(os.system('/usr/bin/gksu -t "{}" -m "{}" -u root {}'.format(
            _('Running Alternatives Configurator...'),
            _('<b>I need your root password to run\n'
              'the Alternatives Configurator.</b>'),
            sys.argv[0])))
    elif DEBUG:
        logger.warn('No root detected, but continue as in debug mode')
    else:
        no_gksu()


from .gui import GAlternatives

galternatives = GAlternatives()
logger.debug(_('Testing galternatives...'))
Gtk.main()
