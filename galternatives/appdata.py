'''
This file contains constants used by various components of the app,
especially the ones that deal with the resource paths.
'''
from . import logger, PACKAGE

import os


__all__ = ['locate_appdata', 'PATHS']


# Idea stolen from QStandardPaths
PATHS = {
    'appdata': [
        os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                     'resources'),
        os.path.join('/usr/share', PACKAGE),
        os.path.join('/usr/local/share', PACKAGE),
        os.path.join('~/.local/share', PACKAGE),
    ],
    'icon': [
        os.path.join(os.path.dirname(os.path.realpath(__file__)),
                     'resources/pixmaps'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                     'resources/pixmaps'),
        os.path.join('/usr/share/pixmaps', PACKAGE),
    ],
}


def locate_appdata(locations, filenames, is_dir=False):
    if type(filenames) != str:
        filename = filenames[0]
    else:
        filename = filenames
        filenames = (filename, )
    for test_location in locations:
        for alt_filename in filenames:
            candidate = os.path.join(test_location, alt_filename)
            if os.path.isdir(candidate) if is_dir else os.path.isfile(candidate):
                logger.debug('locate "{}" at {}'.format(filename, candidate))
                return candidate
    logger.warn('locate "{}" FAILED'.format(filename))
