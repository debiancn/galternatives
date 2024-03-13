"""
Give readable information for various internal objects.

Attributes:
    DESC_DIR (str): Directory path where descriptions for alternative groups
        are stores.
    DEFAULT_DESCRIPTION (str): Placeholder when no description is found.

"""

from configparser import ConfigParser
from gettext import gettext
from locale import getdefaultlocale
from typing import Any, Generator, NamedTuple
import os
import subprocess

from .appdata import get_data_path


__all__ = ['altname_desc', 'query_package', 'describe_cmds']


_ = gettext


DESC_DIR = get_data_path('descriptions', True)
DEFAULT_DESC = _('No description')
DEFAULT_ICON = 'dialog-question'


class Description(NamedTuple):
    name: str
    desc: str = DEFAULT_DESC
    icon: str = DEFAULT_ICON


def altname_desc(name: str, locale=getdefaultlocale()[0]) -> Description:
    """
    Find readable group name and its description for given alternative group
    name.

    It will try to find proper translated strings, then the untranslated
    name and description. If both failed, the original name will be
    returned, along with a placeholder 'No description' as its description.

    :param name: Name of the group.
    :param locale: Preferred locale. Default to current environment locale.
    :return: Readable group name and its description.
    """
    desc_file = os.path.join(DESC_DIR, '{}.desktop'.format(name))

    config = ConfigParser()
    if desc_file not in config.read(desc_file):
        return Description(name)

    section = config['Desktop Entry']
    return Description(
        section.get(f'Name[{locale}]') or section.get('Name') or name,
        section.get(f'Comment[{locale}]') or section.get('Comment') or
        DEFAULT_DESC,
        section.get('Icon') or DEFAULT_ICON)


def query_package(filename: str) -> str | None:
    """
    Query which package provides the file in question.

    In order to make the best guess, use the absolute path of the target file.

    :param filename: Path to the file.
    :return: str: The package name which provides it.
        If no package matches, `None` is returned. If multiple package match,
        the first result will be returned.
    :raises RuntimeError: If `dpkg` exits with non-zero code.
    """
    try:
        p = subprocess.run(['dpkg', '-S', filename], capture_output=True)
    except subprocess.CalledProcessError:
        raise RuntimeError(f"`dpkg' returned with code {p.returncode}")
    return p.stdout and p.stdout.decode().split(': ')[0] or None


def describe_cmds(cmds: list[list[str]]) -> Generator[list[str], Any, None]:
    """
    Describe `update-alternatives` command operations.

    :param cmds: List of commands from :meth:`Alternative.compare`.
    :yield: The readable description for the command.
    """
    for cmd in cmds:
        action = cmd[0]
        if action == 'install':
            desc = [
                _("Install option `{3}' for group `{2}'").format(*cmd),
                _('Priority: {4}').format(*cmd)]
            for __, __, name, path in zip(*([iter(cmd[5:])] * 4)):
                desc.append(_("Slave `{}': `{}'").format(name, path))
            yield desc
        elif action == 'auto':
            yield [_("Set group `{1}' to auto mode").format(*cmd)]
        elif action == 'set':
            yield [_(
                "Set group `{1}' to manual mode, pointed to `{2}'"
            ).format(*cmd)]
        elif action == 'remove':
            yield [_("Remove option `{2}' for group `{1}'").format(*cmd)]
        elif action == 'remove-all':
            yield [_("Remove group `{1}'").format(*cmd)]
