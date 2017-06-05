#!/usr/bin/env python
from __future__ import absolute_import

from . import logger, _, DEBUG, set_logger
from .gui import GAlternatives, no_gksu

import gtk
import os
import sys


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

galternatives = GAlternatives()
logger.debug(_('Testing galternatives...'))
gtk.main()
