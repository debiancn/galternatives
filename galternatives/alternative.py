from __future__ import nested_scopes, generators, division, absolute_import, \
    with_statement

from . import logger, _
from .config import options
from .description import altname_description

import os


class Alternative:
    def __init__(self, name):
        # property names come from update-alternatives(1)
        alt_filepath = os.path.join(options['altdir'], name)
        if not os.path.isfile(alt_filepath):
            raise KeyError('No such alternative name')

        self.name, self.description = altname_description(name)

        # parse alt file
        with open(alt_filepath) as altfile:
            self.option_status = altfile.readline().strip()
            logger.debug('The Status is: %s' % (self.option_status))

            self.link = altfile.readline().strip()
            logger.debug('The link is: %s' % (self.link))

            # find out what are the slaves used by this alternative
            # we need that to know how many slaves to expect from each
            # alternative
            self.slaves = []
            while True:
                line = altfile.readline().strip()
                if line == '':
                    break
                self.slaves.append({
                    'name': line,
                    'link': altfile.readline().strip()
                })

            self.current_option = os.readlink(os.path.join(options['admindir'], name))
            logger.debug('Link currently points to: %s' % (self.current_option))

            self.options = []
            while True:
                line = altfile.readline().strip()
                if line == '':
                    break
                self.options.append({
                    'path': line,
                    'priority': altfile.readline().strip(),
                    'slaves': [
                        {
                            'name': slave['name'],
                            'path': altfile.readline().strip()
                        } for slave in self.slaves
                    ]
                })
            logger.debug(self.options)
