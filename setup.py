#!/usr/local/bin/python

import os, sys

from distutils.core import setup
import galternatives
from galternatives.common import VERSION

data = [ ('bin', ['galternatives/galternatives']),
         ('share/pixmaps', ['pixmaps/galternatives.png']),
         ('share/galternatives', ['galternatives.glade']),
         ('share/galternatives/descriptions', ['descriptions/x-terminal-emulator.control']) ]

if sys.argv[1] == 'build' or sys.argv[1] == 'install':
    curdir = os.getcwd ()
    os.chdir ('%s/translations' % (curdir))
    os.system ('./update-translations.sh')

    pipe = os.popen ('./list-mos.sh')
    while True:
        line = pipe.readline ().strip ()
        if line == '':
            break
        data.append (('share/locale/%s/LC_MESSAGES' % (line), ['translations/%s/galternatives.mo' % (line)]))
    pipe.close ()
    print data
    os.chdir (curdir)

if __name__ == '__main__' :
    setup(name                  = "galternatives",
          version               = VERSION,
          license               = "GPL",
          description           = "Manager for the alternatives system",
          author                = "Gustavo Noronha Silva",
          author_email          = "kov@debian.org",
          url                   = "http://galternatives.alioth.debian.org/",
          packages              = [ 'galternatives' ],
          data_files		= data)

