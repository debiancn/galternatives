from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement, print_function

import pygtk
pygtk.require ('2.0')
import gtk, gobject
from gtk import glade

from . import logger
import sys, os, gettext

from .alternative import Alternative
from .appdata import PACKAGE, GLADE_PATH, ABOUT_IMAGE_PATH

_ = gettext.gettext

UPDATE_ALTERNATIVES = '/usr/bin/update-alternatives'


def gtk_main_quit (*args):
    gtk.main_quit ()


class GAlternatives:
    ALTERNATIVES = 0

    CHOICE = 0
    PRIORITY = 1
    OPTIONS = 2

    SLAVENAME = 0
    SLAVEPATH = 1

    def __init__ (self):
        gettext.bindtextdomain (PACKAGE)
        gettext.textdomain (PACKAGE)
        glade.bindtextdomain(PACKAGE)
        glade.textdomain (PACKAGE)

        locale = os.getenv ('LC_MESSAGES')

        if not locale:
            locale = os.getenv ('LC_ALL')
            if not locale:
                locale = os.getenv ('LANG', 'C')

        try:
            self.locale = locale[:locale.index ('.')]
        except ValueError:
            self.locale = locale

        logger.debug('SL: %s - L: %s' % (self.locale, locale))

        self.gui = glade.XML (GLADE_PATH)
        self.gui.signal_autoconnect (globals ())

        self.main_window = self.gui.get_widget ('main_window')

        # menus / about / credits
        self.about_window = self.gui.get_widget ('about_window')
        self.about_window.connect ('delete-event', self.close_about_window_cb)

        self.about_image = self.gui.get_widget ('about_image')
        self.about_image.set_from_file (ABOUT_IMAGE_PATH)

        self.about_mitem = self.gui.get_widget ('about_mitem')
        self.about_mitem.connect ('activate', self.show_about_window_cb)

        self.credits_button = self.gui.get_widget ('credits_button')
        self.credits_button.connect ('clicked', self.show_credits_window_cb)

        self.about_close_button = self.gui.get_widget ('about_close_button')
        self.about_close_button.connect ('clicked', self.close_about_window_cb)

        self.credits_window = self.gui.get_widget ('credits_window')
        self.credits_window.connect ('delete-event', self.close_credits_window_cb)

        translator_label = self.gui.get_widget ('translator_label')
        if translator_label.get_text () == 'translator_credits':
            translator_label.set_text (_('Unknown/None'))

        self.credits_close_button = self.gui.get_widget ('credits_close_button')
        self.credits_close_button.connect ('clicked', self.close_credits_window_cb)

        # alternatives treeview
        self.alternatives_tv = self.gui.get_widget ('alternatives_tv')
        self.alternatives_model = gtk.TreeStore (gobject.TYPE_STRING)
        self.alternatives_tv.set_model (self.alternatives_model)
        self.set_alternatives_columns ()

        self.alternatives_selection = self.alternatives_tv.get_selection ()
        self.alternatives_selection.connect ('changed',
                                             self.alternative_selected_cb)


        self.status_menu = self.gui.get_widget ('status_menu')
        self.status_changed_signal = self.status_menu.connect ('changed', self.status_changed_cb)

        self.update_alternatives ()

        # tree for options for each alternative
        self.options_tv = self.gui.get_widget ('options_tv')
        self.options_model = gtk.TreeStore (gobject.TYPE_BOOLEAN,
                                            gobject.TYPE_INT,
                                            gobject.TYPE_STRING)
        self.options_model.set_sort_column_id (self.PRIORITY,
                                               gtk.SORT_DESCENDING)

        self.options_tv.set_model (self.options_model)
        self.set_options_columns ()

        self.opt_add_button = self.gui.get_widget ('opt_add_button')
        self.opt_add_button.connect ('clicked', self.show_add_opt_window_cb)

        self.opt_properties_button = self.gui.get_widget ('opt_properties_button')
        self.opt_properties_button.connect ('clicked', self.show_details_cb)

        self.opt_remove_button = self.gui.get_widget ('opt_remove_button')
        self.opt_remove_button.connect ('clicked', self.remove_option_cb)

        # add option window
        self.add_opt_window = self.gui.get_widget ('add_opt_window')
        self.add_opt_window.connect ('delete-event', self.hide_add_opt_window_cb)
        self.add_opt_entry = self.gui.get_widget ('add_opt_entry')
        self.add_opt_spin = self.gui.get_widget ('add_opt_spin')

        self.file_selector = self.gui.get_widget ('file_selector')
        self.filesel_ok = self.gui.get_widget ('filesel_ok')
        self.filesel_ok.connect ('clicked', self.close_filesel_cb)
        self.filesel_cancel = self.gui.get_widget ('filesel_cancel')
        self.filesel_cancel.connect ('clicked', self.close_filesel_cb)

        self.browse_opt_button = self.gui.get_widget ('browse_opt_button')
        self.browse_opt_button.connect ('clicked', self.choose_opt_cb)

        self.add_opt_cancel = self.gui.get_widget ('add_opt_cancel')
        self.add_opt_cancel.connect ('clicked', self.hide_add_opt_window_cb)

        self.add_opt_ok = self.gui.get_widget ('add_opt_ok')
        self.add_opt_ok.connect ('clicked', self.add_option_cb)

        # details window
        self.details_window = self.gui.get_widget ('details_window')
        self.details_window.connect ('delete_event', self.hide_details_cb)

        # tree for slaves for each option
        self.slaves_tv = self.gui.get_widget ('slaves_tv')
        self.slaves_model = gtk.TreeStore (gobject.TYPE_STRING,
                                           gobject.TYPE_STRING)
        self.slaves_tv.set_model (self.slaves_model)
        self.set_slaves_columns ()

        # selects the first alternative on the list
        iter = self.alternatives_model.get_iter_first ()
        if iter != None:
            self.alternatives_selection.select_iter (iter)

    def mainloop (self):
        gtk.main ()

    def refresh_ui (self):
        while gtk.events_pending ():
            gtk.main_iteration_do (False)

    def set_alternatives_columns (self):
        cell_renderer = gtk.CellRendererText ()
        column = gtk.TreeViewColumn (_('Alternatives'), cell_renderer,
                                     text=self.ALTERNATIVES)
        self.alternatives_tv.append_column (column)

    def option_choice_toggled_cb (self, cr, path):
        iter = self.options_model.get_iter_from_string (path)
        current_status = self.options_model.get_value (iter,
                                                       self.CHOICE)
        if current_status:
            return

        self.set_alternative_option (iter)

    def show_add_opt_window_cb (self, *args):
# FIXME: need to finish this part of the window
#        for slave in self.altslaves:
#            label = gtk.Label ()
#            label.set_text ('%s (%s)' % (slave['name'], slave['link']))
#            self.add_opt_window.vbox.pack_start (label, 1, 1, 0)
#
#            entry


        self.add_opt_window.show_all ()


    def hide_add_opt_window_cb (self, *args):
        self.add_opt_window.hide ()
        self.add_opt_entry.set_text ('')
        self.add_opt_entry.grab_focus ()

    def add_option_cb (self, *args):
        alt = self.alternative
        unixname = alt.name
        link = alt.link

        path = self.add_opt_entry.get_text ()
        logger.debug('I should be adding %s to the %s alternative here...' %\
                     (path, self.alternative))

        if os.path.exists (path):
            s = os.stat (path)
        else:
            msg = _('The file or directory you selected does not exist.\n'
                    'Please select a valid one.')
            dialog = gtk.MessageDialog (self.main_window,
                                        gtk.DIALOG_MODAL,
                                        gtk.MESSAGE_ERROR,
                                        gtk.BUTTONS_CLOSE,
                                        msg)
            result = dialog.run ()
            dialog.destroy ()
            return

        priority = self.add_opt_spin.get_value ()

        cmd = '%s --install %s %s %s %d > /dev/null 2>&1' % (UPDATE_ALTERNATIVES, link, unixname, path, priority)
        result = os.system (cmd)

        logger.debug(cmd)
        logger.debug('Result: %d' % (result))

        self.hide_add_opt_window_cb (self)

        self.update_metainfo ()
        self.update_options_tree ()

    def choose_opt_cb (self, *args):
        self.file_selector.show_now ()
        gtk.main ()

        filename = self.file_selector.get_filename ()
        if filename != '':
            self.add_opt_entry.set_text (filename)
        self.file_selector.set_filename ('')
        logger.debug('File selected: %s' % (filename))

    def close_filesel_cb (self, *args):
        self.file_selector.hide ()
        if gtk.main_level () > 1:
            gtk.main_quit ()

    def remove_option_cb (self, *args):
        alt = self.alternative
        selection = self.options_tv.get_selection ()

        unixname = alt.name
        tm, iter = selection.get_selected ()
        option = self.options_model.get_value (iter, self.OPTIONS)

        if self.ask_for_confirmation (_('Are you sure you want to remove this option?')):
            cmd = '%s --remove %s %s > /dev/null 2>&1' % (UPDATE_ALTERNATIVES, unixname, option)
            result = os.system (cmd)
            logger.debug(cmd)
            logger.debug('Result: %d' % (result))

            self.update_metainfo ()
            self.update_options_tree ()

    def ask_for_confirmation (self, msg):
        dialog = gtk.MessageDialog (self.main_window,
                                    gtk.DIALOG_MODAL,
                                    gtk.MESSAGE_QUESTION,
                                    gtk.BUTTONS_YES_NO,
                                    msg)
        result = dialog.run ()
        dialog.destroy ()

        if result == gtk.RESPONSE_YES:
            return True
        else:
            return False

    def set_alternative_option (self, iter):
        alt = self.alternative
        unixname = alt.name
        option = self.options_model.get_value (iter, self.OPTIONS)

        cmd = '%s --set %s %s  > /dev/null 2>&1' % (UPDATE_ALTERNATIVES, unixname, option)
        result = os.system (cmd)

        logger.debug(cmd)
        logger.debug('Result: %d' % (result))

        def deactivate (model, path, iter):
            if self.options_model.get_value (iter, self.CHOICE):
                self.options_model.set (iter,
                                        self.CHOICE,
                                        False)
        self.options_model.foreach (deactivate)

        self.options_model.set (iter,
                                self.CHOICE,
                                False)

        # refresh the GUI, to get the new situation
        self.update_metainfo ()
        self.update_options_tree ()

    def set_options_columns (self):
        """
        set_options_columns ()

        Sets up the columns for the Options list for the currently
        selected alternative.
        """

        self.options_tv.set_reorderable (True)

        cell_renderer = gtk.CellRendererToggle ()
        cell_renderer.set_radio (True)
        cell_renderer.connect ('toggled', self.option_choice_toggled_cb)
        column = gtk.TreeViewColumn (_('Choice'), cell_renderer,
                                     active=self.CHOICE)
        column.set_fixed_width (50)
        self.options_tv.append_column (column)

        cell_renderer = gtk.CellRendererText ()
        cell_renderer.set_property ('xalign', 0.9)
        column = gtk.TreeViewColumn (_('Priority'), cell_renderer,
                                     text=self.PRIORITY)
        column.set_sort_order (gtk.SORT_DESCENDING)
        column.set_sort_indicator (True)
        column.set_sort_column_id (self.PRIORITY)
        column.set_fixed_width (50)
        self.options_tv.append_column (column)

        cell_renderer = gtk.CellRendererText ()
        column = gtk.TreeViewColumn (_('Options'), cell_renderer,
                                     text=self.OPTIONS)
        self.options_tv.append_column (column)

    def set_slaves_columns (self):
        cell_renderer = gtk.CellRendererText ()
        column = gtk.TreeViewColumn (_('Name'), cell_renderer,
                                     text=self.SLAVENAME)
        self.slaves_tv.append_column (column)

        cell_renderer = gtk.CellRendererText ()
        column = gtk.TreeViewColumn (_('Slave'), cell_renderer,
                                     text=self.SLAVEPATH)
        self.slaves_tv.append_column (column)

    def update_alternatives (self, directory='/var/lib/dpkg/alternatives/'):
        self.alternatives_model.clear ()
        alternatives = os.listdir (directory)
        alternatives.sort ()

        for alternative in alternatives:
            iter = self.alternatives_model.append (None)
            self.alternatives_model.set (iter, self.ALTERNATIVES,
                                         alternative)

    def alternative_selected_cb (self, selection):
        # feels faster ;)
        self.refresh_ui ()

        self.update_metainfo ()
        self.update_options_tree ()


    def status_changed_cb (self, *args):
        alt = self.alternative
        selection = self.options_tv.get_selection ()

        self.refresh_ui ()

        option = self.status_menu.get_history ()
        if option == 0:
            alt.option_status = 'auto'
            os.system ('%s --auto %s  > /dev/null 2>&1' % (UPDATE_ALTERNATIVES, alt.name))
        else:
            alt.option_status = 'manual'
            tm, iter = selection.get_selected ()
            self.set_alternative_option (iter)

        self.update_metainfo ()
        self.update_options_tree ()

    def update_options_tree (self):
        alt = self.alternative
        selection = self.options_tv.get_selection ()

        self.options_model.clear ()

        for option in alt.options:
            if option['path'] == alt.current_option:
                is_chosen = True
            else:
                is_chosen = False

            iter = self.options_model.append (None)
            self.options_model.set (iter,
                                    self.CHOICE, is_chosen,
                                    self.PRIORITY, int(option['priority']),
                                    self.OPTIONS, option['path'])

        # selects the first alternative on the list
        iter = self.options_model.get_iter_first ()
        if iter != None:
            selection.select_iter (iter)

    def option_get_selected (self):
        selection = self.options_tv.get_selection ()
        tm, iter = selection.get_selected ()
        if iter == None:
            return

        return tm.get_value (iter, self.OPTIONS)

    def show_details_cb (self, data):
        self.update_slaves_tree ()
        self.details_window.show_all ()

    def hide_details_cb (self, *args):
        self.details_window.hide ()

    def show_about_window_cb (self, *args):
        self.about_window.show_all ()

    def close_about_window_cb (self, *args):
        self.about_window.hide ()

    def show_credits_window_cb (self, *args):
        self.credits_window.show_all ()

    def close_credits_window_cb (self, *args):
        self.credits_window.hide ()

    def options_find_path_in_list (self, path):
        alt = self.alternative

        for option in alt.options:
            if option['path'] == path:
                return option
        return None

    def update_slaves_tree (self):
        option = self.option_get_selected ()
        self.slaves_model.clear ()

        option = self.options_find_path_in_list (option)
        for slave in option['slaves']:
            iter = self.slaves_model.append (None)
            self.slaves_model.set (iter,
                                   self.SLAVENAME, slave['name'],
                                   self.SLAVEPATH, slave['path'])

    def update_metainfo (self):
        selection = self.alternatives_tv.get_selection ()
        tm, iter = selection.get_selected ()

        self.alternative = Alternative (tm.get_value (iter, self.ALTERNATIVES))
        alt = self.alternative

        alternative_label = self.gui.get_widget ('alternative_label')
        description_label = self.gui.get_widget ('description_label')
        status_menu = self.gui.get_widget ('status_menu')

        # feedback!
        self.refresh_ui ()

        # set the name of the alternative to the information area
        alternative_label.set_markup ('<span size="xx-large" weight="bold">%s</span>\n[ %s ]' % \
                                      (alt.name, alt.link))
        description_label.set_text (alt.description)

        # need to block this signal, or the status_menu change will
        # undo my changes
        self.status_menu.handler_block (self.status_changed_signal)
        if alt.option_status == 'auto':
            status_menu.set_history (0)
        else:
            status_menu.set_history (1)
        self.status_menu.handler_unblock (self.status_changed_signal)


def main():
    if os.getuid ():
        if os.access ('/usr/bin/gksu', os.X_OK):
            sys.exit (os.system ('/usr/bin/gksu -t "%s" -m "%s" -u root %s' %
                                 (_('Running Alternatives Configurator...'),
                                  _('<b>I need your root password to run\n'
                                    'the Alternatives Configurator.</b>'),
                                  sys.argv[0])))
        else:
            dialog = gtk.MessageDialog (None, gtk.DIALOG_DESTROY_WITH_PARENT,
                                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE)
            dialog.set_markup (_('<b>This program should be run as root and /usr/bin/gksu is not available.</b>\n\n'
                                 'I am unable to request the password myself without gksu. Unless you have '
                                 'modified your system to explicitly allow your normal user to modify '
                                 'the alternatives system, GAlternatives will not work.'))
            dialog.run ()
            dialog.destroy ()

    DEBUG = False
    try:
        if sys.argv[1] == '--debug':
            DEBUG = True
    except IndexError:
        pass

    galternatives = GAlternatives ()

    logger.debug(_('Testing galternatives...'))

    gtk.main ()
