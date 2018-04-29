'''
Handle alternative database.

The library can read the database of alternative system, make virtual
changes to it, and output ``update-alternatives`` commands according to the
differences between two databases, while saving the state of the original
database is user's duty, by calling ``deepcopy(db)``.

The difference is represented in a list of ``update-alternatives`` argument
lists, without the leading two dashes.

Note we do not try to implement a full version of ``update-alternatives`` in
Python; format and mechanism of alternative system may change in the future,
while we'd like to describe the most fundamental features that will not
likely to be changed.

'''
from __future__ import with_statement

from collections import namedtuple
import os
import subprocess
import sys


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


CommandResult = namedtuple('CommandResult', ('cmd', 'returncode', 'out', 'err'))


class Option(dict):
    '''
    Class for option of alternative group.

    The class does not remember the group it belongs to; it's more like a
    wrapper for dict.

    Attributes:
        priority (int): Priority of the option.

    '''
    def __init__(self, it=(), priority=0, *args, **kwargs):
        '''
        Init the class.

        Args:
            it (Iterable, optional): Iterator for dict initialization. Default
                is empty list.
            priority (int, optional): Priority of the option. Default is 0.
            *args: Variable length argument list will be passed to the super
                constructor.
            **kwargs: Arbitrary keyword arguments will be passed to the super
                constructor.

        '''
        super(Option, self).__init__(it, *args, **kwargs)
        self.priority = priority

    def describe(self, group):
        '''
        Convert to ``update-alternatives`` command.

        Args:
            group (Group): The group which it belongs to.

        Returns:
            Tuple[str, ...]: ``update-alternatives`` command.

        Raises:
            ValueError: If the master path is missing.

        '''
        diff = []
        for ind, name in enumerate(group):
            if name in self and self[name]:
                diff.extend((
                    '--slave' if ind else 'install', group[name],
                    name, self[name]))
            elif ind == 0:
                raise ValueError('master path missing')
            if ind == 0:
                diff.append(str(self.priority))
        return tuple(diff)

    def same_with(self, other, group):
        '''
        Tell whether two options have the same path set for the group.

        Args:
            other (Option): Option to be compared with.
            group (Group): The group which it belongs to.

        Returns:
            bool: The result.

        '''
        return all(self[name] == other[name] for name in group)

    def __hash__(self):
        return id(self)

    def paths(self, group):
        return tuple(
            self[group[i]] if group[i] in self else ''
            for i in range(len(group)))


class Group(list, object):
    '''
    Class for alternative group.

    It acts like an OrderedDict, but allows int as index. The class itself
    stores the names for the master and slave links, while the actual links are
    stored in `_links` attribute.

    See update-alternatives(1) for properties' detail.

    Attributes:
        _parent (Alternative): The associated alternative database.
        _links (Dict[str, str]): Links for names.
        options (List[Option]): Available options.
        status (bool): Whether the group is in auto mode. Read only.
        current (Option): The current applied option. Read only.

    '''
    def __init__(self, name, create=False, parent=None):
        super(Group, self).__init__()
        self._parent = parent
        self._links = {}
        self._current = True
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
            self._current = next(it) == 'auto'
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

        admin = os.path.join(self._parent.admindir, self.name)
        if not os.path.islink(admin):
            raise IOError('admin link for "{}" corrupted'.format(name))
        current_path = os.readlink(admin)

        if not self._current:
            for option in self.options:
                if option[self.name] == current_path:
                    self._current = option

    @property
    def alt(self):
        '''Path of alt file in the admindir.'''
        return os.path.join(self._parent.altdir, self.name)

    @property
    def name(self):
        '''Name of the group.'''
        return self[0]

    @property
    def link(self):
        '''Master link of the group.'''
        return self[self.name]

    @link.setter
    def link(self, value):
        self[self.name] = value

    @property
    def status(self):
        return self._current is True

    @property
    def current(self):
        return self.best if self.status else self._current

    @property
    def best(self):
        '''The best option for the group (the one with the highest priority).'''
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
                self._current = True
                return True
        else:
            if not self.status and self.current == self.options[index]:
                return False
            else:
                self._current = self.options[index]
                return True

    def __setitem__(self, index, value):
        if type(index) == int:
            if value in self._links:
                raise KeyError('element already exists')
            # except_tag(value)
            self._links[value] = self._links[self[index]]
            del self._links[self[index]]
            super(Group, self).__setitem__(index, value)
        else:
            # except_absolute(value)
            if index not in self._links:
                super(Group, self).append(index)
            self._links[index] = value

    def __getitem__(self, index):
        if type(index) in (int, slice):
            return super(Group, self).__getitem__(index)
        else:
            return self._links[index]

    def __delitem__(self, index):
        if type(index) != int:
            index = self.index(index)
        del self._links[super(Group, self).__getitem__(index)]
        super(Group, self).__delitem__(index)

    def __repr__(self):
        return 'altgroup: {} links: {} options: {}'.format(
            self.name, repr(self._links), self.options)

    def __hash__(self):
        return id(self)

    def items(self):
        return [(link, self[link]) for link in self]

    def find_option(self, path):
        for option in self.options:
            if option[self.name] == path:
                return option

    def compare(self, old_group={}):
        '''
        Compare two groups and return the differential commands.

        Args:
            old_group (Group, optional): Original group to be compared with.

        Returns:
            List[Tuple[str, ...]]: Differential commands.

        '''
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
            if not old_group or old_group.status or \
                    not self.current.same_with(old_group.current, self):
                # no old, old in auto, old current not the same
                res.append(('set', self.name, self.current[self.name]))
        return res


def list_starts_with(l, prefix):
    return l[:len(prefix)] == prefix


class Alternative(dict):
    altdir = '/var/lib/dpkg/alternatives'
    admindir = '/etc/alternatives'
    log = '/var/log/alternatives.log'
    update_alternatives = 'update-alternatives'
    PATHS = ('altdir', 'admindir', 'log')

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
        '''
        Add new group to the alternative database.

        Args:
            item (Group): Group to be added.

        Raises:
            KeyError: If the group name already exists.

        '''
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
        self[old][0] = new
        super(Alternative, self).__setitem__(new, self[old])
        super(Alternative, self).__delitem__(old)

    def compare(self, old_db):
        diff = []
        for group_name in old_db:
            if group_name not in self:
                # group in old but not in new
                diff.append(('remove-all', group_name))
        for group_name in self:
            if dict.__getitem__(self, group_name):
                # item has been accessed
                if group_name in self._moves or \
                        not list_starts_with(self[group_name].items(),
                                             old_db[group_name].items()):
                    # group moved or more links than old one, reconstruct
                    if group_name in self._moves and \
                            self._moves[group_name] in old_db and \
                            self._moves[group_name] in self:
                        diff.append(('remove-all', self._moves[group_name]))
                    elif group_name in old_db:
                        diff.append(('remove-all', group_name))
                    diff.extend(self[group_name].compare())
                else:
                    # simply add difference
                    diff.extend(self[group_name].compare(old_db[group_name]))
        return diff

    def commit(self, diff, executer=None):
        results = []
        for cmd in diff:
            args = list(cmd)
            args[0] = '--' + args[0]
            args.insert(0, self.update_alternatives)
            if executer:
                args.insert(0, executer)
            p = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            if isinstance(out, str):
                results.append(CommandResult(args, p.returncode, out, err))
            else:
                results.append(CommandResult(
                    args, p.returncode, out.decode(), err.decode()))
            if p.returncode:
                break
        return p.returncode, results
