import gettext
import gi
import logging

from .info import *


# set gtk version for the whole module
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gtk', '3.0')

gettext.bindtextdomain(PACKAGE)
gettext.textdomain(PACKAGE)

logger = logging.getLogger(PACKAGE)
