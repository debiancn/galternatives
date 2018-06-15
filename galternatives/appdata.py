'''
Find and locate resources for the application.

Attributes:
    PATHS (List[str]): Various paths where the application data may be
        stored at.
        Note: orders matter, especially when the program is installed
        globally.

'''
from . import _, logger, PACKAGE

import os
try:
    import xdg.BaseDirectory
    import xdg.IconTheme
except ImportError:
    class xdg:
        class BaseDirectory:
            @staticmethod
            def load_data_paths(resource):
                yield '/usr/share/' + resource

        class IconTheme:
            @staticmethod
            def getIconPath(iconname):
                path = f'/usr/share/icons/hicolor/48x48/apps/{iconname}.png'
                if os.path.isfile(path):
                    return path


__all__ = ['get_data_path', 'get_icon_path', 'LOGO_PATH']


PATHS = [
    os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources'),
    os.path.join(os.path.dirname(
        os.path.dirname(os.path.realpath(__file__))), 'resources'),
    *xdg.BaseDirectory.load_data_paths(PACKAGE)
]


def get_data_path(filenames, is_dir=False):
    '''
    Find a file or directory by its name in multiple locations.

    It will search the target in the directory from `PATHS` sequentially,
    and return the first item matches. If none matches, ``None`` is
    returned.

    Args:
        filenames (Union[str, List[str]]): Filename(s) of the target. If
            multiple filename provides, the first one will be used as
            'master' one shown in the log.
        is_dir (bool, optional): Whether the target filename represents a
            directory. Default is false.

    Returns:
        Optional[str]: The path of the target.

    '''
    if type(filenames) != str:
        filename = filenames[0]
    else:
        filename = filenames
        filenames = (filename, )
    for test_location in PATHS:
        for alt_filename in filenames:
            candidate = os.path.join(test_location, alt_filename)
            if os.path.isdir(candidate) if is_dir \
                    else os.path.isfile(candidate):
                logger.debug('locate "{}" at {}'.format(filename, candidate))
                return candidate
    logger.warn('locate "{}" FAILED'.format(filename))


def get_icon_path(iconname):
    path = xdg.IconTheme.getIconPath(iconname)
    if path:
        return path
    for extensions in ['png', 'svg', 'xpm']:
        path = get_data_path('icons/{}.{}'.format(iconname, extensions))
        if path:
            return path


LOGO_PATH = get_icon_path(PACKAGE)
if LOGO_PATH is None:
    logger.warn(_('Logo missing. Is your installation correct?'))
