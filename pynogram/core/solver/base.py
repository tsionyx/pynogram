# -*- coding: utf-8 -*-
"""Define nonogram solving operations"""

from __future__ import unicode_literals, print_function

import logging

from six import iteritems

from pynogram.core.common import normalize_row, normalize_description
from pynogram.core.solver import bgu
from pynogram.core.solver import simpson
from pynogram.core.solver.common import NonogramError, LineSolutionsMeta
from pynogram.core.solver.machine import (
    make_nfsm,
    NonogramFSM, NonogramFSMColored,
    LOG as MACHINE_LOGGER,
)

MACHINE_LOGGER.setLevel(logging.WARNING)
simpson.LOG.setLevel(logging.WARNING)


def _solver(name):
    if name in ('partial_match', 'reverse_tracking', 'reverse_tracking_color'):
        def _solve(row_desc, row):
            _name = name
            if _name == 'reverse_tracking_color':
                nfsm_class = NonogramFSMColored
                _name = 'reverse_tracking'
            else:
                nfsm_class = NonogramFSM

            nfsm = make_nfsm(row_desc, nfsm_cls=nfsm_class)

            method_func = getattr(nfsm, 'solve_with_' + _name)
            return method_func(row)

        return _solve

    if name == 'simpson':
        return simpson.FastSolver.solve

    if name == 'bgu':
        return bgu.BguSolver.solve

    raise AttributeError("Cannot find solving method '%s'" % name)


def solve_line(desc, line, method='reverse_tracking'):
    """
    Utility for row solving that can be used in multiprocessing map
    """
    # method = kwargs.pop('method', 'reverse_tracking')
    #
    # if len(args) == 1:
    #     # mp's map supports only one iterable, so this weird syntax
    #     args = args[0]
    #
    # desc, line = args

    desc = normalize_description(desc)
    # desc = tuple(desc)
    line = normalize_row(line)

    return _solver(method)(desc, line)


def assert_match(row_desc, row):
    """
    Verifies that the given row matches the description
    """
    nfsm = make_nfsm(row_desc)
    if not nfsm.match(row):
        raise NonogramError("The row '{}' cannot fit in clue '{}'".format(row, row_desc))


def cache_hit_rate():
    """Cache hit rate for different solvers"""
    return {
        class_name: cache.hit_rate
        for class_name, cache in iteritems(LineSolutionsMeta.registered_caches)
    }
