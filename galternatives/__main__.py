#!/usr/bin/env python
import os
import signal
import sys

# If run as a single file (rather than a module), include the correct path so
# that the package can be imported
if __name__ == '__main__' and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from galternatives import logger, _, PACKAGE, APPID
from galternatives.appdata import *
from galternatives.gui import MainWindow, AboutDialog
from galternatives.utils import cached_property
try:
    from galternatives.log import set_logger
except ImportError:
    set_logger = None

from gi.repository import Gio, GLib, Gtk


class GAlternativesApp(Gtk.Application):
    debug = False

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

        # GtkBuilder will error out if the version requirements are not met.
        # No need to check it again.

        if os.getuid():
            # not root
            if options.contains('normal'):
                logger.warn('No root detected, but continue as in your wishes')
            # TODO: other methods to acquire root
            elif os.access('/usr/bin/gksudo', os.X_OK):
                return os.system(
                    '/usr/bin/gksudo -t "{}" -m "{}" -u root python "{}"'.format(
                        _('Running Alternatives Configurator...'),
                        _('<b>I need your root password to run\n'
                          'the Alternatives Configurator.</b>'),
                        __file__))
            else:
                dialog = Gtk.MessageDialog(
                    None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
                    _('<b>This program should be run as root and '
                      '<tt>/usr/bin/gksu</tt> is not available.</b>'),
                    use_markup=True,
                    secondary_text=_('''\
I am unable to request the password myself without gksu. Unless you have \
modified your system to explicitly allow your normal user to modify \
the alternatives system, GAlternatives will not work.'''))
                if dialog.run() != Gtk.ResponseType.OK:
                    return 1
                dialog.destroy()

        return -1

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.set_app_menu(Gtk.Builder.new_from_file(locate_appdata(
            PATHS['appdata'], 'glade/menubar.ui'
        )).get_object('menu'))

        # Cannot use add_action_entries()
        # see https://bugzilla.gnome.org/show_bug.cgi?id=678655
        for name, activate in {
            'about': self.on_about,
        }.items():
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.add_action(action)

    def do_activate(self):
        self.window.show()

    def on_about(self, action, param):
        self.about_dialog.present()

    @cached_property
    def about_dialog(self):
        return AboutDialog(
            transient_for=self.window and self.window.main_window)

    @cached_property
    def window(self):
        return MainWindow(self)


def main():
    # Allow Ctrl-C to work
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = GAlternativesApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
