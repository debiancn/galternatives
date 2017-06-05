from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement

from . import logger, _
from .appdata import PACKAGE, DESC_DIR
from .config import options

import locale
import os
import sys

if sys.version_info >= (3,):
    import configparser
else:
    import ConfigParser
    configparser = None


class Alternative:
    default_description = _('No description')

    def __init__(self, name, locale=locale.getdefaultlocale()[0]):
        # property names come from update-alternatives(1)
        alt_filepath = os.path.join(options['altdir'], name)
        if not os.path.isfile(alt_filepath):
            raise KeyError('No such alternative name')

        self.description = self.default_description
        self.name = name

        # read friendly description from .desktop,
        # although most of them are not available
        desc_file = os.path.join(DESC_DIR, '{}.desktop'.format(name))
        if configparser:
            config = configparser.ConfigParser()
            # this func call also read the config file!
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

        # parse alt file
        with open(alt_filepath) as altfile:
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

            self.current_option = os.readlink(os.path.join(options['admindir'], name))
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
