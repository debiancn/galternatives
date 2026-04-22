"""
Handle alternative database.

The library can read the database of alternative system, make virtual
changes to it, and output `update-alternatives` commands according to the
differences between two databases, while saving the state of the original
database is user's duty, by calling `copy.deepcopy(db)`.

The difference is represented in a list of `update-alternatives` argument lists,
without the leading two dashes.

Note we do not try to implement a full version of `update-alternatives` in
Python; format and mechanism of alternative system may change in the future,
while we'd like to describe the most fundamental features that will not likely
to be changed.
"""

from dataclasses import dataclass
import os
import subprocess
from typing import (
    TYPE_CHECKING, ClassVar, Iterable, Iterator, NamedTuple, Sequence,
    SupportsIndex, TypeVar, cast, overload)

if TYPE_CHECKING:
    from _typeshed import SupportsGetItem, SupportsKeysAndGetItem

from . import logger


_T = TypeVar('_T')

if TYPE_CHECKING:
    _U = TypeVar('_U')

    type DictInit[_T, _U] = (
        Iterable[tuple[_T, _U]] | SupportsKeysAndGetItem[_T, _U])


class CommandResult(NamedTuple):
    cmd: list[str]
    "subprocess command arguments list"
    returncode: int
    out: str
    "stdout"
    err: str
    "stderr"


@dataclass
class AltConfig:
    ALTDIR: ClassVar[str] = '/var/lib/dpkg/alternatives'
    ADMINDIR: ClassVar[str] = '/etc/alternatives'
    LOG: ClassVar[str] = '/var/log/alternatives.log'
    UPDATE_CMD: ClassVar[str] = 'update-alternatives'

    PATH_NAMES: ClassVar[list[str]] = ['altdir', 'admindir', 'log']

    altdir: str = ALTDIR
    admindir: str = ADMINDIR
    log: str = LOG
    update_cmd: str = UPDATE_CMD


class AltOption(dict[str, str]):
    """
    Class for option of alternative group.

    Instance does not remember the group it belongs to (and thus does not keep
    the order of salves); it's more like a wrapper for dict.
    """
    priority: int
    "priority of the option"

    __slots__ = tuple(__annotations__)

    def __init__(self, iterable: 'DictInit[str, str]' = (), priority: int = 0):
        """
        Init the instance.

        Args:
            iterable (Iterable, optional): Iterator for dict initialization.
                Default is empty list.
            priority (int, optional): Priority of the option. Default is 0.
        """
        super().__init__(iterable)
        self.priority = priority

    def describe(self, group: 'AltGroup') -> list[str]:
        """
        Convert the option into `update-alternatives --install` arguments.

        Args:
            group (AltGroup): The group which it belongs to.

        Returns:
            list[str]: `update-alternatives --install` arguments (including
            `--install`).

        Raises:
            ValueError: If the master path is missing.
        """
        args: list[str] = []
        for ind, name in enumerate(group):
            if name in self and self[name]:
                args.append('--install' if ind == 0 else '--slave')
                args.append(group[name])
                args.append(name)
                args.append(self[name])
            elif ind == 0:
                raise ValueError('master path missing')
            if ind == 0:
                args.append(str(self.priority))
        return args

    def same_with(
            self, other: 'SupportsGetItem[str, str]',
            group: Iterable[str]) -> bool:
        """
        Tell whether two options have the same path set for the group.

        Args:
            other (AltOption): Option to be compared with.
            group (AltGroup): The group which it belongs to.

        Returns:
            bool: The result.
        """
        return all(self[name] == other[name] for name in group)

    def list_paths(self, group: Sequence[str]) -> list[str]:
        return [
            self[group[i]] if group[i] in self else ''
            for i in range(len(group))]


class AltGroup(list[str]):
    """
    Class for alternative group.

    It acts like an :class:`OrderedDict`, but allows int as index. The class
    itself stores the names for the master and slave links, while the actual
    links are stored in `_links` attribute.

    See update-alternatives(1) for properties' detail.
    """
    config: AltConfig
    "alternative database config"
    options: list[AltOption]
    "available options"
    _links: dict[str, str]
    "links for names"
    _current: AltOption | None

    desc: str | None

    __slots__ = tuple(__annotations__)

    def __init__(
            self, name: str, create: bool = False,
            config: AltConfig = AltConfig()) -> None:
        super().__init__()
        self.config = config
        self.options = []
        self._links = {}
        self._current = None
        self[name] = ''

        if not create:
            self.reload()

    def reload(self) -> None:
        if not os.path.isfile(self.alt):
            raise IOError('group alt file missing')

        # parse alt file
        with open(self.alt) as alt_file:
            it = map(lambda s: s.strip(), alt_file)

            # target parser
            auto_mode = next(it) == 'auto'
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
                option = AltOption({next(it_name): line}, int(next(it)))
                for name in it_name:
                    option[name] = next(it)
                self.options.append(option)

        admin = os.path.join(self.config.admindir, self.name)
        if not os.path.islink(admin):
            raise IOError(f'admin link for "{self.name}" corrupted')
        current_path = os.readlink(admin)

        if auto_mode:
            self._current = None
        else:
            for option in self.options:
                if option[self.name] == current_path:
                    self._current = option
                    break
            else:
                raise ValueError(f'current option for "{self.name}" corrupted')

    @property
    def alt(self) -> str:
        """Path of alt file in the admindir."""
        return os.path.join(self.config.altdir, self.name)

    @property
    def name(self) -> str:
        """Name of the group."""
        return self[0]

    @property
    def link(self) -> str:
        """Master link of the group."""
        return self[self.name]

    @link.setter
    def link(self, value: str) -> None:
        self[self.name] = value

    @property
    def is_auto(self) -> bool:
        """whether the group is in auto mode"""
        return self._current is None

    @property
    def current(self) -> AltOption:
        """the current applied option"""
        return self.best if self._current is None else self._current

    @property
    def best(self) -> AltOption:
        """The best option for the group (the one with the highest priority)."""
        return max(self.options, key=lambda o: o.priority)

    @property
    def options_dict(self):
        res = {option[self.name]: option for option in self.options}
        if len(res) != len(self.options):
            raise ValueError('duplicated master path found')
        return res

    def select(self, index: int | None = None) -> bool:
        if index is None:
            if self._current is None:
                return False
            else:
                self._current = None
                return True
        else:
            if self._current is not None and \
                    self._current == self.options[index]:
                return False
            else:
                self._current = self.options[index]
                return True

    @overload
    def __setitem__(self, index: SupportsIndex | str, value: str) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[str]) -> None: ...

    def __setitem__(
            self, index: SupportsIndex | str | slice,
            value: str | Iterable[str]) -> None:
        if isinstance(index, str):
            value = cast(str, value)
            # except_absolute(value)
            if index not in self._links:
                super().append(index)
            self._links[index] = value
        elif isinstance(index, slice):
            super().__setitem__(index, value)
        else:
            value = cast(str, value)
            if value in self._links:
                raise KeyError('element already exists')
            # except_tag(value)
            self._links[value] = self._links[self[index]]
            del self._links[self[index]]
            super().__setitem__(index, value)

    @overload
    def __getitem__(self, index: SupportsIndex | str) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> list[str]: ...

    def __getitem__(
            self, index: SupportsIndex | str | slice) -> str | list[str]:
        if isinstance(index, str):
            return self._links[index]
        else:
            return super().__getitem__(index)

    def __delitem__(self, index: SupportsIndex | str | slice) -> None:
        if isinstance(index, slice):
            for link in self[index]:
                del self._links[link]
        else:
            if isinstance(index, str):
                index = self.index(index)
            del self._links[super().__getitem__(index)]
        super().__delitem__(index)

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}(altgroup={self.name!r}, '
            f'links={self._links!r}, options={self.options!r})')

    def items(self) -> Iterator[tuple[str, str]]:
        return ((link, self[link]) for link in self)

    def find_option(self, path: str) -> AltOption | None:
        for option in self.options:
            if option[self.name] == path:
                return option

    def compare(
            self, old_group: 'AltGroup | None' = None) -> Iterator[list[str]]:
        """
        Return list of `update-alternatives` arguments converting `old_group` to
        `self`.

        Args:
            old_group (AltGroup, optional): Old group.

        Returns:
            Iterator[list[str]]: List of `update-alternatives` arguments.
        """
        new_options = self.options_dict
        old_options = {} if old_group is None else old_group.options_dict

        for p in old_options:
            if p not in new_options:
                yield ['--remove', self.name, p]

        for p, o in new_options.items():
            if p not in old_options or not o.same_with(old_options[p], self):
                yield o.describe(self)

        if self.is_auto:
            if old_group and not old_group.is_auto:
                # old in manual
                yield ['--auto', self.name]
        else:
            if not old_group or old_group.is_auto or \
                    not self.current.same_with(old_group.current, self):
                # no old, old in auto, old current not the same
                yield ['--set', self.name, self.current[self.name]]


def iter_starts_with(l: Iterator[_T], prefix: Iterator[_T]) -> bool:
    if any(p != q for p, q in zip(l, prefix)):
        return False

    try:
        next(prefix)
    except StopIteration:
        return True
    else:
        return False


class AltDB(dict[str, AltGroup | None], AltConfig):
    _moves: dict[str, str | None]
    "map from new name to old name"

    __slots__ = tuple(__annotations__)

    def __init__(
            self, altdir: str | None = None, admindir: str | None = None,
            log: str | None = None) -> None:
        super().__init__(map(lambda name: (name, None), filter(
            lambda name: os.path.isfile(os.path.join(self.altdir, name)),
            os.listdir(self.altdir))))
        AltConfig.__init__(
            self, altdir or self.ALTDIR, admindir or self.ADMINDIR,
            log or self.LOG)
        self._moves = {}

    def __repr__(self) -> str:
        return repr(self.keys())

    def __getitem__(self, name: str) -> AltGroup:
        item = super().__getitem__(name)
        if item is None:
            item = AltGroup(name, config=self)
            self[name] = item
        return item

    def add(self, item: AltGroup) -> None:
        """
        Add new group to the alternative database.

        :param item: Group to be added.
        :raises KeyError: If the group name already exists.
        """
        # except_typeof(item, Group)
        if item.name in self:
            raise KeyError('element already exists')
        item.config = self
        self._moves[item.name] = None
        self[item.name] = item

    def move(self, old: str, new: str) -> None:
        if old in self._moves:
            self._moves[new] = self._moves[old]
            del self._moves[old]
        else:
            self._moves[new] = old
        if self._moves[new] == new:
            del self._moves[new]
        self[old][0] = new
        self[new] = self[old]
        del self[old]

    def compare(self, old_db: 'AltDB') -> Iterator[list[str]]:
        for name in old_db:
            if name not in self:
                # group in old but not in new
                yield ['--remove-all', name]

        for name, group in self.items():
            if group is None:
                continue
            # item has been accessed

            if name not in self._moves and iter_starts_with(
                    group.items(), old_db[name].items()):
                # simply add difference
                yield from group.compare(old_db[name])
                continue

            # group moved or more links than old one, reconstruct
            old_name = self._moves.get(name)
            if old_name is not None and old_name in old_db and old_name in self:
                yield ['--remove-all', old_name]
            elif name in old_db:
                yield ['--remove-all', name]
            yield from group.compare()

    def commit(
            self, cmds: Iterable[list[str]],
            executer: str | None = None) -> tuple[int, list[CommandResult]]:
        """
        Run commands to update alternatives.

        :param cmds: List of `update-alternatives` commands.
        :param executer: `sudo` command, if any.
        :return: Return code and list of :class:`CommandResult`. If commands
            failed midway, result list might be shorter than ``cmds``.
        """
        ret = 0
        results: list[CommandResult] = []
        for args in cmds:
            cmd: list[str] = []
            if executer:
                cmd.append(executer)
            cmd.append(self.update_cmd)
            cmd.extend(args)

            logger.debug(f'run command "{' '.join(cmd)}"')
            p = subprocess.run(cmd, capture_output=True, text=True)
            ret = p.returncode
            results.append(CommandResult(cmd, ret, p.stdout, p.stderr))
            if ret:
                break
        return ret, results
