'''
Shared components and constants of the application.

Attributes:
    PACKAGE: The package name.
    APPID: Appid for Gtk.Application.
    INFO: Other info (version, url, etc.) of the application.
        Also used in Gtk.AboutDialog construction, unknown parameter may
        cause error.
    _: Gettext function.
    logger: Logger for debug and messages.

'''
from __future__ import print_function

import gettext
import logging
import sys


PACKAGE = 'galternatives'

_ = gettext.gettext
gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

logger = logging.getLogger(PACKAGE)

# set gtk version for the whole module
try:
    import gi
    gi.require_version('Gtk', '3.0')
except ImportError:
    # in some cases gi is not installed since we only want to get INFO
    logger.warn('gi is not installed, assuming you only want to get info for '
                'this application.')

APPID = 'org.debian.experimental.' + PACKAGE
INFO = {
    'program_name': 'G Alternatives',
    'version': '0.92',
    'comments': _('A tool to help the administrator select which programs '
                  'provide specific services for the user by default.'),
    'license_type': 'GPL_2_0',
    'copyright': '''(C) 2003-2006 Gustavo Noronha Silva
(C) 2017 Boyuan Yang''',
    'website': 'https://tracker.debian.org/pkg/galternatives',
    'authors': (
        'Gustavo Noronha Silva <kov@debian.org>',
        'Leandro A. F. Pereira <leandro@linuxmag.com.br>',
        'Boyuan Yang <073plan@gmail.com>',
        'Yangfl <mmyangfl@gmail.com>',
    ),
}


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
