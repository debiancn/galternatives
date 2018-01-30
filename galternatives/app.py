from __future__ import absolute_import

from . import logger, eprint, _, PACKAGE, APPID, alternative
from .appdata import *
from .gui import MainWindow, AboutDialog
from .utils import cached_property
try:
    from .log import set_logger
except ImportError:
    set_logger = None

from distutils import spawn
from gi.repository import Gio, GLib, Gtk
import os


class GAlternativesApp(Gtk.Application):
    use_polkit = False
    target_group = None

    def __init__(self, *args, **kwargs):
        super(GAlternativesApp, self).__init__(
            *args, application_id=APPID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs)
        self.add_main_option(
            'debug', ord('d'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            _('Enable debug output'), None)
        self.add_main_option(
            'normal', ord('n'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            _('Do not try to acquire root (as normal user)'), None)
        self.add_main_option(
            'altdir', 0, GLib.OptionFlags.NONE, GLib.OptionArg.FILENAME,
            _('Specify the alternatives directory'), None)
        self.add_main_option(
            'admindir', 0, GLib.OptionFlags.NONE, GLib.OptionArg.FILENAME,
            _('Specify the administrative directory'), None)
        self.add_main_option(
            'log', 0, GLib.OptionFlags.NONE, GLib.OptionArg.FILENAME,
            _('Specify the log file'), None)
        # BUG: Gtk.Application.add_option_group() not working

    def do_handle_local_options(self, options):
        if not self.debug:
            self.debug = bool(options.contains('debug'))
        if set_logger:
            set_logger(PACKAGE, self.debug)
            logger.debug(_('Testing galternatives...'))

        # GtkBuilder will error out if the version requirements are not met.
        # No need to check it again.

        if os.getuid():
            # not root
            if options.contains('normal'):
                logger.warn(_(
                    'No root detected, but continue as in your wishes'))
            elif spawn.find_executable('pkexec'):
                self.use_polkit = True
            else:
                dialog = Gtk.MessageDialog(
                    None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
                    _('<b><tt>pkexec</tt> required for privileged '
                      'operations.</b>'),
                    use_markup=True,
                    secondary_text=_(
                        'The program needs pkexec to perform privileged '
                        'alternatives system modifications under normal user. '
                        'Unless you have modified your system to explicitly '
                        'allow your normal user to do so, GAlternatives will '
                        'not work.'))
                if dialog.run() != Gtk.ResponseType.OK:
                    return 1
                dialog.destroy()

        self.paths = {}
        for option in alternative.Alternative.PATHS:
            value = options.lookup_value(option)
            if value:
                value = value.unpack()
                value.pop()
                self.paths[option] = bytearray(value).decode('utf-8')

        return -1

    def do_local_command_line(self, arguments):
        self.debug = False
        for i, arg in enumerate(arguments):
            if arg.startswith('-dd'):
                self.debug = 2
                break
        return Gtk.Application.do_local_command_line(self, arguments)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()
        if len(args) > 2:
            eprint(_('Specifying more than one group not allowed'))
            return 2
        if len(args) > 1:
            self.target_group = args[1]
            if self.target_group not in self.window.alt_db:
                eprint(_('No such group'))
                self.window.destroy()
                return 1
        self.activate()
        return 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.set_app_menu(
            Gtk.Builder.new_from_file(get_data_path('glade/menubar.ui'))
            .get_object('menu'))

        # Cannot use add_action_entries()
        # see https://bugzilla.gnome.org/show_bug.cgi?id=678655
        for name, activate in {
            'about': self.on_about,
        }.items():
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.add_action(action)

    def do_activate(self):
        if self.debug > 1:
            self.window.edit_warning_show_check.set_active(False)
        self.window.show()

    def on_about(self, action, param):
        self.about_dialog.present()

    @cached_property
    def about_dialog(self):
        return AboutDialog(
            transient_for=self.window and self.window.main_window)

    @cached_property
    def window(self):
        return MainWindow(self, self.paths, self.target_group)
