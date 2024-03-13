"""
Find and locate resources for the application.
"""

from gettext import gettext
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

from . import logger, PACKAGE

try:
    from xdg.BaseDirectory import load_data_paths
except ImportError:
    def load_data_paths(resource: 'StrPath'):
        yield os.path.join('/usr/share/', resource)

try:
    from xdg.IconTheme import getIconPath
except ImportError:
    def getIconPath(iconname: str):
        path = f'/usr/share/icons/hicolor/48x48/apps/{iconname}.png'
        if os.path.isfile(path):
            return path


__all__ = ['get_data_path', 'get_icon_path', 'LOGO_PATH']


_ = gettext


DATA_DIRS = [
    os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources'),
    os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                 'resources')]
"""
Various paths where the application data may be stored at.

Note: orders matter, especially when the program is installed globally.
"""
DATA_DIRS.extend(load_data_paths(PACKAGE))


def get_data_path(path: 'StrPath', is_dir=False):
    """
    Find a file or directory by its name in multiple locations.

    It will search the target in the directory from ``DATA_DIRS`` sequentially,
    and return the first matching item.

    :param file: Path of the target.
    :param is_dir: Whether ``path`` should be a directory.
    :return: The path to the target, or `None` if not found.
    """
    for dir in DATA_DIRS:
        test = os.path.join(dir, path)
        if os.path.isdir(test) if is_dir else os.path.isfile(test):
            logger.debug('locate "{}" at {}'.format(path, test))
            return test
    logger.warning('locate "{}" FAILED'.format(path))


def get_icon_path(iconname: str):
    path = getIconPath(iconname)
    if path:
        return path
    for extensions in ['png', 'svg', 'xpm']:
        path = get_data_path('icons/{}.{}'.format(iconname, extensions))
        if path:
            return path


LOGO_PATH = get_icon_path(PACKAGE)
if LOGO_PATH is None:
    logger.warning(_('Logo missing. Is your installation correct?'))
