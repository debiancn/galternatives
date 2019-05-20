'''
Interface of the application.
'''
from __future__ import absolute_import

from . import logger, _, PACKAGE, INFO, alternative
from .appdata import *
from .description import *
from .utils import stateful_property

from copy import deepcopy
from functools import wraps
from gi.repository import GdkPixbuf, Gdk, Gio, GLib, Gtk, GObject
import os
import shutil
import sys
import threading
try:
    import xdg.Config
except ImportError:
    class xdg:
        class Config:
            icon_size = 48
if sys.version_info >= (3,):
    from itertools import zip_longest
else:
    from itertools import izip_longest as zip_longest

GObject.threads_init()


def hide_on_delete(window, *args):
    '''
    Warpper for Gtk.Widget.hide_on_delete, but allow superfluous arguments.
    Used for signal callback.
    '''
    return Gtk.Widget.hide_on_delete(window)


def reset_dialog(dialog, *args):
    '''
    Select cancel button as default when reshow the dialog. Used for signal
    callback.
    '''
    btn_cancel = \
        dialog.get_widget_for_response(Gtk.ResponseType.CANCEL) or \
        dialog.get_widget_for_response(Gtk.ResponseType.CLOSE)
    btn_cancel.grab_focus()
    btn_cancel.grab_default()


@Gtk.Template.from_file(get_data_path('glade/file_entry.glade'))
class FileEntry(Gtk.Box):
    __gtype_name__ = 'FileEntry'
    entry = Gtk.Template.Child('entry')

    @Gtk.Template.Callback('open_file')
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

@Gtk.Template.from_file(get_data_path('glade/edit_dialog.glade'))
class EditDialog(Gtk.Dialog):
    __gtype_name__ = 'EditDialog'
    slave_it = None

    requires = Gtk.Template.Child('requires')
    slaves_tv = Gtk.Template.Child('slaves_tv')
    slave_fields = Gtk.Template.Child('slave_fields')
    slaves_edit = Gtk.Template.Child('slaves_edit')
    new_group_warning = Gtk.Template.Child('new_group_warning')

    def _init_edit_dialog(self):
        for i, (field_name, label_name, widget_class) in \
                enumerate(self.REQUIRES):
            widget = widget_class()
            widget.set_hexpand(True)
            setattr(self, field_name.lower(), widget)
            self.requires.attach(Gtk.Label(label=label_name), 0, i, 1, 1)
            self.requires.attach(widget, 1, i, 1, 1)
        self.requires.show_all()

        self.slaves_entries = []
        for i, (column_name, label_name, widget_class) in \
                enumerate(self.SLAVES):
            # slaves_tv
            column = Gtk.TreeViewColumn(
                label_name, Gtk.CellRendererText(),
                text=2 * i, background=2 * i + 1)
            column.set_resizable(True)
            self.slaves_tv.append_column(column)
            # slave_fields
            widget = widget_class()
            widget.i_column = i
            widget.connect('changed', self.on_slave_fields_changed)
            self.slaves_entries.append(widget)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.pack_start(Gtk.Label(label=label_name), False, False, 0)
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

    @Gtk.Template.Callback('add_row')
    def add_row(self, button):
        self.slaves_model.append((None, ) * len(self.SLAVES) * 2)

    @Gtk.Template.Callback('remove_row')
    def remove_row(self, button):
        model, it = self.slaves_tv.get_selection().get_selected()
        del model[it]
        for widget in self.slaves_entries:
            widget.set_text('')

    @Gtk.Template.Callback('on_click_slave')
    def on_click_slave(self, widget):
        model, it = widget.get_selected()
        self.slave_it = it
        if it is None:
            return
        for widget, text in zip_longest(
                self.slaves_entries, model[it][::2] if it else ()):
            widget.set_text(text or '')

    def on_slave_fields_changed(self, widget):
        if self.slave_it is None:
            return
        self.slaves_model[self.slave_it][2 * widget.i_column] = \
            widget.get_text()

    @Gtk.Template.Callback('on_response')
    def on_response(self, window, response_id):
        # only bind to cancel button
        # dialog response can not be cancelled, thus not suitable for validation
        if response_id == Gtk.ResponseType.CANCEL:
            # do not emit delete-event
            self.destroy()

    @Gtk.Template.Callback('close')
    def close(self, *args):
        return super(EditDialog, self).close()

    @Gtk.Template.Callback('on_delete_event')
    def on_delete_event(self, window, event):
        validated = True
        empty = True
        for (field_name, _, widget_class) in self.REQUIRES:
            widget = getattr(self, field_name.lower())
            if not widget.get_text():
                self.requires_set_vaild(widget, False)
                validated = False
            else:
                self.requires_set_vaild(widget, True)
                empty = False
        for row in self.slaves_model:
            if not row[0]:
                row[1] = 'red'
                validated = False
            elif row[1]:
                row[1] = None
                empty = False
        if self.is_creating and empty:
            return
        if not validated:
            return True
        return self.on_close(window, event)

    @staticmethod
    def requires_set_vaild(widget, status):
        widget.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, None if status else 'dialog-error')


class GroupDialog(EditDialog):
    REQUIRES = (
        ('Name', _('Name'), Gtk.Entry),
        ('Link', _('Link'), FileEntry),
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

    @property
    def is_creating(self):
        return not isinstance(self.group, alternative.Group)

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
            new_slave = row[0]
            if self.group[i + 1] != new_slave:
                slaves_diff[self.group[i + 1]] = new_slave
            self.group[new_slave] = row[2]
            slaves.add(new_slave)
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
        ('Path', _('Path'), FileEntry),
        ('Priority', _('Priority'), Gtk.SpinButton),
    )
    SLAVES = (
        ('Name', _('Name'), Gtk.Entry),
        ('Path', _('Path'), FileEntry),
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

    @property
    def is_creating(self):
        return not isinstance(self.option, alternative.Option)

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
        if not self.edit_warning_show_check.get_active() or \
                self.edit_warning.run() != Gtk.ResponseType.CANCEL:
            return f(self, *args, **kwargs)
    return wrapper


icontheme = Gtk.IconTheme.get_default()
STATUS_ICONS = []
for icon_name in ('dialog-ok', 'dialog-error'):
    try:
        STATUS_ICONS.append(icontheme.load_icon(icon_name, 8, 0))
    except GLib.Error:
        STATUS_ICONS.append(None)
STATUS_ICONS.append(None)
del icontheme


class MainWindow(object):
    delay_mode = False
    group_cleaning = False
    group_filter_pattern = ''

    def __init__(self, app, paths={}, group=None):
        '''Load alternative database and fetch objects from the builder.'''
        self.paths = paths
        self.group = alternative.Group(group, create=True) if group else None
        self.use_polkit = app.use_polkit if app else \
            os.getuid() and bool(shutil.which('pkexec'))

        # glade XML
        self.builder = Gtk.Builder.new_from_file(
            get_data_path('glade/galternatives.glade'))
        for widget_id in {
            # main window
            'main_window', 'main_accelgroup',
            'pending_box', 'groups_tv',
            'group_find_btn', 'group_find_entry', 'groups_tv_filter',
            'group_icon', 'alternative_label',
            'link_label', 'description_label',
            'status_switch', 'options_tv', 'options_column_package',
            'options_menu',
            # dialogs and messages
            'preferences_dialog',
            'edit_warning', 'edit_warning_show_check',
            'confirm_closing', 'commit_failed', 'results_tv'
        }:
            setattr(self, widget_id, self.builder.get_object(widget_id))
        self.main_window.set_application(app)
        self.main_window.set_icon_from_file(LOGO_PATH)
        self.main_window.main_instance = self

        # save placeholder text strings
        self.empty_group = \
            alternative.Group(self.alternative_label.get_text(), create=True)
        self.empty_group[self.empty_group.name] = self.link_label.get_text()
        self.empty_group.description = self.description_label.get_text()
        self.empty_group._current = False

        # signals
        self.builder.connect_signals(self)
        # actions
        self.options_menu.insert_action_group('win', self.main_window)
        self.actions = {}
        for name, activate in {
            ('preferences', lambda *args: self.preferences_dialog.show()),
            ('quit', self.on_quit),
            ('group.add', self.add_group),
            ('group.edit', self.edit_group),
            ('group.remove', self.remove_group),
            ('group.find', self.find_group),
            ('option.add', self.add_option),
            ('option.edit', self.edit_option),
            ('option.remove', self.remove_option),
            ('change.save', self.on_save),
            ('change.reload', self.load_db),
        }:
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.main_window.add_action(action)
            self.actions[name] = action
        for name in {'delay_mode', 'query_package', 'use_polkit'}:
            action = Gio.SimpleAction.new_stateful(
                name, None, GLib.Variant('b', getattr(self, name)))

            def on_action_toggle_func(name):
                def on_action_toggle(action, value):
                    action.set_state(value)
                    setattr(self, name, value.get_boolean())

                return on_action_toggle

            action.connect('change-state', on_action_toggle_func(name))
            self.main_window.add_action(action)
        # workaround https://stackoverflow.com/questions/19657017
        self.builder.get_object('group_add_btn').get_child().add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Insert'), Gtk.AccelFlags.VISIBLE)
        self.builder.get_object('group_edit_btn').get_child().add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Return'), Gtk.AccelFlags.VISIBLE)
        self.builder.get_object('group_remove_btn').get_child().add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Delete'), Gtk.AccelFlags.VISIBLE)
        self.group_find_btn.get_child().add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('<Control>f'), Gtk.AccelFlags.VISIBLE)
        # model filter
        self.groups_tv_filter.set_visible_func(self.group_filter)

        self.load_db()

    hide_on_delete = staticmethod(hide_on_delete)
    reset_dialog = staticmethod(reset_dialog)

    def show(self):
        '''Show the main window. Pretend itself as Gtk.Window.'''
        # Correct the display name.
        # Ref: https://stackoverflow.com/questions/9324163/
        # how-to-set-application-title-in-gnome-shell
        self.main_window.set_wmclass(INFO['program_name'], PACKAGE)
        return self.main_window.show()

    def destroy(self):
        return self.main_window.destroy()

    @property
    def has_unsaved(self):
        '''Whether there are unsaved changes'''
        return self.pending_box.get_visible()

    # config actions begin #

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
        self.main_window.set_sensitive(False)
        threading.Thread(target=lambda: GObject.idle_add(
            self.do_save_callback, diff_cmds, autosave, *self.alt_db.commit(
                diff_cmds,
                'pkexec' if self.use_polkit else None))
        ).start()

    def do_save_callback(self, diff_cmds, autosave, returncode, results):
        self.main_window.set_sensitive(True)
        if returncode:
            # failed
            model = self.results_tv.get_model()
            model.clear()
            for cmd, result in zip_longest(friendlize(diff_cmds), results):
                it = model.append(None, (
                    STATUS_ICONS[result.returncode != 0 if result else 2],
                    cmd[0]))
                for info in cmd[1:]:
                    model.append(it, (
                        None, '    ' + info))
                if result:
                    model.append(it, (
                        None, '  ' + _('Run command: ') + ' '.join(result.cmd)))
                    out = result.out.rstrip()
                    if out:
                        model.append(it, (None, '  ' + out))
                    err = result.err.rstrip()
                    if err:
                        model.append(it, (None, '  ' + err))
            self.commit_failed.show_all()

        if not returncode and not autosave:
            # succeeded and other fields may also be changed, flush the gui
            self.load_db()
        else:
            # succeeded and only `current' changed, do a quick save
            # or failed, keep everything
            self.alt_db_old = alternative.Alternative(**self.paths)
            self.on_change()

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

    def find_group(self, widget, data):
        if self.group_find_btn.get_active():
            self.group_find_entry.show()
            self.group_find_entry.grab_focus()
        else:
            self.group_find_entry.hide()
            self.group_find_entry.set_text('')

    def on_group_find_entry_changed(self, widget):
        self.group_filter_pattern = widget.get_text()
        self.group_cleaning = True
        self.groups_tv_filter.refilter()
        self.group_cleaning = False
        self.click_group()

    def on_group_find_entry_key_release_event(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.group_find_btn.set_active(False)
            self.find_group(None, None)

    def group_filter(self, model, iter, data):
        return self.group_filter_pattern in model[iter][0]

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
        # load alternative group into groups_tv
        treeview = self.groups_tv
        selection = treeview.get_selection()
        modelfilter = treeview.get_model()
        model = modelfilter.get_model()

        self.group_cleaning = True
        model.clear()
        if self.group_find_btn.get_active():
            self.group_find_btn.set_active(False)
        self.group_cleaning = False

        next_group = None
        for group_name in sorted(self.alt_db):
            it = model.append((group_name, ))
            if self.group and self.group.name == group_name:
                # clear self.group first to prevent same-tab reloading problem
                self.group = None
                path = model.get_path(it)
                treeview.set_cursor(path)
                # by this time self.group has been changed
                # disable this code block
                next_group = self.group
                self.group = None
        self.group = next_group

        if self.group is None:
            # disable edit/remove buttons
            self.actions['group.edit'].set_enabled(False)
            self.actions['group.remove'].set_enabled(False)
            # clear options_tv
            self.group = self.empty_group
            self.load_options()
            self.description_label.set_text(self.empty_group.description)
            self.group = None

    def click_group(self, widget=None):
        '''Load options for selected alternative group into options_tv.'''
        if self.group_cleaning:
            return
        if widget is None:
            widget = self.groups_tv.get_selection()
        model, it = widget.get_selected()
        if it is None:
            if self.group:
                for row in model:
                    if row[0] == self.group.name:
                        it = row.iter
                        path = model.get_path(it)
                        self.group_cleaning = True
                        self.groups_tv.set_cursor(path)
                        self.group_cleaning = False
                        break
            return
        group = self.alt_db[model.get_value(it, 0)]
        if group == self.group:
            return

        # enable buttons
        if not self.group:
            self.actions['group.edit'].set_enabled(True)
            self.actions['group.remove'].set_enabled(True)
        # save current group
        self.group = group
        self.load_options()

    def load_options(self):
        if self.group is None:
            return

        # set the name of the alternative to the information area
        name, description, icon = altname_description(self.group.name)
        self.alternative_label.set_text(name)
        self.link_label.set_text(self.group.link)
        self.description_label.set_text(description)
        self.group_icon.set_from_icon_name(
            icon, self.group_icon.get_icon_name()[1])
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
            self.actions['option.edit'].set_enabled(pthinfo)
            self.actions['option.remove'].set_enabled(pthinfo)
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
    def __init__(self, **kwargs):
        kwargs.update(INFO)
        if 'license_type' in kwargs and isinstance(kwargs['license_type'], str):
            if hasattr(Gtk.License, kwargs['license_type']):
                kwargs['license_type'] = \
                    getattr(Gtk.License, kwargs['license_type'])
            else:
                logger.warn("`license_type' incorrect!")
        super(AboutDialog, self).__init__(
            logo=LOGO_PATH and GdkPixbuf.Pixbuf.new_from_file_at_scale(
                LOGO_PATH, xdg.Config.icon_size, -1, True),
            translator_credits=_('translator_credits'),
            **kwargs)
        self.connect('response', hide_on_delete)
        self.connect('delete-event', hide_on_delete)
