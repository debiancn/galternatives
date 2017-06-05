from __future__ import absolute_import

from . import logger, _
from .appdata import DESC_DIR

import locale
import sys
import os


DEFAULT_DESCRIPTION = _('No description')

# read friendly description from .desktop,
# although most of them are not available
if sys.version_info >= (3,):
    import configparser

    def altname_description(name, locale=locale.getdefaultlocale()[0]):
        desc_file = os.path.join(DESC_DIR, '{}.desktop'.format(name))
        config = configparser.ConfigParser()
        # this func call also read the config file!
        if desc_file in config.read(desc_file):
            section = config['Desktop Entry']
            return (
                section.get('Name[{}]'.format(locale)) or
                section.get('Name') or
                name,
                section.get('Comment[{}]'.format(locale)) or
                section.get('Comment') or
                DEFAULT_DESCRIPTION
            )
        return (name, DEFAULT_DESCRIPTION)
else:
    import ConfigParser

    def altname_description(name, locale=locale.getdefaultlocale()[0]):
        desc_file = os.path.join(DESC_DIR, '{}.desktop'.format(name))
        config = ConfigParser.RawConfigParser()
        config.read(desc_file)
        #print config
        if desc_file in config.read(desc_file):
            return (
                config.has_option(
                    'Desktop Entry', 'Name[{}]'.format(locale)) and
                config.get('Desktop Entry', 'Name[{}]'.format(locale)) or
                config.has_option('Desktop Entry', 'Name') and
                config.get('Desktop Entry', 'Name') or
                name,
                config.has_option(
                    'Desktop Entry', 'Comment[{}]'.format(locale)) and
                config.get('Desktop Entry', 'Comment[{}]'.format(locale)) or
                config.has_option('Desktop Entry', 'Comment') and
                config.get('Desktop Entry', 'Comment') or
                DEFAULT_DESCRIPTION,
            )
        return (name, DEFAULT_DESCRIPTION)
