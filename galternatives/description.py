from __future__ import absolute_import

from . import logger, _
from .appdata import *

import locale
import subprocess
import sys
import os


__all__ = ['altname_description', 'query_pkg', 'friendlize']

DESC_DIR = locate_appdata(PATHS['appdata'], 'descriptions', True)
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


def query_pkg(filename):
    p = subprocess.Popen(('dpkg', '-S', filename), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if not out:
        return
    if p.returncode:
        raise RuntimeError("`dpkg' returned with code {}".format(p.returncode))
    return out.split(': ')[0]


def friendlize(commands):
    for cmd in commands:
        type_ = cmd[0]
        if type_ == 'install':
            yield _("Install option `{2}' for group `{1}'").format(*cmd)  # XXX
        elif type_ == 'auto':
            yield _("Set group `{1}' in auto mode").format(*cmd)
        elif type_ == 'set':
            yield _("Set group `{1}' in manual mode, pointed to `{2}'").format(*cmd)
        elif type_ == 'remove':
            yield _("Remove option `{2}' for group `{1}'").format(*cmd)
        elif type_ == 'remove-all':
            yield _("Remove group `{1}'").format(*cmd)
