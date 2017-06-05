from __future__ import nested_scopes, generators, with_statement

import os
import sys
from weakref import WeakValueDictionary


ALTDIR = '/var/lib/dpkg/alternatives'
ADMINDIR = '/etc/alternatives'
LOG = '/var/log/alternatives.log'
UPDATE_ALTERNATIVES = '/usr/bin/update-alternatives'


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
    if path is None:
        return
    except_typeof(path, str)
    if not os.path.isabs(path):
        raise ValueError('path not absolute')


def except_tag(tag):
    except_typeof(tag, str)
    if any(char in tag for char in ' \t\n\r'):
        raise ValueError('special char not allowed')


class Name:
    def __init__(self, name):
        self.name = name

    def set(self, name):
        except_tag(name)
        self.name = name

    def get(self):
        return self.name

    def __repr__(self):
        return 'Name({})'.format(self.name)


class Option(dict):
    def __init__(self, init={}, priority=0, names=None, *args, **kwargs):
        super(Option, self).__init__(init, *args, **kwargs)
        for name, path in self.items():
            except_typeof(name, Name)
            except_absolute(path)
        self._names = names
        self.priority = priority

    def __getitem__(self, name):
        return super(Option, self).__getitem__(self._names[name])

    def __setitem__(self, name, path):
        except_absolute(path)
        return super(Option, self).__setitem__(self._names[name], path)

    def __contains__(self, name):
        return super(Option, self).__contains__(self._names[name])

    def __eq__(self, other):
        return all(
            name in other and self[name] == other[name]
            for name in self._names
        )

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


class OptionList(list):
    def __init__(self, names):
        super(OptionList, self).__init__()
        self._names = names

    def _map(self, dic):
        return {self._names[name]: path for name, path in dic.items()}

    def __setitem__(self, index, item):
        return super(OptionList, self).__setitem__(
            index, item if isinstance(item, Option) else
            Option(self._map(item), 0, self._names))

    def find(self, name, path):
        for option in self:
            if option[name] == path:
                return option
        # raise ValueError('{} is not in list'.format(name))

    def append(self, item, priority=0):
        return super(OptionList, self).append(
            item if isinstance(item, Option) else
            Option(self._map(item), priority, self._names))


class AlternativeGroup(list):
    # property names come from update-alternatives(1)
    STATUS = {'auto', 'manual'}
    _status = 'auto'
    _current = None

    def __init__(self, name, create=False, parent=None):
        self._parent = parent
        self._links = {}
        self._names = WeakValueDictionary()
        super(AlternativeGroup, self).__init__()
        self[name] = None
        self.options = OptionList(self._names)
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
            self._status = next(it)
            self[self[0]] = next(it)
            while True:
                line = next(it)
                if line == '':
                    break
                self[line] = next(it)

            # option parser
            while True:
                line = next(it)
                if line == '':
                    break
                option = []
                option.append(line)
                priority = int(next(it))
                for i in range(len(self) - 1):
                    option.append(next(it))
                self.options.append(
                    {name: path for name, path in zip(self, option)}, priority)

        current_path = os.readlink(get_admin(self._parent.admindir, self.name))
        for option in self.options:
            if option[self.name] == current_path:
                self._current = option

    @property
    def alt(self):
        return os.path.join(self._parent.altdir, self[0])

    @property
    def name(self):
        return self[0]

    @name.setter
    def name(self, value):
        self[0] = value

    @property
    def link(self):
        return self[self[0]]

    @link.setter
    def link(self, value):
        self[self[0]] = value

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        if value is None:
            if self.current not in self.options:
                self.status = 'auto'
            return
        if value == self._current:
            return
        if value not in self.options:
            raise ValueError('value nonexist')
        self._current = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value == self._status:
            return
        if value not in self.__class__.STATUS:
            raise ValueError(
                "status must be 'auto' or 'manual', not '{}'".format(value))
        self._status = value
        if value == 'auto':
            self._current = self.best

    @property
    def best(self):
        return max(self.options.values(), key=lambda o: o.priority)

    def __setitem__(self, index, value):
        if type(index) == int:
            if value in self._names:
                raise KeyError('element already exists')
            if index == 0:
                self._parent._move(self.name, value)
            self._names[value] = self._names[self[index]]
            del self._names[self[index]]
            super(AlternativeGroup, self).__getitem__(index).set(value)
        else:
            except_absolute(value)
            if index not in self._names:
                super(AlternativeGroup, self).append(Name(index))
                self._names[index] = \
                    super(AlternativeGroup, self).__getitem__(-1)
            self._links[self._names[index]] = value

    def __getitem__(self, index):
        if type(index) == int:
            return super(AlternativeGroup, self).__getitem__(index).get()
        else:
            return self._links[self._names[index]]

    def __delitem__(self, index):
        if type(index) != int:
            index = self.index(self._names[index])
        assert index > 0
        del self._links[super(AlternativeGroup, self).__getitem__(index)]
        super(AlternativeGroup, self).__delitem__(index)

    def __iter__(self):
        return (self[i] for i in range(len(self)))

    def __repr__(self):
        return 'altgroup: {} links: {} options: {}'.format(
            self.name, repr(self._links), self.options)


class Alternative(dict):
    def __init__(self, altdir=ALTDIR, admindir=ADMINDIR, log=LOG):
        self._altdir = altdir
        self._admindir = admindir
        self._log = log
        self._moves = {}
        super(Alternative, self).__init__(
            map(lambda name: (name, None), filter(
                lambda name: os.path.isfile(os.path.join(self.altdir, name)),
                os.listdir(self.altdir))))

    @property
    def altdir(self):
        return self._altdir

    @property
    def admindir(self):
        return self._admindir

    @property
    def log(self):
        return self._log

    def __repr__(self):
        return repr(self.keys())

    def __setitem__(self, name, item):
        raise RuntimeError('use add() instead')

    def __getitem__(self, name):
        item = super(Alternative, self).__getitem__(name)
        if not item:
            item = AlternativeGroup(name, parent=self)
            super(Alternative, self).__setitem__(name, item)
        return item

    def add(self, item):
        except_typeof(item, AlternativeGroup)
        if item.name in self:
            raise KeyError('element already exists')
        item._parent = self
        self._moves[item.name] = None
        return super(Alternative, self).__setitem__(item.name, item)

    def _move(self, old, new):
        if old in self._moves:
            self._moves[new] = self._moves[old]
            del self._moves[old]
        else:
            self._moves[new] = old
        if self._moves[new] == new:
            del self._moves[new]
        super(Alternative, self).__setitem__(new, self[old])
        super(Alternative, self).__delitem__(old)


def shrink_group(new_group, old_group):
    return [
        ('remove', new_group.name, option[new_group.name])
        for option in old_group.options
        if not new_group.options.find(new_group.name, option[new_group.name])
    ]


def extend_group(new_group, old_group=AlternativeGroup('EMPTY', True)):
    return [
        option.describe(new_group)
        for option in new_group.options
        if option != old_group.options.find(
            new_group.name, option[new_group.name])
    ]


def compare(new_db, old_db):
    diff = []
    for group in old_db:
        if group not in new_db:
            diff.append(('remove-all', group))
    for group in new_db:
        if dict.__getitem__(new_db, group) is not None:
            if group in new_db._moves or \
                    set(old_db[group]) - set(new_db[group]):
                if group in new_db._moves and \
                        new_db._moves[group] in old_db and \
                        new_db._moves[group] in new_db:
                    diff.append(('remove-all', new_db._moves[group]))
                diff.extend(extend_group(new_db[group]))
                if new_db[group].status != 'auto':
                    diff.append(('set', group, new_db[group].current[0]))
            else:
                diff.extend(shrink_group(new_db[group], old_db[group]))
                diff.extend(extend_group(new_db[group], old_db[group]))
                if new_db[group].status != old_db[group].status:
                    if new_db[group].status == 'auto':
                        diff.append(('auto', group))
                    elif new_db[group].current != old_db[group].current:
                        diff.append(('set', group, new_db[group].current[0]))
    return diff


def commit(diff):
    pass


if __name__ == '__main__':
    b=Alternative()
    d=Alternative()
    c=d['awk']
    print(c)
    c.options[0]['nawk.1.gz'] = '/'
    print(compare(d,b))
    del c.options[0]
    c.options.append({'awk':'/'},1)
    print(compare(d,b))
    c.name='aaa'
    print(compare(d,b))
