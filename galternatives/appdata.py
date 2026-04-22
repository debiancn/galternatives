"""
Find and locate resources for the application.
"""

from gettext import gettext
import os
from typing import TYPE_CHECKING, Iterator, Literal, overload

if TYPE_CHECKING:
    from _typeshed import StrPath

from . import logger, PACKAGE

try:
    from xdg.BaseDirectory import load_data_paths
except ImportError:
    def load_data_paths(*resource) -> Iterator[str]:  # type: ignore
        yield os.path.join('/usr/share/', *resource)  # type: ignore

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


@overload
def get_data_path(
    name: 'StrPath', is_dir: bool = False, require: Literal[False] = False
) -> str | None: ...


@overload
def get_data_path(
    name: 'StrPath', is_dir: bool, require: Literal[True]) -> str: ...


def get_data_path(
        name: 'StrPath', is_dir: bool = False, require: bool = False
) -> str | None:
    """
    Find a file or directory by its name in multiple locations.

    It will search the target in the directory from ``DATA_DIRS`` sequentially,
    and return the first matching item.

    :param name: Relative path to the target.
    :param is_dir: Whether ``path`` should be a directory.
    :return: Full path to the target, or `None` if not found.
    """
    path = None
    for dir in DATA_DIRS:
        path = os.path.join(dir, name)
        if os.path.isdir(path) if is_dir else os.path.isfile(path):
            logger.debug(f'locate "{name}" at {name, path}')
            break

    if path is None:
        if require:
            raise FileNotFoundError(f'locate "{name}" FAILED')
        else:
            logger.warning(f'locate "{name}" FAILED')

    return path


def get_icon_path(iconname: str) -> str | None:
    path = getIconPath(iconname)
    if path:
        return path
    for ext in ['png', 'svg', 'xpm']:
        path = get_data_path(f'icons/{iconname}.{ext}')
        if path:
            return path


LOGO_PATH = get_icon_path(PACKAGE)
if LOGO_PATH is None:
    logger.warning(_('Logo missing. Is your installation correct?'))
