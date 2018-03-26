# -*- coding: utf-8 -*-
"""Define common solving utilities"""

from __future__ import unicode_literals, print_function

from six import itervalues

from pynogram.utils.cache import Cache


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve a nonogram which has an internal contradiction.
    """
    pass


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
