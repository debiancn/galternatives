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
    debug = False
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
            _('Specifies the alternatives directory'), None)
        self.add_main_option(
            'admindir', 0, GLib.OptionFlags.NONE, GLib.OptionArg.FILENAME,
            _('Specifies the administrative directory'), None)
        self.add_main_option(
            'log', 0, GLib.OptionFlags.NONE, GLib.OptionArg.FILENAME,
            _('Specifies the log file'), None)
        # BUG: Gtk.Application.add_option_group() not working

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
                logger.warn(_(
                    'No root detected, but continue as in your wishes'))
            elif spawn.find_executable('pkexec'):
                self.use_polkit = True
            elif spawn.find_executable('gksudo'):
                logger.warn(_("No `pkexec' detected, but found `gksudo'. "
                              "You should really consider polkit."))
                return os.system(
                    'gksudo -t "{}" -m "{}" -u root python "{}"'.format(
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
                    secondary_text=_(
                        'I am unable to request the password myself without '
                        'gksu. Unless you have modified your system to '
                        'explicitly allow your normal user to modify the '
                        'alternatives system, GAlternatives will not work.'))
                if dialog.run() != Gtk.ResponseType.OK:
                    return 1
                dialog.destroy()

        self.paths = {
            option: ''.join(map(chr, options.lookup_value(option)))[:-1]
            for option in alternative.Alternative.PATHS
            if options.contains(option)
        }

        return -1

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
