'''
Interface of the application.
'''
from __future__ import absolute_import

from . import logger, _, PACKAGE, INFO, alternative
from .appdata import *
from .description import *
from .utils import GtkTemplate, stateful_property

import sys
from copy import deepcopy
from functools import wraps
from itertools import cycle
from gi.repository import Gio, GLib, Gtk, GdkPixbuf
if sys.version_info >= (3,):
    from itertools import zip_longest
else:
    from itertools import izip_longest as zip_longest


def hide_on_delete(window, *args):
    '''
    Warpper for Gtk.Widget.hide_on_delete, but allow superfluous arguments.
    Used for singal callback.
    '''
    return Gtk.Widget.hide_on_delete(window)


def reset_dialog(dialog, *args):
    '''
    Select cancel button as default when reshow the dialog. Used for singal
    callback.
    '''
    btn_cancel = \
        dialog.get_widget_for_response(Gtk.ResponseType.CANCEL) or \
        dialog.get_widget_for_response(Gtk.ResponseType.CLOSE)
    btn_cancel.grab_focus()
    btn_cancel.grab_default()


@GtkTemplate(ui=locate_appdata(PATHS['appdata'], 'glade/file_entry.glade'))
class FileEntry(Gtk.Box):
    def __init__(self, **kwargs):
        super(FileEntry, self).__init__(**kwargs)
        self.init_template()
        self.entry = self.get_template_child('entry')

    @GtkTemplate.Callback
    def open_file(self, button):
        '''Select a file and fill the entry with the path.'''
        file_chooser = Gtk.FileChooserDialog(
            title=_('Select File'), action=Gtk.FileChooserAction.OPEN,
            parent=button.get_toplevel(), buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        if file_chooser.run() == Gtk.ResponseType.OK:
            self.entry.set_text(file_chooser.get_filename())
        file_chooser.destroy()

    def set_text(self, text):
        return self.entry.set_text(text)

    def get_text(self):
        return self.entry.get_text()

    def set_icon_from_icon_name(self, icon_pos, icon_name):
        return self.entry.set_icon_from_icon_name(icon_pos, icon_name)

    def connect(self, detailed_signal, handler):
        return self.entry.connect(
            detailed_signal, lambda widget, *args: handler(self, *args))


# can't inherit GtkTemplate, need workaround

@GtkTemplate(ui=locate_appdata(PATHS['appdata'], 'glade/edit_dialog.glade'))
class EditDialog(Gtk.Dialog):
    slave_it = None

    def __init__(self, *args, **kwargs):
        super(EditDialog, self).__init__(**kwargs)
        self.init_template()
        for widget_id in {
            'requires', 'slaves_tv', 'slave_fields', 'slaves_edit',
            'new_group_warning'
        }:
            setattr(self, widget_id, self.get_template_child(widget_id))

    def _init_edit_dialog(self):
        for i, (field_name, widget_class) in enumerate(self.REQUIRES):
            widget = widget_class()
            setattr(self, field_name.lower(), widget)
            self.requires.attach(Gtk.Label(label=_(field_name)), 0, i, 1, 1)
            self.requires.attach(widget, 1, i, 1, 1)
        self.requires.show_all()

        self.slaves_entries = []
        for i, (column_name, widget_class) in enumerate(self.SLAVES):
            column_name = _(column_name)
            # slaves_tv
            column = Gtk.TreeViewColumn(
                column_name, Gtk.CellRendererText(),
                text=2 * i, background=2 * i + 1)
            column.set_resizable(True)
            self.slaves_tv.append_column(column)
            # slave_fields
            widget = widget_class()
            widget.i_column = i
            widget.connect('changed', self.on_slave_fields_changed)
            self.slaves_entries.append(widget)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.pack_start(Gtk.Label(label=column_name), False, False, 0)
            box.pack_start(widget, True, True, 0)
            self.slave_fields.pack_start(box, False, False, 0)
        self.slave_fields.show_all()
        self.slaves_model = Gtk.ListStore(*(str, ) * len(self.SLAVES) * 2)
        self.slaves_tv.set_model(self.slaves_model)

    def __new__(cls, *args, **kwargs):
        if cls != EditDialog:
            self = EditDialog(**kwargs)
            self.__class__ = cls
            EditDialog._init_edit_dialog(self)
            return self
        else:
            return super(EditDialog, cls).__new__(cls, *args, **kwargs)

    @GtkTemplate.Callback
    def add_row(self, button):
        self.slaves_model.append((None, ) * len(self.SLAVES) * 2)

    @GtkTemplate.Callback
    def remove_row(self, button):
        model, it = self.slaves_tv.get_selection().get_selected()
        del model[it]
        for widget in self.slaves_entries:
            widget.set_text('')

    @GtkTemplate.Callback
    def on_click_slave(self, widget):
        model, it = widget.get_selected()
        if it is None:
            return
        self.slave_it = it
        for widget, text in zip(
                self.slaves_entries, model[it][::2] if it else cycle('')):
            widget.set_text(text or '')

    def on_slave_fields_changed(self, widget):
        if self.slave_it is None:
            return
        self.slaves_model[self.slave_it][2 * widget.i_column] = \
            widget.get_text()

    @GtkTemplate.Callback
    def on_response(self, window, response_id):
        # only bind to cancel button
        # dialog response can not be cancelled, thus not suitable for validation
        if response_id == Gtk.ResponseType.CANCEL:
            # do not emit delete-event
            self.destroy()

    @GtkTemplate.Callback
    def close(self, *args):
        return super(EditDialog, self).close()

    @GtkTemplate.Callback
    def on_delete_event(self, window, event):
        validated = True
        for (field_name, widget_class) in self.REQUIRES:
            widget = getattr(self, field_name.lower())
            if not widget.get_text():
                self.requires_set_vaild(widget, False)
                validated = False
            else:
                self.requires_set_vaild(widget, True)
        for row in self.slaves_model:
            if not row[0]:
                row[1] = 'red'
                validated = False
            elif row[1]:
                row[1] = None
        if not validated:
            return True
        return self.on_close(window, event)

    def requires_set_vaild(self, widget, status):
        widget.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, None if status else 'dialog-error')


class GroupDialog(EditDialog):
    REQUIRES = (
        ('Name', Gtk.Entry),
        ('Link', FileEntry),
    )
    SLAVES = REQUIRES

    def __init__(self, group=None, *args, **kwargs):
        self.group = group

        if isinstance(self.group, alternative.Group):
            self.set_title(_('Edit group - {}').format(self.group.name))
            self.name.set_text(self.group.name)
            self.link.set_text(self.group.link)
            for slave_name in self.group[1:]:
                self.slaves_model.append(
                    (slave_name, None, self.group[slave_name], None))
        else:
            self.set_title(_('Add group'))
            self.new_group_warning.show()

    def on_close(self, window, event):
        main_instance = self.get_transient_for().main_instance
        name = self.name.get_text()
        reload_groups_p = False
        slaves_diff = {}
        if self.group is None:
            self.group = alternative.Group(name, create=True)
            main_instance.alt_db.add(self.group)
            reload_groups_p = True
        elif name != self.group.name:
            slaves_diff[self.group.name] = name
            main_instance.alt_db.move(self.group.name, name)
            reload_groups_p = True
        self.group.link = self.link.get_text()
        slaves = set()
        for i, row in enumerate(self.slaves_model):
            if self.group[i] != row[0]:
                slaves_diff[self.group[i]] = row[0]
            self.group[row[0]] = row[2]
            slaves.add(row[0])
        for old_slave in self.group[1:]:
            if old_slave not in slaves:
                del self.group[old_slave]
        for option in self.group.options:
            option.update({
                slaves_diff[k]: v for k, v in option.items() if k in slaves_diff
            })
        if reload_groups_p:
            main_instance.load_groups()
        else:
            main_instance.load_options()
        main_instance.on_change()


class OptionDialog(EditDialog):
    REQUIRES = (
        ('Path', FileEntry),
        ('Priority', Gtk.SpinButton),
    )
    SLAVES = (
        ('Name', Gtk.Entry),
        ('Path', FileEntry),
    )

    def __init__(self, option=None, group=None, *args, **kwargs):
        self.group = group
        self.option = option

        self.slaves_edit.hide()
        self.priority.set_adjustment(
            Gtk.Adjustment(0, -(1 << 31), 1 << 31, 1, 10, 0))
        if isinstance(self.option, alternative.Option):
            self.set_title(
                _('Edit option - {}').format(self.option[self.group.name]))
            self.path.set_text(self.option[self.group.name])
            self.priority.set_value(self.option.priority)
            for slave_name in self.group[1:]:
                self.slaves_model.append(
                    (slave_name, None, self.option[slave_name], None))
        else:
            self.set_title(_('Add option'))
            self.priority.set_value(0)
            for slave_name in self.group[1:]:
                self.slaves_model.append(
                    (slave_name, None, None, None))

    def on_close(self, window, event):
        main_instance = self.get_transient_for().main_instance
        if self.option is None:
            self.option = alternative.Option()
            self.group.options.append(self.option)
        for row in self.slaves_model:
            if row[2]:
                self.option[row[0]] = row[2]
            elif row[0] in self.option:
                del self.option[row[0]]
        path = self.path.get_text()
        self.option[self.group.name] = path
        self.option.priority = self.priority.get_value_as_int()
        main_instance.load_options()
        main_instance.on_change()


def advanced(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if self.no_edit_warning:
            return f(self, *args, **kwargs)
        elif self.edit_warning.run() != Gtk.ResponseType.CANCEL:
            self.no_edit_warning = not self.edit_warning_show_check.get_active()
            return f(self, *args, **kwargs)
    return wrapper


icontheme = Gtk.IconTheme.get_default()
STATUS_ICONS = []
for icon_name in ('dialog-ok', 'dialog-error'):
    try:
        STATUS_ICONS.append(icontheme.load_icon(icon_name, 8, 0))
    except GLib.Error:
        STATUS_ICONS.append(None)
del icontheme


class MainWindow(object):
    no_edit_warning = False
    group = None
    paths = {}

    def __init__(self, app):
        '''Load alternative database and fetch objects from the builder.'''
        # glade XML
        self.builder = Gtk.Builder.new_from_file(locate_appdata(
            PATHS['appdata'], 'glade/galternatives.glade'))
        for widget_id in {
            # main window
            'main_window',
            'pending_box', 'groups_tv',
            'alternative_label', 'link_label', 'description_label',
            'status_switch', 'options_tv', 'options_column_package',
            'options_menu', 'option_edit_item', 'option_remove_item',
            'option_add_item',
            # dialogs and messages
            'preferences_dialog',
            'edit_warning', 'edit_warning_show_check',
            'confirm_closing', 'commit_failed', 'results_tv'
        }:
            setattr(self, widget_id, self.builder.get_object(widget_id))
        self.main_window.set_application(app)
        self.main_window.main_instance = self
        self.options_menu.insert_action_group('win', self.main_window)

        # actions and signals
        for name, activate in {
            ('preferences', lambda *args: self.preferences_dialog.show()),
            ('quit', self.on_quit),
            ('group.add', self.add_group),
            ('group.edit', self.edit_group),
            ('group.remove', self.remove_group),
            ('option.add', self.add_option),
            ('option.edit', self.edit_option),
            ('option.remove', self.remove_option),
            ('change.save', self.on_save),
            ('change.reload', self.load_db),
        }:
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.main_window.add_action(action)
            setattr(self, name.replace('.', '_'), action)

        for name in {'delay_mode', 'query_package'}:
            action = Gio.SimpleAction.new_stateful(
                name, None, GLib.Variant('b', getattr(self, name)))

            def on_action_toggle_func(name):
                def on_action_toggle(action, value):
                    action.set_state(value)
                    setattr(self, name, value.get_boolean())

                return on_action_toggle

            action.connect('change-state', on_action_toggle_func(name))
            self.main_window.add_action(action)

        self.builder.connect_signals(self)

        self.load_db()
        # save placeholder text strings
        self.empty_group = \
            alternative.Group(self.alternative_label.get_text(), create=True)
        self.empty_group[self.empty_group.name] = self.link_label.get_text()
        self.empty_group.description = self.description_label.get_text()
        self.empty_group._current = False

    hide_on_delete = staticmethod(hide_on_delete)
    reset_dialog = staticmethod(reset_dialog)

    def show(self):
        '''Show the main window. Pretend itself as Gtk.Window.'''
        return self.main_window.show()

    @property
    def has_unsaved(self):
        '''Whether there are unsaved changes'''
        return self.pending_box.get_visible()

    # config actions begin #

    @stateful_property(False)
    def delay_mode(self, value):
        return value

    @stateful_property(False)
    def query_package(self, value):
        self.options_column_package.set_visible(value)
        if value:
            self.load_options_pkgname()
        return value

    def load_config(self, widget=None):
        for option in alternative.Alternative.PATHS:
            self.builder.get_object(option + '_chooser').set_filename(
                getattr(self.alt_db, option))

    def on_preferences_dialog_response(self, widget, response_id):
        self.paths = {
            option: self.builder.get_object(option + '_chooser').get_filename()
            for option in alternative.Alternative.PATHS
        }
        if any(getattr(self.alt_db, option) != path
               for option, path in self.paths.items()):
            self.load_db()

    # config actions end #

    # commit actions begin #

    def on_quit(self, *args):
        '''Check for unsaved changes before quitting.'''
        if self.has_unsaved:
            response_id = self.confirm_closing.run()
            if response_id == Gtk.ResponseType.CANCEL:
                return True
            if response_id == Gtk.ResponseType.NO:
                return self.do_quit()
            if response_id == Gtk.ResponseType.YES:
                self.do_save()
                return self.has_unsaved
        self.do_quit()

    def do_quit(self, *args):
        '''Close the main window.'''
        self.main_window.destroy()

    def on_save(self, *args):
        self.do_save()

    def do_save(self, diff_cmds=None, autosave=False):
        '''Save changes.'''
        if diff_cmds is None:
            diff_cmds = self.alt_db.compare(self.alt_db_old)
        returncode, results = self.alt_db.commit(diff_cmds)
        if returncode:
            self.on_change()
            model = self.results_tv.get_model()
            model.clear()
            for cmd, result in zip_longest(friendlize(diff_cmds), results):
                if result:
                    it = model.append(
                        None, (STATUS_ICONS[result.returncode != 0], cmd))
                    for msg in (
                        _('Run command: ') + ' '.join(result.cmd),
                        result.out.rstrip(),
                        result.err.rstrip()
                    ):
                        model.append(it, (None, msg))
                else:
                    it = model.append(None, (None, cmd))
            self.commit_failed.show_all()
            self.alt_db_old = alternative.Alternative(**self.paths)
            self.on_change()
        elif not autosave:
            self.load_db()

    def save_and_quit(self, *args, **kwargs):
        self.do_save()
        self.do_quit()

    def load_db(self, *args):
        self.alt_db = alternative.Alternative(**self.paths)
        self.alt_db_old = deepcopy(self.alt_db)
        self.pending_box.hide()
        self.load_groups()

    # commit actions end #

    # detail windows actions begin #
    # TODO: windows need a good way for handling (group destruction)

    @advanced
    def add_group(self, widget, data):
        self.show_group_window(None)

    @advanced
    def edit_group(self, widget, data):
        self.show_group_window(self.group)

    @advanced
    def remove_group(self, widget, data):
        del self.alt_db[self.group.name]
        self.load_groups()
        self.on_change()

    def show_group_window(self, group):
        window = GroupDialog(group, transient_for=self.main_window)
        window.present()

    @advanced
    def add_option(self, widget, data):
        self.show_option_window(self.group, None)

    @advanced
    def edit_option(self, widget, data):
        self.show_option_window(self.group, self.option)

    @advanced
    def remove_option(self, widget, data):
        self.load_options()
        self.on_change()

    def show_option_window(self, group, option):
        window = OptionDialog(option, group, transient_for=self.main_window)
        window.present()

    # detail windows actions end #

    # main window actions begin #

    def load_groups(self):
        # disable edit/remove buttons
        self.group_edit.set_enabled(False)
        self.group_remove.set_enabled(False)

        # load alternative group into groups_tv
        treeview = self.groups_tv
        selection = treeview.get_selection()
        selection.unselect_all()  # prevent event trigger
        model = treeview.get_model()
        model.clear()
        for group_name in sorted(self.alt_db):
            model.append((group_name, ))

        # clear options_tv
        if self.group is not None:
            self.group = self.empty_group
            self.load_options()
            self.description_label.set_text(self.empty_group.description)
            self.group = None

    def click_group(self, widget):
        '''Load options for selected alternative group into options_tv.'''
        # widget = self.groups_tv.get_selection()
        model, it = widget.get_selected()
        if it is None:
            return
        group = self.alt_db[model.get_value(it, 0)]
        if group == self.group:
            return

        # enable buttons
        if not self.group:
            self.group_edit.set_enabled(True)
            self.group_remove.set_enabled(True)
        # save current group
        self.group = group
        self.load_options()

    def load_options(self):
        if self.group is None:
            return

        # set the name of the alternative to the information area
        name, description = altname_description(self.group.name)
        self.alternative_label.set_text(name)
        self.link_label.set_text(self.group.link)
        self.description_label.set_text(description)
        self.status_switch.set_active(self.group.status)

        # set columns
        self.options_tv.get_column(1).set_title(self.group.name)
        for i in range(4, self.options_tv.get_n_columns()):
            self.options_tv.remove_column(self.options_tv.get_column(4))
        for i in range(1, len(self.group)):
            column = Gtk.TreeViewColumn(
                self.group[i], Gtk.CellRendererText(), text=i + 3)
            column.set_resizable(True)
            self.options_tv.append_column(column)

        # load options_liststore
        options_model = Gtk.ListStore(
            bool, int, str, *(str, ) * len(self.group))
        self.options_tv.set_model(options_model)
        for option in self.group.options:
            options_model.append((
                option == self.group.current,
                option.priority,
                None,
            ) + option.paths(self.group))
        if self.query_package:
            self.load_options_pkgname()

    def load_options_pkgname(self):
        for record in self.options_tv.get_model():
            if record[2]:
                break
            record[2] = query_package(record[3])

    def load_options_current(self):
        self.options_tv.get_model().foreach(
            lambda model, path, it: model.set(
                it, 0, self.group.current == self.group.options[path[0]]))

    def change_status(self, widget, gparam):
        '''
        Handle click on status_switch.
        When current status is auto, it will block the click action.
        '''
        widget.set_sensitive(not widget.get_active())
        if widget.get_active():
            self.select_option()

    def click_option(self, widget, path):
        '''Handle click on radio buttons of options.'''
        self.select_option(int(path))

    def select_option(self, index=None):
        if index is None:
            if self.group.status:
                return
        else:
            if not self.group.status and \
                    self.group.current == self.group.options[index]:
                return
        self.group.select(index)
        self.load_options_current()
        self.status_switch.set_active(self.group.status)
        self.on_change(not self.delay_mode)

    def on_options_tv_button_press_event(self, treeview, event):
        if event.button == 3 and self.group:
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            self.option = pthinfo and self.group.options[pthinfo[0][0]]
            pthinfo = bool(pthinfo)
            self.option_edit.set_enabled(pthinfo)
            self.option_remove.set_enabled(pthinfo)
            self.options_menu.popup(None, None, None, None,
                                    event.button, event.time)

    def on_change(self, autosave=False):
        diff_cmds = self.alt_db.compare(self.alt_db_old)
        if autosave and len(diff_cmds) == 1:
            self.do_save(diff_cmds, autosave=True)
            return
        if diff_cmds:
            self.pending_box.show()
        else:
            self.pending_box.hide()

    # main window actions end #


class AboutDialog(Gtk.AboutDialog):
    '''About dialog of the application.'''

    logo_path = locate_appdata(PATHS['icon'], 'galternatives.png')

    def __init__(self, **kwargs):
        kwargs.update(INFO)
        if self.logo_path is None:
            logger.warn(_('Logo missing. Is your installation correct?'))
        super(Gtk.AboutDialog, self).__init__(
            logo=self.logo_path and
            GdkPixbuf.Pixbuf.new_from_file(self.logo_path),
            translator_credits=_('translator_credits'),
            **kwargs)
        self.connect('response', hide_on_delete)
        self.connect('delete-event', hide_on_delete)
