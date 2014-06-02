#!/usr/bin/python

from common import PACKAGE
import os, gettext

_ = gettext.gettext

from gadebug import print_debug

class Alternative:
    def __init__ (self, unixname, locale = 'C'):
        # default fallback, in case there's no control file, or a
        # corrupted one
        self.unixname = unixname
        self.name = unixname
        self.description = _('No description')
        self.locale = locale
        try:
            desc_file = open ('/usr/share/galternatives/descriptions/%s.control' %
                              (unixname))

            # init some variables, cause we're gonna check all of
            # them, and some may be unitialized
            original_name = ''
            translated_name = ''
            original_desc = ''
            translated_desc = ''

            while 1:
                str = desc_file.readline ().strip ()
                if str == '':
                    break

                elif str[:4] == 'Name':
                    translation_start = 5 + len (self.locale)

                    if str[4] == '=':
                        original_name = str[5:]
                    elif str[5:translation_start] == self.locale:
                        translated_name = str[translation_start+2:]

                elif str[:11] == 'Description':
                    print_debug (str)
                    translation_start = 12 + len (self.locale)

                    if str[11] == '=':
                        original_desc = str[12:]
                    elif str[12:translation_start] == self.locale:
                        translated_desc = str[translation_start+2:]

            desc_file.close ()

            if translated_name:
                self.name = translated_name
            else:
                self.name = original_name
                
            if translated_desc:
                self.description = translated_desc
            else:
                self.description = original_desc

        except IOError:
            pass

        # now get the real information!
        altfile = open ('/var/lib/dpkg/alternatives/%s' % (unixname))

        # parsing file
        self.option_status = altfile.readline ().strip ()
        print_debug ('The Status is: %s' % (self.option_status))

        self.link = altfile.readline ().strip ()
        print_debug ('The link is: %s' % (self.link))

        # find out what are the slaves used by this alternative
        # we need that to know how many slaves to expect from each
        # alternative
        self.slaves = []
        while 1:
            line = altfile.readline ().strip ()
            if line == '':
                break
            
            sdict = {}
            sdict['name'] = line
            sdict['link'] = altfile.readline ().strip ()
            self.slaves.append (sdict)
            
        self.current_option = os.readlink ('/etc/alternatives/%s' %
                                           (unixname))
        print_debug ('Link currently points to: %s' % (self.current_option))

        self.options = []
        while 1:
            line = altfile.readline ().strip ()
            if line == '':
                break

            odict = {}
            odict['path'] = line
            odict['priority'] = altfile.readline ().strip ()
            print_debug (odict)
            optslaves = []
            for count in range(len (self.slaves)):
                sdict = {}
                sdict['name'] = self.slaves[count]['name']
                sdict['path'] = altfile.readline ().strip ()
                optslaves.append (sdict)
            odict['slaves'] = optslaves

            self.options.append (odict)
        print_debug (self.options)

        altfile.close ()

    def get_unixname (self):
        return self.unixname

    def get_name (self):
        return self.name

    def get_description (self):
        return self.description

    def get_options (self):
        return self.options

    def get_slaves (self):
        return self.slaves

    def get_link (self):
        return self.link

    def get_current_option (self):
        return self.current_option

    def get_option_status (self):
        return self.option_status

    def set_option_status (self, status):
        self.option_status = status

    def set_unixname (self, unixname):
        self.unixname = unixname

    def set_name (self, name):
        self.name = name

    def set_description (self, description):
        self.description = description

    def set_options (self, options):
        self.options = options

    def set_slaves (self, slaves):
        self.slaves = slaves

    def set_link (self, link):
        self.link = link

if __name__ == '__main__':
    alt = Alternative ('x-terminal-emulator')
    print 'name: %s\nlink: %s\ndescription: %s\nOptions:' \
          % (alt.get_name (), alt.get_link(), alt.get_description ())
    print alt.get_options ()
    print 'current_option: %s' % (alt.get_current_option ())
