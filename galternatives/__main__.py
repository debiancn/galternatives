from __future__ import absolute_import

from . import logger, _, PACKAGE, APPID
from .appdata import *
from .gui import GAlternativesWindow, GAlternativesAbout

import logging
import os
import sys
import signal
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
# TODO: dbus?
gi.require_version('Polkit', '1.0')
try:
    from gi.repository import Polkit
    from gi.repository import GObject
except ImportError:
    print('Polkit not available, in-program root access not available.')
    Polkit = None


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


class GAlternativesApp(Gtk.Application):
    debug = False

    def __init__(self, *args, **kwargs):
        super(Gtk.Application, self).__init__(
            *args, application_id=APPID, **kwargs)

        self.add_main_option(
            'debug', ord('d'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Enable debug output', None)
        self.add_main_option(
            'normal', ord('n'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            'Do not try to acquire root (as normal user)', None)

    def do_handle_local_options(self, options):
        if options.contains('debug'):
            self.debug = True
            set_logger(True, True)
            logger.debug(_('Testing galternatives...'))
        else:
            set_logger()

        if Gtk.get_minor_version() < 14:
            dialog = Gtk.MessageDialog(
                None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK_CANCEL,
                _('The program requires Gtk+ 3.14 or higher'),
                secondary_text=_(
                    'Your system provides Gtk+ 3.{}. If you continue, the program '
                    'may or may not work properly, and potential damage could happen. '
                    'Strongly recommend update your Gtk+ libaray before continue.'
                ).format(Gtk.get_minor_version()))
            if dialog.run() != Gtk.ResponseType.OK:
                return 2
            dialog.destroy()

        if os.getuid():
            # not root
            if options.contains('normal'):
                logger.warn('No root detected, but continue as in your wishes')
            elif Polkit:
                result = Polkit.Authority.get().check_authorization_sync(
                    Polkit.UnixProcess.new(os.getppid()),
                    'org.freedesktop.policykit.exec',
                    None,
                    Polkit.CheckAuthorizationFlags.ALLOW_USER_INTERACTION,
                    None
                )
                authenticated = False
                try:
                    authenticated = result.get_is_authorized() or result.get_is_challenge()
                except GObject.GError as err:
                    logger.warn('_polkit_auth_callback: error: %s'.format(err))
                if not authenticated:
                    return 1
            elif os.access('/usr/bin/pkexec', os.X_OK):
                return os.system('/usr/bin/pkexec {}'.format(sys.argv[0]))
            elif os.access('/usr/bin/gksu', os.X_OK):
                return os.system('/usr/bin/gksu -t "{}" -m "{}" -u root {}'.format(
                    _('Running Alternatives Configurator...'),
                    _('<b>I need your root password to run\n'
                      'the Alternatives Configurator.</b>'),
                    sys.argv[0]))
            else:
                dialog = Gtk.MessageDialog(
                    None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
                    _('<b>This program should be run as root and <tt>/usr/bin/gksu</tt> is not available.</b>'),
                    use_markup=True,
                    secondary_text=_(
                        'I am unable to request the password myself without gksu. Unless you have '
                        'modified your system to explicitly allow your normal user to modify '
                        'the alternatives system, GAlternatives will not work.'))
                if dialog.run() != Gtk.ResponseType.OK:
                    return 1
                dialog.destroy()

        return -1

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.set_app_menu(Gtk.Builder.new_from_file(locate_appdata(
            PATHS['appdata'], ('menubar.ui', 'glade/menubar.ui')
        )).get_object("menu"))

    def do_activate(self):
        self.window = GAlternativesWindow(self)
        self.window.show()

        # Cannot use add_action_entries()
        # see https://bugzilla.gnome.org/show_bug.cgi?id=678655

        self.about_dialog = GAlternativesAbout(transient_for=self.window.main_window)
        action = Gio.SimpleAction(name='about')
        action.connect('activate', lambda action, param: self.about_dialog.present())
        self.add_action(action)

        action = Gio.SimpleAction(name='preferences')
        action.connect('activate', self.window.show_preferences)
        self.add_action(action)

        action = Gio.SimpleAction(name='quit')
        action.connect('activate', self.window.on_quit)
        self.add_action(action)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = GAlternativesApp()
    sys.exit(app.run(sys.argv))
