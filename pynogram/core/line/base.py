# -*- coding: utf-8 -*-
"""Define nonogram solving operations"""

from __future__ import unicode_literals, print_function

from six import (
    iteritems, itervalues,
    add_metaclass,
)

from pynogram.core.common import (
    NonogramError,
    SPACE_COLORED,
)
from pynogram.utils.cache import Cache


class TwoLayerCache(Cache):
    """
    Special cache for storing nonograms line solutions.
    The keys are pairs (clue, partial_solution)
    """

    def __len__(self):
        return sum(len(lines) for lines in itervalues(self._storage))

    def _save(self, name, value, **kwargs):
        clue, prev_line = name
        if clue not in self._storage:
            self._storage[clue] = dict()

        self._storage[clue][prev_line] = value

    def _get(self, name):
        clue, prev_line = name
        clue_solutions = self._storage.get(clue)
        if clue_solutions is None:
            return None

        return clue_solutions.get(prev_line)

    def delete(self, name):
        clue, prev_line = name
        clue_solutions = self._storage.get(clue)
        if clue_solutions is None:
            return False

        return bool(clue_solutions.pop(prev_line, False))


class LineSolutionsMeta(type):
    """
    A metaclass for line solvers.
    It adds the solutions_cache to the solver class.
    """

    registered_caches = {}

    def __new__(mcs, *args, **kwargs):
        new_cls = super(LineSolutionsMeta, mcs).__new__(mcs, *args, **kwargs)
        new_cls.solutions_cache = Cache(increase=True)
        mcs.registered_caches[new_cls.__name__] = new_cls.solutions_cache
        return new_cls


def cache_info():
    """Cache size and hit rate for different solvers"""
    return {
        class_name: (len(cache), cache.hit_rate)
        for class_name, cache in iteritems(LineSolutionsMeta.registered_caches)
    }


@add_metaclass(LineSolutionsMeta)
class BaseLineSolver(object):
    """
    Basic line nonogram solver which provides
    facilities to save and extract solutions using cache
    """

    def __init__(self, description, line):
        self.description = description
        self.line = line

    @classmethod
    def _error_message(cls, description, line, additional_info=''):
        """Solve the line (or use cached value)"""
        description, line = tuple(description), tuple(line)
        return '{}: Failed to solve line {!r} with clues {!r}{}'.format(
            cls.__name__, line, description, additional_info)

    @classmethod
    def solve(cls, description, line):
        """Solve the line (or use cached value)"""
        if not line:
            return line

        description, line = tuple(description), tuple(line)

        solved = cls.solutions_cache.get((description, line))

        if solved is False:
            raise NonogramError(
                cls._error_message(description, line, additional_info=' (cached)'))

        if solved is not None:
            assert len(solved) == len(line)
            return solved

        solver = cls(description, line)
        try:
            solved = tuple(solver._solve())
        except NonogramError as ex:
            cls.save_in_cache((description, line), False)
            raise NonogramError(
                cls._error_message(description, line, additional_info=': {}'.format(ex)))

        assert len(solved) == len(line)
        cls.save_in_cache((description, line), solved)
        return solved

    @classmethod
    def save_in_cache(cls, original, solved):
        """
        Put the solution in local cache.
        Use solved=False to show that the line is not solvable.
        """
        cls.solutions_cache.save(original, solved)

    def _solve(self):
        """
        Override this function with actual solving algorithm.
        You should return something iterable (tuple, list or even generator!).
        """
        return self.line


class ColoredSolver(BaseLineSolver):  # pragma: no cover
    """Define some helpers for colored puzzle solvers"""

    @classmethod
    def non_space_indexes(cls, line):
        """
        Skip some heading and trailing spaces in line.
        """
        first_non_space, last_non_space = 0, 0

        if line:
            for first_non_space, cell in enumerate(line):
                if cell != SPACE_COLORED:
                    break

            for last_non_space, cell in enumerate(reversed(line)):
                if cell != SPACE_COLORED:
                    break

        return first_non_space, last_non_space

    @classmethod
    def solve(cls, description, line):
        """Optimize line solving by trimming off the spaces"""

        original = line
        first_non_space, last_non_space = cls.non_space_indexes(line)
        if first_non_space:
            if last_non_space:
                line = line[first_non_space: -last_non_space]
            else:
                line = line[first_non_space:]
        elif last_non_space:
            line = line[:-last_non_space]

        if not line:  # if consists only of spaces
            return (SPACE_COLORED,) * len(original)

        solved = super(ColoredSolver, cls).solve(description, line)

        if first_non_space or last_non_space:
            space_t = (SPACE_COLORED,)
            solved = space_t * first_non_space + solved + space_t * last_non_space

        return solved
