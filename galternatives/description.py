'''
Give readable information for various internal objects.

Attributes:
    DESC_DIR (str): Directory path where descriptions for alternative groups
        are stores.
    DEFAULT_DESCRIPTION (str): Placeholder when no description is found.

'''
from __future__ import absolute_import

from . import logger, _
from .appdata import *

import locale
import subprocess
import sys
import os


__all__ = ['altname_description', 'query_package', 'friendlize']


DESC_DIR = get_data_path('descriptions', True)
DEFAULT_DESCRIPTION = _('No description')
DEFAULT_ICON = 'dialog-question'


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
                DEFAULT_DESCRIPTION,
                section.get('Icon') or
                DEFAULT_ICON,
            )
        return (name, DEFAULT_DESCRIPTION, DEFAULT_ICON)
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
                config.has_option('Desktop Entry', 'Icon') and
                config.get('Desktop Entry', 'Icon') or
                DEFAULT_ICON,
            )
        return (name, DEFAULT_DESCRIPTION, DEFAULT_ICON)

altname_description.__doc__ = '''
Find readable group name and its description for given alternative group
name.

It will try to find proper translated strings, then the untranslated
name and description. If both failed, the original name will be
returned, along with a placeholder 'No description' as its description.

Args:
    name (str): Name of the group.
    locale (str, optional): Preferred locale. Default to current
        environment locale.

Returns:
    Tuple[str, str]: Readable group name and its description.

'''


def query_package(filename):
    '''
    Query which package provides the file.

    If no package matches, an empty string will be returned. If multiple package
    match, the first result will be returned.

    In order to make the best guess, use the absolute path of the target file.

    Args:
        filename (str): Path of the file.

    Returns:
        str: The package name which provides it.

    Raises:
        RuntimeError: If ``dpkg`` exits with non-zero code.

    '''
    p = subprocess.Popen(('dpkg', '-S', filename),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if not out:
        return
    if p.returncode:
        raise RuntimeError("`dpkg' returned with code {}".format(p.returncode))
    return out.decode().split(': ')[0]


def friendlize(commands):
    '''
    Convert ``update-alternatives`` commands into readable descriptions.

    Args:
        commands (List[str]): List of commands from
            ``Alternative.compare()``

    Yields:
        List[str]: The readable description for the command.

    '''
    for cmd in commands:
        type_ = cmd[0]
        if type_ == 'install':
            yield (
                _("Install option `{3}' for group `{2}'").format(*cmd),
                _('Priority: {4}').format(*cmd),
                *(_("Slave `{}': `{}'").format(name, path)
                  for __, __, name, path in zip(*((iter(cmd[5:]), ) * 4))),
            )
        elif type_ == 'auto':
            yield (
                _("Set group `{1}' to auto mode").format(*cmd),
            )
        elif type_ == 'set':
            yield (
                _("Set group `{1}' to manual mode, pointed to `{2}'")
                .format(*cmd),
            )
        elif type_ == 'remove':
            yield (
                _("Remove option `{2}' for group `{1}'").format(*cmd), )
        elif type_ == 'remove-all':
            yield (
                _("Remove group `{1}'").format(*cmd),
            )
