#!/usr/bin/env python
from galternatives import PACKAGE, VERSION

from glob import glob
import os
import sys
from distutils.core import setup
from distutils.command import install_scripts


if sys.argv[1] == 'build' or sys.argv[1] == 'install':
    os.system('make -C resources')

if __name__ == '__main__':
    setup(
        name=PACKAGE,
        version=VERSION,
        license="GPL",
        description="Manager for the alternatives system",
        long_description='A GUI to help the system administrator to choose '
                         'what program should provide a given service.',
        author="Gustavo Noronha Silva",
        author_email="kov@debian.org",
        url="https://galternatives.alioth.debian.org/",
        scripts=['resources/galternatives'],
        packages=[PACKAGE],
        data_files=[
            ('share/pixmaps', glob('resources/pixmaps/*.png')),
            ('share/galternatives', glob('resources/glade/*.glade')),
            ('share/galternatives/descriptions', glob('resources/descriptions/*.desktop')),
        ] + list(
            ('share/locale/{}/LC_MESSAGES'.format(locale), [
                'resources/locale/{}/LC_MESSAGES/galternatives.mo'.format(locale)
            ])
            for locale in os.listdir('resources/locale')
        )
    )
