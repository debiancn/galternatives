'''
These are options that can be specified, but rarely changed ones.
See update-alternatives(1) OPTIONS section for more information.
'''
DEFAULT_OPTIONS = {
    'altdir': '/var/lib/dpkg/alternatives',
    'admindir': '/etc/alternatives',
    'log': '/var/log/alternatives.log',
}
options = DEFAULT_OPTIONS
