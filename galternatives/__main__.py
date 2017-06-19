from __future__ import absolute_import

from . import logger, _, PACKAGE, APPID
from .appdata import *
from .gui import GAlternativesWindow, GAlternativesAbout, Polkit
try:
    from .log import set_logger
except ImportError:
    set_logger = None

import os
import sys
import signal
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk


class GAlternativesApp(Gtk.Application):
    debug = False
    window = None
    about_dialog = None

    def __init__(self, *args, **kwargs):
        super(GAlternativesApp, self).__init__(
            *args, application_id=APPID, **kwargs)
        self.add_main_option(
            'debug', ord('d'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            _('Enable debug output'), None)
        self.add_main_option(
            'normal', ord('n'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            _('Do not try to acquire root (as normal user)'), None)

    def do_handle_local_options(self, options):
        self.debug = options.contains('debug')
        if set_logger:
            set_logger(PACKAGE, self.debug)
            logger.debug(_('Testing galternatives...'))

        if Gtk.get_minor_version() < 14:
            dialog = Gtk.MessageDialog(
                None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK_CANCEL,
                _('The program requires Gtk+ 3.14 or higher'),
                secondary_text=_(
                    'Your system only provides Gtk+ 3.{}. If you continue, the program '
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
                logger.debug('delay root acquirement since Polkit available')
            elif os.access('/usr/bin/pkexec', os.X_OK):
                return os.system('/usr/bin/pkexec "{}"'.format(sys.argv[0]))
            elif os.access('/usr/bin/gksu', os.X_OK):
                return os.system('/usr/bin/gksu -t "{}" -m "{}" -u root "{}"'.format(
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
        )).get_object('menu'))

    def do_activate(self):
        if self.window is None:
            self.window = GAlternativesWindow(self)

            # Cannot use add_action_entries()
            # see https://bugzilla.gnome.org/show_bug.cgi?id=678655
            for name, activate in {
                'about': self.on_about,
            }.items():
                action = Gio.SimpleAction(name=name)
                action.connect('activate', activate)
                self.add_action(action)

        self.window.show()

    def on_about(self, action, param):
        if self.about_dialog is None:
            self.about_dialog = GAlternativesAbout(transient_for=self.window and self.window.main_window)
        self.about_dialog.present()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = GAlternativesApp()
    sys.exit(app.run(sys.argv))
