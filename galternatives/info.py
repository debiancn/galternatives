from gettext import gettext

try:
    from .version import VERSION
except ImportError:
    VERSION = 'git'


__all__ = ['PACKAGE', 'APPID', 'INFO']


_ = gettext


PACKAGE = 'galternatives'
"the package name"
APPID = 'org.debian.' + PACKAGE
"appid for Gtk.Application"
INFO = {
    'program_name': 'G Alternatives',
    'version': VERSION,
    'comments': _('A tool to help the administrator select which programs '
                  'provide specific services for the user by default.'),
    'license_type': 'GPL_2_0',
    'copyright':
        '(C) 2003-2006 Gustavo Noronha Silva\n'
        '(C) 2017-2019 Boyuan Yang',
    'website': 'https://salsa.debian.org/chinese-team/galternatives',
    'authors': (
        'Gustavo Noronha Silva <kov@debian.org>',
        'Boyuan Yang <073plan@gmail.com>',
        'Yangfl <mmyangfl@gmail.com>'),
    'artists': ('Leandro A. F. Pereira <leandro@linuxmag.com.br>', )}
"""
Other info (version, url, etc.) of the application.

Also used in Gtk.AboutDialog construction, unknown parameters may cause error.
"""
