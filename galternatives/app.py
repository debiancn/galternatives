from copy import deepcopy
from gettext import gettext
from gi.repository import GdkPixbuf, Gdk, Gio, GLib, Gtk, GObject
from itertools import zip_longest
import os
import shutil
import sys
import threading
import traceback
from typing import TYPE_CHECKING, Any, Callable, Iterable, TypeVar, cast

if TYPE_CHECKING:
    from _typeshed import SupportsKeysAndGetItem

try:
    from xdg.Config import icon_size
except ImportError:
    icon_size = 48

if TYPE_CHECKING:
    _T = TypeVar('_T')
    _U = TypeVar('_U')

    type DictInit[_T, _U] = (
        Iterable[tuple[_T, _U]] | SupportsKeysAndGetItem[_T, _U])


from . import logger, APPID, INFO, PACKAGE
from .alternative import AltDB, AltGroup, AltOption, CommandResult
from .appdata import LOGO_PATH, get_data_path
from .description import altname_desc, query_package, describe_cmds
try:
    from .log import setColoredLogger
except ImportError:
    setColoredLogger = None


_ = gettext


GObject.threads_init()


def hide_on_delete(window: Gtk.Window, *args: Any) -> bool:
    """
    Warpper for Gtk.Widget.hide_on_delete, but allow superfluous arguments.
    Used for signal callback.
    """
    return Gtk.Widget.hide_on_delete(window)


def reset_dialog(dialog: Gtk.Dialog, *args: Any) -> None:
    """
    Select cancel button as default when reshow the dialog. Used for signal
    callback.
    """
    btn_cancel = \
        dialog.get_widget_for_response(Gtk.ResponseType.CANCEL) or \
        dialog.get_widget_for_response(Gtk.ResponseType.CLOSE)
    if btn_cancel is None:
        return

    btn_cancel.grab_focus()
    btn_cancel.grab_default()


class Taglike:
    def get_text(self) -> str: ...
    def set_text(self, text: str) -> None: ...

    def set_icon_from_icon_name(
        self, icon_pos: Gtk.EntryIconPosition, icon_name: str | None = None
    ) -> None: ...


class TagWidget(Gtk.Widget, Taglike):
    ...


@Gtk.Template.from_file(get_data_path('glade/file_entry.glade', False, True))
class FileEntry(Gtk.Box, Taglike):
    __gtype_name__ = 'FileEntry'
    entry: Gtk.Entry = Gtk.Template.Child('entry')

    @Gtk.Template.Callback('open_file')
    def open_file(self, button: Gtk.Button) -> None:
        """Select a file and fill the entry with the path."""
        file_chooser = Gtk.FileChooserDialog(
            title=_('Select File'), action=Gtk.FileChooserAction.OPEN,
            parent=button.get_toplevel(), buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        if file_chooser.run() == Gtk.ResponseType.OK:
            filename = file_chooser.get_filename()
            if filename is not None:
                self.entry.set_text(filename)
        file_chooser.destroy()

    def set_text(self, text: str) -> None:
        return self.entry.set_text(text)

    def get_text(self) -> str:
        return self.entry.get_text()

    def set_icon_from_icon_name(
            self, icon_pos: Gtk.EntryIconPosition,
            icon_name: str | None = None) -> None:
        return self.entry.set_icon_from_icon_name(icon_pos, icon_name)

    def connect(
            self, detailed_signal: str | GObject.Signal,
            handler: Callable[..., Any], *args: Any) -> int:
        def wrapper(*args: Any) -> Any:
            return handler(self, *args[1:])

        return self.entry.connect(detailed_signal, wrapper)


@Gtk.Template.from_file(get_data_path('glade/edit_dialog.glade', False, True))
class EditDialog(Gtk.Dialog):
    __gtype_name__ = 'EditDialog'
    requires: Gtk.Grid = Gtk.Template.Child('requires')
    slaves_tv: Gtk.TreeView = Gtk.Template.Child('slaves_tv')
    slave_fields: Gtk.Box = Gtk.Template.Child('slave_fields')
    slaves_edit: Gtk.Box = Gtk.Template.Child('slaves_edit')
    new_group_warning: Gtk.Box = Gtk.Template.Child('new_group_warning')

    REQUIRES: list[tuple[str, type[TagWidget]]]
    SLAVES: list[tuple[str, type[TagWidget]]]

    main_instance: 'MainWindow'
    requires_widgets: list[TagWidget]
    slaves_widgets: list[TagWidget]
    slaves_ls: Gtk.ListStore
    slave_it: Gtk.TreeIter | None = None

    @property
    def is_creating(self) -> bool: ...

    def on_close(self, window: Gtk.Window, event: Gdk.Event) -> None: ...

    def _init_edit_dialog(self) -> None:
        self.requires_widgets = []
        for i, (label_name, widget_class) in enumerate(self.REQUIRES):
            widget = widget_class()
            widget.set_hexpand(True)
            self.requires_widgets.append(widget)
            self.requires.attach(Gtk.Label(label=label_name), 0, i, 1, 1)
            self.requires.attach(widget, 1, i, 1, 1)
        self.requires.show_all()

        self.slaves_widgets = []
        for i, (label_name, widget_class) in enumerate(self.SLAVES):
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
            self.slaves_widgets.append(widget)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.pack_start(Gtk.Label(label=label_name), False, False, 0)
            box.pack_start(widget, True, True, 0)
            self.slave_fields.pack_start(box, False, False, 0)
        self.slave_fields.show_all()
        self.slaves_ls = Gtk.ListStore(*[str] * (len(self.SLAVES) * 2))
        self.slaves_tv.set_model(self.slaves_ls)

    def __new__(cls, *args, **kwargs):
        if cls == EditDialog:
            return super().__new__(cls, *args, **kwargs)

        self = EditDialog(**kwargs)
        self.__class__ = cls
        EditDialog._init_edit_dialog(self)
        return self

    @property
    def main_window(self) -> Gtk.ApplicationWindow:
        return cast(Gtk.ApplicationWindow, self.get_transient_for())

    @Gtk.Template.Callback('add_row')
    def add_row(self, button: Gtk.Button) -> None:
        new_row: list[str | None] = [None] * (len(self.SLAVES) * 2)
        new_row[0] = '<new>'
        self.slaves_ls.append(new_row)

    @Gtk.Template.Callback('remove_row')
    def remove_row(self, button: Gtk.Button) -> None:
        ls, it = self.slaves_tv.get_selection().get_selected()
        if it is not None:
            del ls[it]
        if len(ls) > 0:
            # on_click_slave and on_slave_fields_changed will be called
            return
        # on_click_slave will not be called, clear fields
        for slave in self.slaves_widgets:
            slave.set_text('')

    @Gtk.Template.Callback('on_click_slave')
    def on_click_slave(self, widget: Gtk.TreeSelection) -> None:
        ls, it = widget.get_selected()
        self.slave_it = it
        if it is None:
            return
        for slave, text in zip_longest(self.slaves_widgets, ls[it][::2]):
            slave.set_text(text or '')

    def on_slave_fields_changed(self, widget: TagWidget) -> None:
        if self.slave_it is None:
            return
        self.slaves_ls[self.slave_it][2 * widget.i_column] = \
            widget.get_text()

    @Gtk.Template.Callback('on_response')
    def on_response(self, window: Gtk.Window, response_id: int) -> None:
        # only bind to cancel button
        # dialog response can not be cancelled, thus not suitable for validation
        if response_id == Gtk.ResponseType.CANCEL:
            # do not emit delete-event
            self.destroy()

    @Gtk.Template.Callback('close')
    def close(self, *args: Any) -> None:
        return super().close()

    @Gtk.Template.Callback('on_delete_event')
    def on_delete_event(
            self, window: Gtk.Window, event: Gdk.Event) -> bool | None:
        validated = True
        empty = True
        for widget in self.requires_widgets:
            if not widget.get_text():
                self.requires_set_vaild(widget, False)
                validated = False
            else:
                self.requires_set_vaild(widget, True)
                empty = False
        for row in self.slaves_ls:
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
    def requires_set_vaild(widget: Taglike, status: bool) -> None:
        widget.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, None if status else 'dialog-error')


class GroupDialog(EditDialog):
    group: AltGroup | None

    REQUIRES = [
        (_('Name'), Gtk.Entry),
        (_('Link'), FileEntry),
    ]
    SLAVES = REQUIRES

    _name: Gtk.Entry
    _link: FileEntry

    def __init__(
            self, main_instance: 'MainWindow', group: AltGroup | None = None,
            *args: Any, **kwargs: Any) -> None:
        self.main_instance = main_instance
        self.group = group

        self._name = self.requires_widgets[0]
        self._link = self.requires_widgets[1]

        if self.group is None:
            self.set_title(_('Add group'))
            self.new_group_warning.show()
        else:
            self.set_title(_('Edit group - {}').format(self.group.name))
            self._name.set_text(self.group.name)
            self._link.set_text(self.group.link)
            for slave_name in self.group[1:]:
                self.slaves_ls.append((
                    slave_name, None, self.group[slave_name], None))

    @property
    def is_creating(self) -> bool:
        return self.group is None

    def on_close(self, window: Gtk.Window, event: Gdk.Event) -> None:
        name = self._name.get_text()
        reload_groups = False
        slaves_diff: dict[str, str] = {}

        if self.group is None:
            self.group = AltGroup(name, create=True)
            self.main_instance.db.add(self.group)
            reload_groups = True
        elif name != self.group.name:
            slaves_diff[self.group.name] = name
            self.main_instance.db.move(self.group.name, name)
            reload_groups = True
        self.group.link = self._link.get_text()

        slaves: set[str] = set()
        for i, row in enumerate(self.slaves_ls):
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

        if reload_groups:
            self.main_instance.load_groups()
        else:
            self.main_instance.load_options()
        self.main_instance.on_change()


class OptionDialog(EditDialog):
    group: AltGroup
    option: AltOption | None

    REQUIRES = [
        (_('Path'), FileEntry),
        (_('Priority'), Gtk.SpinButton),
    ]
    SLAVES = [
        (_('Name'), Gtk.Entry),
        (_('Path'), FileEntry),
    ]

    _path: FileEntry
    _priority: Gtk.SpinButton

    def __init__(
            self, main_instance: 'MainWindow', group: AltGroup,
            option: AltOption | None = None, *args: Any, **kwargs: Any) -> None:
        self.main_instance = main_instance
        self.group = group
        self.option = option

        self._path = self.requires_widgets[0]
        self._priority = self.requires_widgets[1]

        self.slaves_edit.hide()
        self._priority.set_adjustment(
            Gtk.Adjustment(0, -(1 << 31), 1 << 31, 1, 10, 0))
        if self.option is None:
            self.set_title(_('Add option'))
            self._priority.set_value(0)
            for slave_name in self.group[1:]:
                self.slaves_ls.append([slave_name, None, None, None])
        else:
            self.set_title(
                _('Edit option - {}').format(self.option[self.group.name]))
            self._path.set_text(self.option[self.group.name])
            self._priority.set_value(self.option.priority)
            for slave_name in self.group[1:]:
                self.slaves_ls.append([
                    slave_name, None, self.option[slave_name], None])

    @property
    def is_creating(self) -> bool:
        return self.option is None

    def on_close(self, window: Gtk.Window, event: Gdk.Event) -> None:
        if self.option is None:
            self.option = AltOption()
            self.group.options.append(self.option)
        for row in self.slaves_ls:
            if row[2]:
                self.option[row[0]] = row[2]
            elif row[0] in self.option:
                del self.option[row[0]]
        path = self._path.get_text()
        self.option[self.group.name] = path
        self.option.priority = self._priority.get_value_as_int()
        self.main_instance.load_options()
        self.main_instance.on_change()


icontheme = Gtk.IconTheme.get_default()
STATUS_ICONS: list[GdkPixbuf.Pixbuf | None] = []
icon = None
for icon_name in ('dialog-ok', 'dialog-error'):
    try:
        icon = icontheme.load_icon(icon_name, 8, 0)
    except GLib.Error:
        icon = None
    STATUS_ICONS.append(icon)
STATUS_ICONS.append(None)
del icon
del icontheme


class MainWindow:
    altdb_paths: dict[str, str]

    db: AltDB
    db_orig: AltDB
    group: AltGroup | None
    option: AltOption | None

    debug: int
    use_polkit: bool
    delay_mode: bool
    group_cleaning: bool
    group_filter_pattern: str

    _query_package: bool

    builder: Gtk.Builder

    main_window: Gtk.ApplicationWindow
    main_accelgroup: Gtk.AccelGroup
    pending_box: Gtk.Box
    groups_tv: Gtk.TreeView
    group_find_btn: Gtk.ToggleToolButton
    group_find_entry: Gtk.Entry
    groups_tv_filter: Gtk.TreeModelFilter
    group_icon: Gtk.Image
    alternative_label: Gtk.Label
    link_label: Gtk.Label
    description_label: Gtk.Label
    status_switch: Gtk.Switch
    options_tv: Gtk.TreeView
    options_column_package: Gtk.TreeViewColumn
    options_menu: Gtk.Menu

    preferences_dialog: Gtk.Dialog
    edit_warning: Gtk.MessageDialog
    edit_warning_show_check: Gtk.CheckButton
    confirm_closing: Gtk.MessageDialog
    commit_failed: Gtk.MessageDialog
    results_tv: Gtk.TreeView

    empty_group: AltGroup
    actions: dict[str, Gio.SimpleAction]

    def __init__(
            self, app: 'GAlternativesApp',
            paths: 'DictInit[str, str] | None' = None,
            group: str | None = None) -> None:
        """Load alternative database and fetch objects from the builder."""
        self.altdb_paths = dict(paths) if paths else {}
        self.group = AltGroup(group, create=True) if group else None
        self.option = None

        self.debug = app.debug
        self.use_polkit = app.use_polkit if app else bool(
            os.getuid() and shutil.which('pkexec'))
        self.delay_mode = False
        self.group_cleaning = False
        self.group_filter_pattern = ''
        self._query_package = False

        # glade XML
        self.builder = Gtk.Builder.new_from_file(get_data_path(
            'glade/galternatives.glade', False, True))
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
        if LOGO_PATH:
            self.main_window.set_icon_from_file(LOGO_PATH)

        # save placeholder text strings
        self.empty_group = \
            AltGroup(self.alternative_label.get_text(), create=True)
        self.empty_group[self.empty_group.name] = self.link_label.get_text()
        self.empty_group.desc = self.description_label.get_text()

        # signals
        self.builder.connect_signals(self)
        # actions
        self.options_menu.insert_action_group('win', self.main_window)
        self.actions = {}
        actions: list[tuple[str, Callable[..., Any]]] = [
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
        ]
        for name, activate in actions:
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.main_window.add_action(action)
            self.actions[name] = action
        for name in {'delay_mode', 'query_package', 'use_polkit'}:
            action = Gio.SimpleAction.new_stateful(
                name, None, GLib.Variant('b', getattr(self, name)))

            def on_action_toggle_func(name: str):
                def on_action_toggle(
                        action: Gio.SimpleAction, value: GLib.Variant):
                    action.set_state(value)
                    setattr(self, name, value.get_boolean())

                return on_action_toggle

            action.connect('change-state', on_action_toggle_func(name))
            self.main_window.add_action(action)
        # workaround https://stackoverflow.com/questions/19657017
        toolbtn = cast(
            Gtk.ToolButton, self.builder.get_object('group_add_btn'))
        cast(Gtk.Button, toolbtn.get_child()).add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Insert'), Gtk.AccelFlags.VISIBLE)
        toolbtn = cast(
            Gtk.ToolButton, self.builder.get_object('group_edit_btn'))
        cast(Gtk.Button, toolbtn.get_child()).add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Return'), Gtk.AccelFlags.VISIBLE)
        toolbtn = cast(
            Gtk.ToolButton, self.builder.get_object('group_remove_btn'))
        cast(Gtk.Button, toolbtn.get_child()).add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('Delete'), Gtk.AccelFlags.VISIBLE)
        cast(Gtk.Button, self.group_find_btn.get_child()).add_accelerator(
            'clicked', self.main_accelgroup,
            *Gtk.accelerator_parse('<Control>f'), Gtk.AccelFlags.VISIBLE)
        # model filter
        self.groups_tv_filter.set_visible_func(self.group_filter)

    hide_on_delete = staticmethod(hide_on_delete)
    reset_dialog = staticmethod(reset_dialog)

    def show(self):
        """Show the main window. Pretend itself as Gtk.Window."""
        # Correct the display name.
        # Ref: https://stackoverflow.com/questions/9324163/
        # how-to-set-application-title-in-gnome-shell
        self.main_window.set_wmclass(cast(str, INFO['program_name']), PACKAGE)
        return self.main_window.show()

    def destroy(self):
        return self.main_window.destroy()

    @property
    def has_unsaved(self):
        """Whether there are unsaved changes"""
        return self.pending_box.get_visible()

    # config actions begin #

    @property
    def query_package(self):
        return self._query_package

    @query_package.setter
    def query_package(self, value: bool) -> bool:
        if value == self._query_package:
            return value
        self._query_package = value

        self.options_column_package.set_visible(value)
        if value:
            self.load_options_pkgname()
        return value

    def load_config(self, widget: Gtk.Widget) -> None:
        for option in AltDB.PATH_NAMES:
            filebtn = cast(Gtk.FileChooserButton,
                           self.builder.get_object(option + '_chooser'))
            filebtn.set_filename(getattr(self.db, option))

    def on_preferences_dialog_response(
            self, widget: Gtk.Widget, response_id: int) -> None:
        self.altdb_paths.clear()
        reload = False
        for option in AltDB.PATH_NAMES:
            filebtn = cast(Gtk.FileChooserButton,
                           self.builder.get_object(option + '_chooser'))
            path = cast(str, filebtn.get_filename())
            self.altdb_paths[option] = path
            if getattr(self.db, option) != path:
                reload = True

        if reload:
            self.load_db()

    def confirm_advanced(self)-> bool:
        return (
            not self.edit_warning_show_check.get_active() or
            self.edit_warning.run() != Gtk.ResponseType.CANCEL)

    # config actions end #

    # commit actions begin #

    def on_quit(self, *args: Any) -> bool:
        """Check for unsaved changes before quitting."""
        if self.has_unsaved:
            response_id = self.confirm_closing.run()
            if response_id == Gtk.ResponseType.CANCEL:
                return True
            if response_id == Gtk.ResponseType.NO:
                self.do_quit()
                return False
            if response_id == Gtk.ResponseType.YES:
                self.do_save()
                return self.has_unsaved
        self.do_quit()
        return False

    def do_quit(self, *args: Any) -> None:
        """Close the main window."""
        self.main_window.destroy()

    def on_save(self, *args: Any) -> None:
        self.do_save()

    def do_save(
            self, cmds: list[list[str]] | None = None,
            autosave: bool = False) -> None:
        """Save changes."""
        if cmds is None:
            cmds = list(self.db.compare(self.db_orig))
        self.main_window.set_sensitive(False)
        if self.debug > 1:
            logger.debug(
                'submit commands %s%s', cmds,
                ' via polkit' if self.use_polkit else '')
        threading.Thread(target=lambda: GObject.idle_add(
            self.do_save_callback, cmds, autosave, *self.db.commit(
                cmds, 'pkexec' if self.use_polkit else None))).start()

    def do_save_callback(
            self, cmds: list[list[str]], autosave: bool, returncode: int,
            results: list[CommandResult]) -> None:
        self.main_window.set_sensitive(True)
        if returncode:
            # failed
            ts = self.results_tv.get_model()
            if ts is None:
                raise RuntimeError
            ts = cast(Gtk.TreeStore, ts)
            ts.clear()
            for cmd, result in zip_longest(
                    describe_cmds(cmds), results, fillvalue=None):
                if cmd is None:
                    raise RuntimeError
                it = ts.append(None, [
                    STATUS_ICONS[result.returncode != 0 if result else 2],
                    cmd[0]])
                for info in cmd[1:]:
                    ts.append(it, [None, '    ' + info])
                if result:
                    ts.append(it, [
                        None, '  ' + _('Run command: ') + ' '.join(result.cmd)])
                    out = result.out.rstrip()
                    if out:
                        ts.append(it, [None, '  ' + out])
                    err = result.err.rstrip()
                    if err:
                        ts.append(it, [None, '  ' + err])
            self.commit_failed.show_all()

        if not returncode and not autosave:
            # succeeded and other fields may also be changed, flush GUI
            self.load_db()
        else:
            # succeeded and only `current' changed, do a quick save
            # or failed, keep everything
            self.db_orig = AltDB(**self.altdb_paths)
            self.on_change()

    def save_and_quit(self, *args: Any, **kwargs: Any) -> None:
        self.do_save()
        self.do_quit()

    def load_db(self, *args: Any) -> None:
        self.db = AltDB(**self.altdb_paths)
        self.db_orig = deepcopy(self.db)
        self.pending_box.hide()
        self.load_groups()

    # commit actions end #

    # detail windows actions begin #
    # TODO: windows need a good way for handling (group destruction)

    def add_group(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        self.show_group_window(None)

    def edit_group(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        self.show_group_window(self.group)

    def remove_group(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        if not self.group:
            raise RuntimeError
        del self.db[self.group.name]
        self.load_groups()
        self.on_change()

    def show_group_window(self, group: AltGroup | None) -> None:
        window = GroupDialog(self, group, transient_for=self.main_window)
        window.present()

    def find_group(self, widget: Gtk.Widget, data: Any) -> None:
        if self.group_find_btn.get_active():
            self.group_find_entry.show()
            self.group_find_entry.grab_focus()
        else:
            self.group_find_entry.hide()
            self.group_find_entry.set_text('')

    def on_group_find_entry_changed(self, widget: Gtk.Entry) -> None:
        self.group_filter_pattern = widget.get_text()
        self.group_cleaning = True
        self.groups_tv_filter.refilter()
        self.group_cleaning = False
        self.click_group()

    def on_group_find_entry_key_release_event(
            self, widget: Gtk.Entry, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.group_find_btn.set_active(False)
            self.find_group(widget, None)

    def group_filter(
            self, model: Gtk.TreeModelFilter, iter: Gtk.TreeIter,
            data: Any) -> bool:
        return self.group_filter_pattern in model[iter][0]

    def add_option(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        if not self.group:
            raise RuntimeError
        self.show_option_window(self.group, None)

    def edit_option(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        if not self.group:
            raise RuntimeError
        self.show_option_window(self.group, self.option)

    def remove_option(self, widget: Gio.Action, data: Any) -> None:
        if not self.confirm_advanced():
            return

        self.load_options()
        self.on_change()

    def show_option_window(self, group: AltGroup, option: AltOption | None) -> None:
        window = OptionDialog(
            self, group, option, transient_for=self.main_window)
        window.present()

    # detail windows actions end #

    # main window actions begin #

    def load_groups(self) -> None:
        # load alternative group into groups_tv
        tv_filter = self.groups_tv.get_model()
        if tv_filter is None:
            raise RuntimeError
        tv_filter = cast(Gtk.TreeModelFilter, tv_filter)
        ls = cast(Gtk.ListStore, tv_filter.get_model())

        self.group_cleaning = True
        ls.clear()
        if self.group_find_btn.get_active():
            self.group_find_btn.set_active(False)
        self.group_cleaning = False

        next_group = None
        for group_name in sorted(self.db):
            it = ls.append((group_name, ))
            if self.group and self.group.name == group_name:
                # clear self.group first to prevent same-tab reloading problem
                self.group = None
                path = ls.get_path(it)
                self.groups_tv.set_cursor(path)
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
            if self.empty_group.desc is None:
                raise RuntimeError
            self.description_label.set_text(self.empty_group.desc)
            self.group = None

    def click_group(self, widget: Gtk.TreeSelection | None = None) -> None:
        """Load options for selected alternative group into options_tv."""
        if self.group_cleaning:
            return
        if widget is None:
            widget = self.groups_tv.get_selection()
        ls, it = widget.get_selected()
        if it is None:
            if self.group:
                for row in ls:
                    if row[0] == self.group.name:
                        it = row.iter
                        path = ls.get_path(it)
                        self.group_cleaning = True
                        self.groups_tv.set_cursor(path)
                        self.group_cleaning = False
                        break
            return
        group = self.db[ls.get_value(it, 0)]
        if group == self.group:
            return

        # enable buttons
        if self.group is None:
            self.actions['group.edit'].set_enabled(True)
            self.actions['group.remove'].set_enabled(True)
        # save current group
        self.group = group
        self.load_options()

    def load_options(self) -> None:
        if self.group is None:
            return

        # set the name of the alternative to the information area
        name, description, icon = altname_desc(self.group.name)
        self.alternative_label.set_text(name)
        self.link_label.set_text(self.group.link)
        self.description_label.set_text(description)
        self.group_icon.set_from_icon_name(
            icon, self.group_icon.get_icon_name()[1])
        self.status_switch.set_active(self.group.is_auto)

        # set columns
        column = self.options_tv.get_column(1)
        if column is None:
            raise RuntimeError
        column.set_title(self.group.name)
        for i in range(4, self.options_tv.get_n_columns()):
            column = self.options_tv.get_column(4)
            if column is None:
                raise RuntimeError
            self.options_tv.remove_column(column)
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
                *option.list_paths(self.group)
            ))
        if self.query_package:
            self.load_options_pkgname()

    def load_options_pkgname(self) -> None:
        model = self.options_tv.get_model()
        if model is None:
            raise RuntimeError
        for record in model:
            if record[2]:
                break
            record[2] = query_package(record[3])

    def load_options_current(self) -> None:
        model = self.options_tv.get_model()
        if model is None:
            raise RuntimeError

        def set_current(
                model: Gtk.ListStore, path: Gtk.TreePath,
                it: Gtk.TreeIter) -> bool:
            if self.group is None:
                raise RuntimeError
            model.set(it, 0, self.group.current == self.group.options[path[0]])
            return False

        model.foreach(set_current)

    def change_status(
            self, widget: Gtk.Switch, gparam: GObject.ParamSpecBoolean) -> None:
        """
        Handle click on status_switch.

        When current status is auto, it will block the click action.
        """
        widget.set_sensitive(not widget.get_active())
        if widget.get_active():
            self.select_option()

    def click_option(self, widget: Gtk.CellRendererToggle, path: str) -> None:
        """Handle click on radio buttons of options."""
        self.select_option(int(path))

    def select_option(self, index: int | None = None) -> None:
        if self.group is None:
            return
        if index is None:
            if self.group.is_auto:
                return
        else:
            if not self.group.is_auto and \
                    self.group.current == self.group.options[index]:
                return

        self.group.select(index)
        self.load_options_current()
        self.status_switch.set_active(self.group.is_auto)
        self.on_change(not self.delay_mode)

    def on_options_tv_button_press_event(
            self, treeview: Gtk.TreeView, event: Gdk.EventButton) -> None:
        if event.button == 3 and self.group:
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            self.option = pthinfo and self.group.options[pthinfo[0][0]]
            pthinfo = bool(pthinfo)
            self.actions['option.edit'].set_enabled(pthinfo)
            self.actions['option.remove'].set_enabled(pthinfo)
            self.options_menu.popup(
                None, None, None, None, event.button, event.time)

    def on_change(self, autosave: bool = False) -> None:
        cmds = list(self.db.compare(self.db_orig))
        if autosave and len(cmds) == 1:
            self.do_save(cmds, autosave=True)
            return
        if cmds:
            self.pending_box.show()
        else:
            self.pending_box.hide()

    # main window actions end #


class AboutDialog(Gtk.AboutDialog):
    """About dialog of the application."""

    def __init__(self, **kwargs) -> None:
        kwargs.update(INFO)
        if 'license_type' in kwargs and isinstance(kwargs['license_type'], str):
            if hasattr(Gtk.License, kwargs['license_type']):
                kwargs['license_type'] = \
                    getattr(Gtk.License, kwargs['license_type'])
            else:
                logger.warning("`license_type' incorrect!")

        logo = \
            None if LOGO_PATH is None else \
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                LOGO_PATH, icon_size, -1, True)
        super().__init__(
# TRANSLATORS: Your name <Your email address> here!
            logo=logo, translator_credits=_('translator_credits'), **kwargs)

        self.connect('response', hide_on_delete)
        self.connect('delete-event', hide_on_delete)


class GAlternativesApp(Gtk.Application):
    use_polkit: bool
    target_group: str | None
    debug: int
    altdb_paths: dict[str, str]

    _window: MainWindow | None
    _about_dialog: AboutDialog | None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args, application_id=APPID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE, **kwargs)
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

        self.use_polkit = False
        self.target_group = None
        self.debug = 0
        self.altdb_paths = {}

        self._window = None
        self._about_dialog = None

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        if not self.debug:
            self.debug = int(options.contains('debug'))
        if setColoredLogger:
            setColoredLogger(logger, self.debug > 0)
            logger.debug(_('Testing galternatives...'))

        # GtkBuilder will error out if the version requirements are not met.
        # No need to check it again.

        if os.getuid():
            # not root
            if options.contains('normal'):
                logger.warning(_(
                    'No root privileges detected, but continuing anyway'))
            elif shutil.which('pkexec'):
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

        for option in AltDB.PATH_NAMES:
            value = options.lookup_value(option)
            if value is not None:
                self.altdb_paths[option] = \
                    value.get_bytestring().rstrip(b'\0').decode()

        return -1

    def do_local_command_line(
            self, arguments: list[str]) -> tuple[bool, list[str], int]:
        self.debug = 0
        for arg in arguments:
            if arg.startswith('-dd'):
                self.debug = 2
                break
        return Gtk.Application.do_local_command_line(self, arguments)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = command_line.get_arguments()
        if len(args) > 2:
            print(_('Error: Specifying more than one group is not allowed'),
                  file=sys.stderr)
            return 2

        self._window = MainWindow(self, self.altdb_paths, self.target_group)
        try:
            self._window.load_db()
        except:
            print(traceback.format_exc())
            self._window.destroy()
            return 1

        if len(args) > 1:
            self.target_group = args[1]
            if self.target_group not in self._window.db:
                print(_('Error: No such group "{}"').format(self.target_group),
                      file=sys.stderr)
                self._window.destroy()
                return 1

        self._about_dialog = AboutDialog(
            transient_for=self._window.main_window)
        self.activate()
        return 0

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        menu = cast(Gio.MenuModel, Gtk.Builder.new_from_file(get_data_path(
            'glade/menubar.ui', False, True)).get_object('menu'))
        self.set_app_menu(menu)

        # Cannot use add_action_entries()
        # see https://bugzilla.gnome.org/show_bug.cgi?id=678655
        for name, activate in {
            'about': self.on_about,
        }.items():
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.add_action(action)

    def do_activate(self) -> None:
        if self._window is None:
            raise RuntimeError
        if self.debug > 1:
            self._window.edit_warning_show_check.set_active(False)
        self._window.show()

    def on_about(self, action: Gio.SimpleAction, param: Any) -> None:
        if self._about_dialog is None:
            raise RuntimeError
        self._about_dialog.present()
