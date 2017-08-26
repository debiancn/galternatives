#!/usr/bin/env python
import os
import sys
# If run as a single file (rather than a module), include the correct path so
# that the package can be imported
if __name__ == '__main__' and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from galternatives.app import GAlternativesApp

import signal


def main():
    # Allow Ctrl-C to work
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = GAlternativesApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
