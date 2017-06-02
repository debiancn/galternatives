from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement, print_function

from . import logger
from .appdata import PACKAGE, DESC_DIR

import os
import gettext
import sys

if sys.version_info >= (3,):
    import configparser
else:
    import ConfigParser
    configparser = None

_ = gettext.gettext


ALT_DB_DIR = '/var/lib/dpkg/alternatives'
ALT_LINK_DIR = '/etc/alternatives'


class Alternative:
    default_description = _('No description')

    def __init__(self, name, locale='C'):
        alt_filepath = os.path.join(ALT_DB_DIR, name)
        if not os.path.isfile(alt_filepath):
            raise KeyError('No such alternative name')

        self.description = self.default_description
        self.name = name

        # read friendly description from .desktop,
        # although most of them are not available
        desc_file = os.path.join(DESC_DIR, '{}.desktop'.format(name))
        # this func call also read the config file!
        if configparser:
            config = configparser.ConfigParser()
            if desc_file in config.read(desc_file):
                section = config['Desktop Entry']
                self.description = \
                    section.get('Comment[{}]'.format(locale)) or \
                    section.get('Comment') or \
                    self.default_description
                self.name = \
                    section.get('Name[{}]'.format(locale)) or \
                    section.get('Name') or \
                    name
        else:
            config = ConfigParser.RawConfigParser()
            if desc_file in config.read(desc_file):
                self.description = \
                    config.has_option('Desktop Entry', 'Comment[{}]'.format(locale)) and \
                    config.get('Desktop Entry', 'Comment[{}]'.format(locale)) or \
                    config.has_option('Desktop Entry', 'Comment') and \
                    config.get('Desktop Entry', 'Comment') or \
                    self.default_description
                self.name = \
                    config.has_option('Desktop Entry', 'Name[{}]'.format(locale)) and \
                    config.get('Desktop Entry', 'Name[{}]'.format(locale)) or \
                    config.has_option('Desktop Entry', 'Name') and \
                    config.get('Desktop Entry', 'Name') or \
                    name


        # now get the real information!
        with open(alt_filepath) as altfile:
            # parsing file
            self.option_status = altfile.readline().strip()
            logger.debug('The Status is: %s' % (self.option_status))

            self.link = altfile.readline().strip()
            logger.debug('The link is: %s' % (self.link))

            # find out what are the slaves used by this alternative
            # we need that to know how many slaves to expect from each
            # alternative
            self.slaves = []
            while True:
                line = altfile.readline().strip()
                if line == '':
                    break
                self.slaves.append({
                    'name': line,
                    'link': altfile.readline().strip()
                })

            self.current_option = os.readlink(os.path.join(ALT_LINK_DIR, name))
            logger.debug('Link currently points to: %s' % (self.current_option))

            self.options = []
            while True:
                line = altfile.readline().strip()
                if line == '':
                    break

                self.options.append({
                    'path': line,
                    'priority': altfile.readline().strip(),
                    'slaves': [
                        {
                            'name': slave['name'],
                            'path': altfile.readline().strip()
                        } for slave in self.slaves
                    ]
                })
            logger.debug(self.options)
