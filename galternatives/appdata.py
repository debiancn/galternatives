'''
This file contains constants used by various components of the app,
especially the ones that deal with the resource paths.
'''
from . import logger, PACKAGE

import os


__all__ = ['PACKAGE', 'VERSION', 'DESC_DIR', 'GLADE_PATH', 'ABOUT_IMAGE_PATH']


# Idea stealed from QStandardPaths
appdata_locations = [
    os.path.join('/usr/share', PACKAGE),
    os.path.join('/usr/local/share', PACKAGE),
    os.path.join('~/.local/share', PACKAGE),
    os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources'),
    os.path.dirname(os.path.realpath(__file__)),
    os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                 'resources'),
]
icon_locations = [
    os.path.join('/usr/share/pixmaps', PACKAGE),
    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                 'resources/pixmaps'),
    os.path.dirname(os.path.realpath(__file__)),
    os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                 'resources/pixmaps'),
]


def locate_appdata(locations, filename, is_dir=False):
    for test_location in locations:
        test_path = os.path.join(test_location, filename)
        if os.path.isdir(test_path) if is_dir else os.path.isfile(test_path):
            logger.debug(
                'locate_appdata: locate "{}" at {}'.format(filename, test_path))
            return test_path
    logger.warn('locate_appdata: locate "{}" FAILED'.format(filename))
    return ''


DESC_DIR = locate_appdata(appdata_locations, 'descriptions', True)
GLADE_PATH = locate_appdata(appdata_locations, 'galternatives.glade') or \
             locate_appdata(appdata_locations, 'glade/galternatives.glade')
ABOUT_IMAGE_PATH = locate_appdata(icon_locations, 'galternatives.png')
