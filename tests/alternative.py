#!/usr/bin/env python3

from galternatives.alternative import Alternative

if __name__ == '__main__':
    alt = Alternative('x-terminal-emulator')
    print('name: {}\nlink: {}\ndescription: {}\nOptions:'
          .format(alt.name, alt.link, alt.description))
    print(alt.options)
    print('current_option: {}'.format(alt.current_option))
