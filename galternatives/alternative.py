from __future__ import with_statement

import os
import sys


def get_admin(admindir, name):
    if name is None:
        return None
    admin = os.path.join(admindir, name)
    if not os.path.islink(admin):
        raise IOError('admin link for "{}" corrupted'.format(name))
    return admin


def get_link(link, admin):
    if admin is None:
        return None
    if not os.path.exists(link):
        raise IOError('target link "{}" not exists'.format(link))
    if not os.path.islink(link):
        raise IOError('target link "{}" not symlink'.format(link))
    if os.readlink(link) != admin:
        raise IOError(
            'target link "{}" not a symlink to corresponding admin'.format(
                link))
    return link


def get_empty(targetdir, name):
    empty = os.path.join(targetdir, name)
    if os.path.exists(empty):
        raise IOError('target path "{}" already exists'.format(empty))
    return empty


def except_typeof(i, of_type):
    if not isinstance(i, of_type):
        raise TypeError('instance "{}" not of type {}, got {}'.format(
            repr(i), of_type.__name__, type(i).__name__))


def except_absolute(path):
    if path == '':
        return
    except_typeof(path, str)
    if not os.path.isabs(path):
        raise ValueError('path not absolute')


def except_tag(tag):
    except_typeof(tag, str)
    if any(char in tag for char in ' \t\n\r'):
        raise ValueError('special char not allowed')


class Option(dict):
    def __init__(self, it=(), priority=0, *args, **kwargs):
        super(Option, self).__init__(it, *args, **kwargs)
        self.priority = priority

    def describe(self, group):
        diff = []
        for ind, name in enumerate(group):
            if name in self:
                diff.extend((
                    '--slave' if ind else 'install', group[name],
                    name, self[name]))
            elif ind == 0:
                raise ValueError('master path missing')
            if ind == 0:
                diff.append(self.priority)
        return tuple(diff)

    def same_with(self, other, group):
        return all(self[name] == other[name] for name in group)

    def __hash__(self):
        return id(self)


class Group(list):
    # property names come from update-alternatives(1)
    status = True
    current = None

    def __init__(self, name, create=False, parent=None):
        self._parent = parent
        self._links = {}
        super(Group, self).__init__()
        self[name] = ''
        self.options = []
        if not create:
            self.reload()

    def reload(self):
        if not os.path.isfile(self.alt):
            raise IOError('group alt file missing')

        # parse alt file
        with open(self.alt) as alt_file:
            it = map(lambda s: s.strip(), alt_file)
            if sys.version_info < (3,):
                it = iter(it)

            # target parser
            self.status = next(it) == 'auto'
            self[self.name] = next(it)
            while True:
                line = next(it)
                if line == '':
                    break
                self[line] = next(it)

            # option parser
            while True:
                it_name = iter(self)
                line = next(it)
                if line == '':
                    break
                option = Option({next(it_name): line}, int(next(it)))
                for name in it_name:
                    option[name] = next(it)
                self.options.append(option)

        current_path = os.readlink(get_admin(self._parent.admindir, self.name))
        for option in self.options:
            if option[self.name] == current_path:
                self.current = option

    @property
    def alt(self):
        return os.path.join(self._parent.altdir, self[0])

    @property
    def name(self):
        return self[0]

    @property
    def link(self):
        return self[self.name]

    @property
    def best(self):
        return max(self.options, key=lambda o: o.priority)

    @property
    def options_dict(self):
        res = {option[self.name]: option for option in self.options}
        if len(res) != len(self.options):
            raise ValueError('duplicated master path found')
        return res

    def select(self, index=None):
        if index is None:
            if self.status:
                return False
            else:
                self.current = self.best
                self.status = True
                return True
        else:
            if not self.status and self.current == self.options[index]:
                return False
            else:
                self.current = self.options[index]
                self.status = False
                return True

    def __setitem__(self, index, value):
        if type(index) == int:
            if value in self._links:
                raise KeyError('element already exists')
            except_tag(value)
            self._links[value] = self._links[self[index]]
            del self._links[self[index]]
            super(Group, self).__setitem__(index, value)
        else:
            except_absolute(value)
            if index not in self._links:
                super(Group, self).append(index)
            self._links[index] = value

    def __getitem__(self, index):
        if type(index) == int:
            return super(Group, self).__getitem__(index)
        else:
            return self._links[index]

    def __delitem__(self, index):
        if type(index) != int:
            index = self.index(self[index])
        del self._links[super(Group, self).__getitem__(index)]
        super(Group, self).__delitem__(index)

    def __repr__(self):
        return 'altgroup: {} links: {} options: {}'.format(
            self.name, repr(self._links), self.options)

    def __hash__(self):
        return id(self)

    def find_option(self, path):
        for option in self.options:
            if option[self.name] == path:
                return option

    def compare(self, old_group={}):
        new_options = self.options_dict
        old_options = old_group and old_group.options_dict
        res = [
            ('remove', self.name, p)
            for p in old_options
            if p not in new_options
        ] + [
            o.describe(self)
            for p, o in new_options.items()
            if p not in old_options or not o.same_with(old_options[p], self)
        ]
        if self.status:
            # self in auto
            if old_group and not old_group.status:
                # old in manual
                res.append(('auto', self.name))
        else:
            # self in manual
            if not old_group or old_group.status or not self.current.same_with(old_group.current, self):
                # no old, old in auto, old current not the same
                res.append(('set', self.name, self.current[self.name]))
        return res


class Alternative(dict):
    altdir = '/var/lib/dpkg/alternatives'
    admindir = '/etc/alternatives'
    log = '/var/log/alternatives.log'
    update_alternatives = '/usr/bin/update-alternatives'

    def __init__(self, altdir=None, admindir=None, log=None):
        if altdir is not None:
            self.altdir = altdir
        if admindir is not None:
            self.admindir = admindir
        if log is not None:
            self.log = log
        self._moves = {}
        super(Alternative, self).__init__(
            map(lambda name: (name, None), filter(
                lambda name: os.path.isfile(os.path.join(self.altdir, name)),
                os.listdir(self.altdir))))

    def __repr__(self):
        return repr(self.keys())

    def __getitem__(self, name):
        item = super(Alternative, self).__getitem__(name)
        if not item:
            item = Group(name, parent=self)
            super(Alternative, self).__setitem__(name, item)
        return item

    def add(self, item):
        # except_typeof(item, Group)
        if item.name in self:
            raise KeyError('element already exists')
        item._parent = self
        self._moves[item.name] = None
        return super(Alternative, self).__setitem__(item.name, item)

    def move(self, old, new):
        if old in self._moves:
            self._moves[new] = self._moves[old]
            del self._moves[old]
        else:
            self._moves[new] = old
        if self._moves[new] == new:
            del self._moves[new]
        super(Alternative, self).__setitem__(new, self[old])
        super(Alternative, self).__delitem__(old)

    def compare(self, old_db):
        diff = []
        for group in old_db:
            if group not in self:
                diff.append(('remove-all', group))
        for group in self:
            if dict.__getitem__(self, group):
                if group in self._moves or \
                        set(old_db[group]) - set(self[group]):
                    if group in self._moves and \
                            self._moves[group] in old_db and \
                            self._moves[group] in self:
                        diff.append(('remove-all', self._moves[group]))
                    diff.extend(self[group].compare())
                else:
                    diff.extend(self[group].compare(old_db[group]))
        return diff


def commit(diff):
    pass


if __name__ == '__main__':
    from copy import deepcopy
    b=Alternative()
    d=deepcopy(b)
    #d=Alternative()
    c=d['awk']
    print(c)
    c.options[0]['nawk.1.gz'] = '/'
    print(d.compare(b))
    del c.options[0]
    c.options.append(Option({'awk':'/','aaa':'/a'},1))
    print(d.compare(b))
    d.move('awk','aaa')
    print(d.compare(b))
