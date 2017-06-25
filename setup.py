#!/usr/bin/env python
from galternatives import PACKAGE, VERSION

from glob import glob
import os
import sys
from distutils.core import setup


if sys.argv[1] == 'build' or sys.argv[1] == 'install':
    os.system('make -C resources')

if __name__ == '__main__':
    setup(
        name=PACKAGE,
        version=INFO['version'],
        license='GPL',
        description='Manager for the alternatives system',
        long_description='A GUI to help the system administrator to choose '
                         'what program should provide a given service.',
        author='Gustavo Noronha Silva',
        author_email='kov@debian.org',
        url=INFO['website'],
        scripts=['resources/galternatives'],
        packages=[PACKAGE],
        data_files=[
            ('share/pixmaps', glob('resources/pixmaps/*.png')),
            ('share/galternatives/glade', glob('resources/glade/*.glade')),
            ('share/galternatives/descriptions',
             glob('resources/descriptions/*.desktop')),
        ] + [
            ('share/locale/{}/LC_MESSAGES'.format(locale), [
                'resources/locale/{}/LC_MESSAGES/galternatives.mo'.format(
                    locale)
            ]) for locale in os.listdir('resources/locale')
        ]
    )
