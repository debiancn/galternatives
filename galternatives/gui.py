from __future__ import absolute_import

from . import logger, _, PACKAGE, INFO
from .alternative import Alternative
from .appdata import *
from .description import *

from copy import deepcopy
from collections import defaultdict
import os
from weakref import WeakKeyDictionary
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio
from gi.repository import Gtk
try:
    from gi.repository import GdkPixbuf
except ImportError:
    logger.warn('GdkPixbuf not available, cannot show icon in about dialog.')
    GdkPixbuf = None
# TODO: Polkit? (require service registration)
gi.require_version('Polkit', '1.0')
try:
    from gi.repository import Polkit
except ImportError:
    logger.warn('Polkit not available, in-program root access not available.')
    Polkit = None

import sys
if sys.version_info < (3,):
    range = xrange


###s common actions begin ###
def hide_on_delete(window, *args):
    '''warpper for Gtk.Widget.hide_on_delete, but allow superfluous arguments'''
    return Gtk.Widget.hide_on_delete(window)


def reset_dialog(dialog, *args):
    '''select cancel button as default when re-show the dialog'''
    btn_cancel = \
        dialog.get_widget_for_response(Gtk.ResponseType.CANCEL) or \
        dialog.get_widget_for_response(Gtk.ResponseType.CLOSE)
    btn_cancel.grab_focus()
    btn_cancel.grab_default()


def open_file(button, *args):
    '''select a file and fill the entry with the path'''
    file_chooser = Gtk.FileChooserDialog(
        title=_('Select File'), action=Gtk.FileChooserAction.OPEN,
        parent=button.get_toplevel(), buttons=(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    if file_chooser.run() == Gtk.ResponseType.OK:
        button.get_parent().foreach(lambda widget:
            isinstance(widget, Gtk.Entry) and
            widget.set_text(file_chooser.get_filename()))
    file_chooser.destroy()
### common actions end ###


class GAlternativesWindow:
    group = None
    option_index = None

    def __init__(self, app):
        '''load alternative database and fetch objects from the builder'''
        self.alt_db = Alternative()
        self.alt_db_old = deepcopy(self.alt_db)

        # load glade XML file
        self.builder = Gtk.Builder.new_from_file(locate_appdata(
            PATHS['appdata'], 'glade/galternatives.glade'))

        # main window
        self.main_window = self.builder.get_object('main_window')
        self.main_window.set_application(app)

        self.pending_box = self.builder.get_object('pending_box')

        self.alternative_label = self.builder.get_object('alternative_label')
        self.link_label = self.builder.get_object('link_label')
        self.description_label = self.builder.get_object('description_label')

        self.status_switch = self.builder.get_object('status_switch')
        self.options_tv = self.builder.get_object('options_tv')
        self.options_menu = self.builder.get_object('options_menu')
        self.options_menu.insert_action_group('win', self.main_window)
        self.option_edit_item = self.builder.get_object('option_edit_item')
        self.option_remove_item = self.builder.get_object('option_remove_item')
        self.option_add_item = self.builder.get_object('option_add_item')

        # dialogs and messages
        self.preferences_dialog = self.builder.get_object('preferences_dialog')

        self.edit_warning = self.builder.get_object('edit_warning')
        self.adding_problem = self.builder.get_object('adding_problem')
        self.confirm_closing = self.builder.get_object('confirm_closing')
        self.confirm_commit = self.builder.get_object('confirm_commit')

        self.commit_failed = self.builder.get_object('commit_failed')
        self.results_tv = self.builder.get_object('results_tv')

        self.group_glade = locate_appdata(PATHS['appdata'], 'glade/group.glade')
        self.option_glade = locate_appdata(PATHS['appdata'], 'glade/option.glade')

        self.group_windows = {}
        self.option_windows = defaultdict(dict)

        # actions and signals
        for name, activate in {
            'preferences': lambda *args: self.preferences_dialog.show(),
            'quit': self.on_quit,
            'group.add': self.add_group,
            'group.edit': self.edit_group,
            'group.remove': self.remove_group,
            'option.add': self.add_option,
            'option.edit': self.edit_option,
            'option.remove': self.remove_option,
            'change.save': self.on_save,
            'change.reload': self.do_reload,
        }.items():
            action = Gio.SimpleAction(name=name)
            action.connect('activate', activate)
            self.main_window.add_action(action)

        self.builder.connect_signals({
            # common
            'hide_on_delete': hide_on_delete,
            'reset_dialog': reset_dialog,
            'open_file': open_file,
            # config
            'reload_config': self.reload_config,
            'on_editable_check_toggled': self.on_editable_check_toggled,
            'on_config_changed': self.on_config_changed,
            # commit
            'on_quit': self.on_quit,
            'save_and_quit': lambda *args: self.save() or self.do_quit(),
            'do_quit': self.do_quit,
            'get_pending_commands': self.get_pending_commands,
            # main window
            'update_groups': self.update_groups,
            'update_options': self.update_options,
            'change_status': self.change_status,
            'select_option': self.select_option,
            'on_options_tv_button_press_event': self.on_options_tv_button_press_event,
        })

    def show(self):
        '''pretend itself as Gtk.Window'''
        self.main_window.show()

    ### config actions begin ###
    # TODO: allow config file? (may pollute user's home)
    def reload_config(self, widget):
        '''reload config when showing preference dialog'''
        for options in ('altdir', 'admindir', 'log'):
            self.builder.get_object(options + '_chooser').set_filename(getattr(self.alt_db, options))

    def on_editable_check_toggled(self, widget):
        '''show warning when enabling edit feature'''
        if widget.get_active():
            # set buttons for edit_warning dialog
            self.edit_warning.get_widget_for_response(Gtk.ResponseType.OK).show()
            self.edit_warning.get_widget_for_response(Gtk.ResponseType.YES).hide()
            self.edit_warning.get_widget_for_response(Gtk.ResponseType.NO).hide()
            if self.edit_warning.run() == Gtk.ResponseType.CANCEL:
                widget.set_active(False)

    def on_config_changed(self, widget):
        '''auto save config change'''
        # TODO: save config?
        print(Gtk.Buildable.get_name(widget), widget.get_active())
    ### config actions end ###

    ### commit actions begin ###
    def on_quit(self, *args):
        '''check for unsaved changes before quitting'''
        if self.pending_box.get_visible():  # TODO: change not save
            response_id = self.confirm_closing.run()
            if response_id == Gtk.ResponseType.CANCEL:
                return True
            if response_id == Gtk.ResponseType.NO:
                return self.do_quit()
            if response_id == Gtk.ResponseType.YES:
                self.do_save()
                return self.pending_box.get_visible()
        self.do_quit()

    def do_quit(self, *args):
        '''close the window'''
        self.main_window.destroy()

    def on_save(self, *args):
        if self.confirm_commit.run() == Gtk.ResponseType.OK:
            self.do_save()

    def do_save(self):
        '''save changes'''
        # improve: neat way to reuse differential commands
        if self.commands is None:
            logger.warn('No commands supplied')
            self.commands = self.alt_db.compare(self.alt_db_old)
        results = self.alt_db.commit(self.commands)
        if results:
            model = self.results_tv.get_model()
            model.clear()
            for cmd, out in zip(friendlize(self.commands), results):
                model.set(model.append(None), 1, cmd)
                model.set(model.append(None), 1, out[2])
            self.commit_failed.run()
            self.alt_db_old = Alternative()
            self.on_change()
        else:
            self.alt_db_old = deepcopy(self.alt_db)
        self.commands = None

    def do_reload(self, *args):
        self.alt_db = deepcopy(self.alt_db_old)
        self.pending_box.hide()
        # TODO: flush all widgets

    def get_pending_commands(self, widget):
        commands = self.alt_db.compare(self.alt_db_old)
        self.commands = commands
        model = widget.get_model()
        model.clear()
        for friend_cmd in friendlize(commands):
            model.set(model.append(None), 0, friend_cmd)
    ### commit actions end ###

    ### detail windows actions begin ###
    # TODO: windows need a good way for handling (group destruction)
    def add_group(self, widget, data):
        if self.adding_problem.run() == Gtk.ResponseType.OK:
            self.show_group_window()

    def edit_group(self, widget, data):
        if self.confirm_editable():
            self.show_group_window(self.group)

    def remove_group(self, widget, data):
        if self.confirm_editable():
            if self.group in self.group_windows:
                self.group_windows[self.group].destory()
            if self.group in self.option_windows:
                for win in self.option_windows[self.group].values():
                    win.destory()

    def show_group_window(self, group=None):
        if group and group in self.group_windows:
            window = self.group_windows[group]
        else:
            builder = Gtk.Builder.new_from_file(self.group_glade)
            builder.connect_signals({
                'open_file': open_file,
                'on_group_window_close': self.on_group_window_close,
            })
            window = builder.get_object('group_window')
            window.set_title(
                _('Edit group - {}').format(group.name) if group
                else _('Add group'))
            window.group = group
        if group and group not in self.group_windows:
            self.group_windows[group] = window
        window.present()
        # TODO: make window selected

    def on_group_window_close(self, window, event):
        print(window.group)

    def add_option(self, widget, data):
        if self.adding_problem.run() == Gtk.ResponseType.OK:
            self.show_option_window(self.group)

    def edit_option(self, widget, data):
        if self.confirm_editable():
            self.show_option_window(self.group, option)

    def remove_option(self, widget, data):
        if self.confirm_editable():
            if self.group in self.group_windows:
                self.option_windows[self.group][self.option].destory()

    def show_option_window(self, group, option=None):
        if option and option in self.option_windows[group]:
            window = self.option_windows[group][option]
        else:
            builder = Gtk.Builder.new_from_file(self.option_glade)
            builder.connect_signals({
                'open_file': open_file,
                'on_option_window_close': self.on_option_window_close,
            })
            window = builder.get_object('group_window')
            window.set_transient_for(self.main_window)
            window.set_title(
                _('Edit option - {}').format(option[group.name]) if option
                else _('Add option'))
            window.option = option
        if option and option not in self.option_windows[group]:
            self.option_windows[group][option] = window
        window.present()

    def on_option_window_close(self, window, event):
        print(window.option)

    def confirm_editable(self):
        '''show warning dialog before editing or removing group'''
        self.edit_warning.get_widget_for_response(Gtk.ResponseType.OK).hide()
        self.edit_warning.get_widget_for_response(Gtk.ResponseType.YES).show()
        self.edit_warning.get_widget_for_response(Gtk.ResponseType.NO).show()
        return self.edit_warning.run() != Gtk.ResponseType.CANCEL
    ### detail windows actions end ###

    ### main window actions begin ###
    def update_groups(self, widget):
        '''load alternative group into groups_tv when startup'''
        # widget = self.groups_tv
        model = widget.get_model()
        model.clear()
        for alternative in sorted(self.alt_db):
            model.set(model.append(None), 0, alternative)

    def update_options(self, widget):
        '''load options for selected alternative group into options_tv'''
        # save current group
        # widget = self.groups_tv.get_selection()
        groups_model, groups_it = widget.get_selected()
        group = self.alt_db[groups_model.get_value(groups_it, 0)]

        # enable buttons
        if not self.group:
            self.builder.get_object('group_edit_btn').set_sensitive(True)
            self.builder.get_object('group_remove_btn').set_sensitive(True)
        self.group = group

        # set the name of the alternative to the information area
        name, description = altname_description(group.name)
        self.alternative_label.set_text(name)
        self.link_label.set_text(group.link)
        self.description_label.set_text(description)
        self.status_switch.block = True
        self.status_switch.set_active(group.status)
        self.status_switch.set_sensitive(not group.status)
        self.status_switch.block = False

        # set columns
        self.options_tv.get_column(1).set_title(group.name)
        for i in range(3, self.options_tv.get_n_columns()):
            self.options_tv.remove_column(self.options_tv.get_column(3))
        for i in range(1, len(group)):
            self.options_tv.append_column(Gtk.TreeViewColumn(group[i], Gtk.CellRendererText(), text=i + 2))

        options_model = Gtk.ListStore(bool, str, int, *(str for i in range(1, len(group))))
        self.options_tv.set_model(options_model)
        for option in group.options:
            it = options_model.append(None)
            options_model.set(
                it,
                0, option == group.current,
                1, option[group.name],
                2, option.priority
            )
            for i in range(1, len(group)):
                options_model.set(it, i + 2, option[group[i]])

    def change_status(self, widget, gparam):
        '''handle click on status_switch
        When current status is auto, it will block the click action.'''
        if widget.block:
            return
        assert not self.group.status
        assert widget.get_active()
        self.group.select()
        self.options_tv.get_model().foreach(lambda model, path, it:
            model.set(it, 0, self.group.current == self.group.options[path[0]]))
        widget.set_sensitive(False)
        self.on_change(True)

    def select_option(self, widget, path):
        '''handle click on radio buttons of options'''
        index = int(path)
        if self.group.current == self.group.options[index]:
            return
        self.group.select(index)
        model = self.options_tv.get_model()
        model.foreach(lambda model, path, it:
            model.get(it, 0)[0] and (model.set(it, 0, False) or True))
        model.set(model.iter_nth_child(None, index), 0, True)
        self.status_switch.block = True
        self.status_switch.set_active(False)
        self.status_switch.set_sensitive(True)
        self.status_switch.block = False
        self.on_change(True)

    def on_options_tv_button_press_event(self, treeview, event):
        if event.button == 3:
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo:
                self.option_index = pthinfo[0][0]
                self.option_edit_item.set_sensitive(True)
                self.option_remove_item.set_sensitive(True)
                self.option_add_item.set_sensitive(bool(self.group))
                self.options_menu.popup(None, None, None, None, event.button, event.time)

    def on_change(self, autosave=False):
        commands = self.alt_db.compare(self.alt_db_old)
        self.commands = commands
        if autosave and len(commands) == 1:
            self.do_save()
            return
        if commands:
            self.pending_box.show()
        else:
            self.pending_box.hide()
    ### main window actions end ###


class GAlternativesAbout(Gtk.AboutDialog):
    def __init__(self, *args, **kwargs):
        kwargs.update(INFO)
        super(Gtk.AboutDialog, self).__init__(
            logo=GdkPixbuf and GdkPixbuf.Pixbuf.new_from_file(
                locate_appdata(PATHS['icon'], 'galternatives.png')),
            translator_credits=_('translator_credits'),
            **kwargs)
        self.connect('response', hide_on_delete)
        self.connect('delete-event', hide_on_delete)
