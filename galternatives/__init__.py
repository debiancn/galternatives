from __future__ import absolute_import

import gettext
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


PACKAGE = 'galternatives'
APPID = 'org.debiancn.galternatives'

_ = gettext.gettext
gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

logger = logging.getLogger(PACKAGE)

INFO = {
    'program_name': 'G Alternatives',
    'version': '0.13.5',
    'comments': _('A tool to help the administrator select which programs '
                  'provide specific services for the user by default.'),
    'license_type': Gtk.License.GPL_2_0,
    'copyright': '''(C) 2003-2006 Gustavo Noronha Silva
(C) 2017 Boyuan Yang''',
    'website': 'https://alioth.debian.org/projects/galternatives/',
    'authors': (
        'Gustavo Noronha Silva <kov@debian.org>',
        'Leandro A. F. Pereira <leandro@linuxmag.com.br>',
        'Boyuan Yang <073plan@gmail.com>',
        'Yangfl <mmyangfl@gmail.com>',
    ),
}
