#!/usr/bin/env python3
from galternatives import PACKAGE, INFO

from glob import glob
import os
import sys
from distutils.core import setup


if len(sys.argv) > 1:
    if sys.argv[1] == 'build' or sys.argv[1] == 'install':
        os.system('make -C resources')
    elif sys.argv[1] == 'clean':
        os.system('make -C resources clean')

if __name__ == '__main__':
    setup(
        name=PACKAGE,
        version=INFO['version'],
        license='GPL2+',
        description='Manager for the alternatives system',
        long_description='A GUI to help the system administrator to choose '
                         'what program should provide a given service.',
        author='Gustavo Noronha Silva',
        author_email='kov@debian.org',
        url=INFO['website'],
        scripts=['resources/galternatives'],
        packages=[PACKAGE],
        data_files=[
            ('share/applications', glob('resources/*.desktop')),
            ('share/galternatives/glade',
             glob('resources/glade/*.glade') + glob('resources/glade/*.ui')),
            ('share/galternatives/descriptions',
             glob('resources/descriptions/*.desktop')),
            ('share/icons/hicolor/48x48/apps', glob('resources/icons/*.png')),
            ('share/icons/hicolor/scalable/apps', glob('resources/icons/*.svg')),
        ] + [
            ('share/locale/{}/LC_MESSAGES'.format(locale), [
                'resources/locale/{}/LC_MESSAGES/galternatives.mo'.format(
                    locale)
            ]) for locale in os.listdir('resources/locale')
        ] if os.path.isdir('resources/locale')
        else []  # deal with `setup.py clean'
    )
